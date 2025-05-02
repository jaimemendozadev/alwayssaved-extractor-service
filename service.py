"""
Main extractor service file
"""

import asyncio
import json
import os
import time

import boto3
import torch
import whisper
from dotenv import load_dotenv

from services.audio_extractor.main import delete_local_file, download_video_or_audio
from services.audio_transcription.main import transcribe_audio_file
from services.aws.s3 import upload_to_s3
from services.aws.sqs import get_extractor_sqs_request, send_embedding_sqs_message
from services.utils.mongodb.main import create_mongodb_instance, create_note_files

load_dotenv()

# IMPORTANT: REMEMBER TO SET PYTHON_MODE in .env to 'production' when creating Docker image
PYTHON_MODE = os.getenv("PYTHON_MODE", "production")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

s3_client = boto3.client("s3", region_name=AWS_REGION)

whisper_model = whisper.load_model("turbo", device=DEVICE)


async def main():
    mp3_file_name = None
    transcript_file_name = None

    print(f"PYTHON_MODE: ${PYTHON_MODE}")

    try:
        mongo_db = create_mongodb_instance()

        while True:
            # For MVP, will only dequee one SQS message at a time.
            sqs_msg = get_extractor_sqs_request()

            message_list = sqs_msg.get("Messages", [])

            if len(message_list) == 0:
                continue

            sqs_payload = message_list.pop()

            sqs_message = json.loads(sqs_payload.get("Body", {}))

            s3_key = sqs_message.get("s3_key", None)
            note_id = sqs_message.get("note_id", None)
            user_id = sqs_message.get("user_id", None)

            if s3_client is None or note_id is None or user_id is None:
                raise ValueError(
                    f"Missing s3_key: {s3_key}, note_id: {note_id}, or user_id: {user_id} for incoming SQS Message."
                )

            # 1) Download the audio file.
            audio_download_start_time = time.time()

            video_title = download_video_or_audio(s3_key, PYTHON_MODE)

            audio_download_end_time = time.time()
            audio_elapsed_time = audio_download_end_time - audio_download_start_time

            print(f"Elapsed time for audio download: {audio_elapsed_time} seconds")

            if video_title is None:
                raise ValueError(
                    "Video File was not downloaded. Cannot proceed any further."
                )

            mp3_file_name = f"{video_title}.mp3"

            # 2) Transcribe audio file.
            transcribe_start_time = time.time()

            transcript_file_name = transcribe_audio_file(video_title, whisper_model)

            transcribe_end_time = time.time()

            transcribe_elapsed_time = transcribe_end_time - transcribe_start_time
            print(f"Elapsed time for transcribing: {transcribe_elapsed_time} seconds")

            if transcript_file_name is None:
                raise ValueError("Audio was not transcribed. Cannot proceed further")

            base_s3_key = f"{user_id}/{note_id}"

            # 3) Upload the mp3 audio and transcript to s3.
            uploaded_files = upload_to_s3(s3_client, base_s3_key, video_title)

            if len(uploaded_files) != 2:
                raise ValueError(
                    "Transcript and mp3 files were not uploaded to s3. Cannot proceed further"
                )

            s3_transcript_url, s3_mp3_url = uploaded_files  # pylint: disable=W0632

            s3_urls = [s3_transcript_url, s3_mp3_url]

            # 5) Update MongoDB and delete local files.
            await create_note_files(
                video_title=video_title,
                note_payload={"user_id": user_id, "note_id": note_id},
                s3_urls=s3_urls,
                mongo_client=mongo_db,
            )

            # 6) Delete local files, reset local variables, and send SQS Message to embedding queue.
            delete_local_file(f"{video_title}.mp3")
            mp3_file_name = None

            delete_local_file(f"{video_title}.txt")
            transcript_file_name = None

            embedding_payload = {
                "note_id": note_id,
                "transcript_url": s3_transcript_url,
            }

            # TODO: May have to reevaluate payload shape that gets sent to embedding service
            send_embedding_sqs_message(embedding_payload)

    except ValueError as e:
        if mp3_file_name:
            delete_local_file(mp3_file_name)
        if transcript_file_name:
            delete_local_file(transcript_file_name)

        mp3_file_name = None
        transcript_file_name = None

        print(f"❌ Value Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

# pylint: disable=W0105
"""
Dev Notes 5/1/25:

- Decided to organize media uploads and call each upload a "Note".
- If the Note is an .mp3 or .mp4, a Note is created for that file and it'll get uploaded on the Frontend to s3 at /{userID}/{noteID}/{fileName}.{fileExtension}
- When SQS messages arrives in Extractor service, will transcribe and upload the transcript to s3 at /{userID}/{noteID}/{fileName}.txt
- Incoming SQS Message has the following shape:
  {
     note_id: ObjectID;
     user_id: ObjectID;
     s3_key: string;
  }


- Outgoing SQS Message has the following shape (may get redone):
{
    note_id: string;
    transcript_url: string;
}
"""
