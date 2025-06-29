"""
Main extractor service file
"""

import asyncio
import json
import os
import time
from typing import Coroutine, List

import boto3
import torch
import whisper
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

from services.audio_extractor.main import (
    delete_local_file,
    download_and_convert_from_s3,
)
from services.audio_transcription.main import transcribe_audio_file
from services.aws.s3 import upload_s3_file_record_in_db
from services.aws.sqs import (
    delete_extractor_sqs_message,
    get_extractor_sqs_request,
    send_embedding_sqs_message,
)
from services.utils.mongodb.main import create_mongodb_instance
from services.utils.types.main import ExtractorStatus, s3MediaUpload

# ────────────────────────────────────────────────────────────── #
#                           GLOBAL INIT                          #
# ────────────────────────────────────────────────────────────── #

load_dotenv()

# Force device detection once in main context
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"✅ [BOOT] Using device: {DEVICE}")

WHISPER_MODEL_NAME = "base"  # Or turbo -> confirm this is valid
WHISPER_MODEL = whisper.load_model(WHISPER_MODEL_NAME, device=str(DEVICE))
print(f"✅ Model loaded on device: {next(WHISPER_MODEL.parameters()).device}")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
s3_client = boto3.client("s3", region_name=AWS_REGION)


# Global lock to serialize GPU access
gpu_lock = asyncio.Lock()

# ────────────────────────────────────────────────────────────── #
#                       AUDIO TRANSCRIPTION                      #
# ────────────────────────────────────────────────────────────── #


def transcribe_audio(video_title: str) -> str | None:
    print(f"🔁 [subprocess] Starting transcription for: {video_title}")
    try:
        print(f"💻 [subprocess] Using device: {DEVICE}")
        model = whisper.load_model(WHISPER_MODEL_NAME, device=str(DEVICE))
        print(f"📦 Model loaded on: {next(model.parameters()).device}")
        return transcribe_audio_file(video_title, model)
    except Exception as e:
        print(f"❌ [subprocess] Failed in transcribe_audio: {e}")
        return None


# ────────────────────────────────────────────────────────────── #
#                       MEDIA PROCESSING                         #
# ────────────────────────────────────────────────────────────── #


async def process_media_upload(
    upload: s3MediaUpload, user_id: str, mongo_client: AsyncMongoClient
) -> ExtractorStatus:
    mp3_file_name = None
    transcript_file_name = None
    note_id = upload["note_id"]
    s3_key = upload["s3_key"]

    try:
        # 1) Download the audio file.
        audio_download_start_time = time.time()
        video_title = await asyncio.to_thread(download_and_convert_from_s3, s3_key)
        audio_elapsed_time = time.time() - audio_download_start_time
        print(
            f"Elapsed time for {video_title} audio download: {audio_elapsed_time:.2f}s"
        )

        if not video_title:
            raise ValueError("Video download failed.")

        mp3_file_name = f"{video_title}.mp3"

        # 2) Transcribe audio file.
        async with gpu_lock:
            transcribe_start_time = time.time()
            transcript_file_name = transcribe_audio(video_title)
            transcribe_elapsed_time = time.time() - transcribe_start_time

        print(
            f"Elapsed time for {video_title} transcribing: {transcribe_elapsed_time:.2f}s"
        )

        if not transcript_file_name:
            raise ValueError(f"Transcription for {video_title} failed.")

        # 3) Upload the mp3 audio and transcript to s3 and create File document.
        audio_payload, transcript_payload = await asyncio.gather(
            upload_s3_file_record_in_db(
                s3_client,
                mongo_client,
                {"file_name": mp3_file_name, "user_id": user_id, "note_id": note_id},
            ),
            upload_s3_file_record_in_db(
                s3_client,
                mongo_client,
                {
                    "file_name": transcript_file_name,
                    "user_id": user_id,
                    "note_id": note_id,
                },
            ),
        )

        if not all(
            [
                audio_payload.get("s3_key"),
                audio_payload.get("file_id"),
                transcript_payload.get("s3_key"),
                transcript_payload.get("file_id"),
            ]
        ):
            raise ValueError("Failed to upload audio or transcript to S3.")

        # 4) Delete local files, reset local variables.
        delete_local_file(mp3_file_name)
        mp3_file_name = None

        delete_local_file(transcript_file_name)
        transcript_file_name = None

        # 5) Send SQS Message to embedding queue & delete old processed SQS message.
        await asyncio.to_thread(
            send_embedding_sqs_message,
            {
                "note_id": note_id,
                "user_id": user_id,
                "file_id": transcript_payload["file_id"],
                "transcript_s3_key": transcript_payload["s3_key"],
            },
        )

        return {"s3_key": s3_key, "status": "success"}

    except ValueError as e:
        print(f"❌ Value Error in process_media_upload function: {e}")
        if mp3_file_name:
            delete_local_file(mp3_file_name)

        if transcript_file_name:
            delete_local_file(transcript_file_name)

        mp3_file_name = None
        transcript_file_name = None

        return {"s3_key": s3_key, "status": "failed"}


# ────────────────────────────────────────────────────────────── #
#                            MAIN LOOP                           #
# ────────────────────────────────────────────────────────────── #


async def main():

    mongo_client = create_mongodb_instance()

    while True:

        if mongo_client is None:
            print("❌ mongo_client unavailable. Can't run Extractor service.")
            return

        # For MVP, will only dequee one SQS message at a time.
        incoming_sqs_msg = get_extractor_sqs_request()
        message_list = incoming_sqs_msg.get("Messages", [])

        print(f"incoming_sqs_msg in main(): {incoming_sqs_msg}")

        if not message_list:
            print("No messages in SQS queue. Waiting...")
            await asyncio.sleep(5)
            continue

        popped_sqs_payload = message_list.pop()
        sqs_message_body = json.loads(popped_sqs_payload.get("Body", {}))

        user_id = sqs_message_body.get("user_id")
        media_uploads: List[s3MediaUpload] = sqs_message_body.get("media_uploads")

        if not (user_id and media_uploads):
            raise ValueError(
                f"Missing critical functionality like s3_client, user_id {user_id}, or media_uploads. Can't continue with media extraction."
            )

        tasks: List[Coroutine] = [
            process_media_upload(upload, user_id, mongo_client)
            for upload in media_uploads
        ]

        results = await asyncio.gather(*tasks)
        success_count = sum(1 for result in results if result["status"] == "success")
        failure_count = len(results) - success_count

        if success_count == 0:
            # All failed → Don't delete → Let SQS redrive or DLQ
            print("❌ All media uploads failed — skipping delete to allow DLQ redrive.")
        else:
            # 6) Delete old processed SQS message.
            # # ✅ At least one succeeded — go ahead and delete message
            delete_extractor_sqs_message(popped_sqs_payload)
            print(
                f"✅ Processed message with {success_count} successes and {failure_count} failures."
            )


if __name__ == "__main__":
    asyncio.run(main())


# pylint: disable=W0105
"""
Notes:

- Media uploads are organized as "Files" and all Files belong to a "Note".
- In v1: Users upload .mp4 Video file(s) on the Frontend where a single "Note" document is created.
  - A File document with the parent note_id is created for each video upload.

- When SQS messages arrives in Extractor service, will transcribe and upload the transcript to s3 at /{fileOwner}/{noteID}/{fileID}/{fileName}.txt
- Incoming SQS Message has the following shape:

  [
    {
      user_id: string;
      media_uploads: [
        {
         note_id: ObjectID;
         user_id: ObjectID;
         s3_key: string;
        }
      ]
    }
  ]


- Outgoing SQS Message has the following shape:
  {
      note_id: string;
      file_id: string;
      user_id: string;
      transcript_s3_key: string;
  }

"""
