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
from services.audio_summary.main import summarize_transcript
from services.audio_transcription.main import transcribe_audio_file
from services.aws.s3 import upload_to_s3
from services.aws.sqs import send_embedding_sqs_message
from services.utils.main import (
    _generate_fake_sqs_msg,
)
from services.utils.mongodb.main import create_mongodb_instance

load_dotenv()

# IMPORTANT: REMEMBER TO SET PYTHON_MODE in .env to 'production' when creating Docker image
PYTHON_MODE = os.getenv("PYTHON_MODE", "production")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

s3_client = boto3.client("s3", region_name=AWS_REGION)

whisper_model = whisper.load_model("turbo", device=DEVICE)

"""
Dev Notes 4/25/25:

- Decided to organize media uploads and call each upload a "Note".
- If the Note is an .mp3 or .mp4, a Note is created for that file and it'll get uploaded on the Frontend to s3 at /{userID}/{noteID}/{fileName}.{fileExtension}
- When SQS messages arrives in Extractor service, will transcribe and upload the transcript to s3 at /{userID}/{noteID}/{fileName}.txt

"""


async def main():
    mp3_file_name = None
    transcript_file_name = None

    print(f"PYTHON_MODE: ${PYTHON_MODE}")

    try:
        mongo_db = create_mongodb_instance()

        while True:
            # For MVP, will only dequee one SQS message at a time.
            _fake_sqs_msg = _generate_fake_sqs_msg(PYTHON_MODE)

            message_list = _fake_sqs_msg.get("Messages", [])

            print(f"message_list: {message_list}")

            if len(message_list) == 0:
                continue

            sqs_payload = message_list.pop()

            sqs_message = json.loads(sqs_payload.get("Body", {}))

            print(f"sqs_message: {sqs_message} \n")

            s3_key = sqs_message.get("s3_key")
            note_id = sqs_message.get("note_id")
            user_id = sqs_message.get("user_id")

            print(f"s3_k3y: {s3_key}, note_id: {note_id}, user_id: {user_id} \n")

            # DELETE after finishing development
            if PYTHON_MODE == "development":
                break

            transcript_id = _fake_sqs_msg.get("transcriptID")

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

            base_s3_key = f"{user_id}/{transcript_id}"

            # 3) Upload the mp3 audio and transcript to s3.
            uploaded_files = upload_to_s3(s3_client, base_s3_key, video_title)

            if len(uploaded_files) != 2:
                raise ValueError(
                    "Transcript and mp3 files were not uploaded to s3. Cannot proceed further"
                )

            s3_transcript_url, s3_mp3_url = uploaded_files

            # 4) Generate a summary of the transcript.
            summarize_start_time = time.time()

            transcript_summary = summarize_transcript(video_title)

            summarize_end_time = time.time()

            summarize_elapsed_time = summarize_end_time - summarize_start_time
            print(f"Elapsed time for summarizing: {summarize_elapsed_time} seconds")

            transcript_payload = {
                "_id": transcript_id,
                "transcriptURL": s3_transcript_url,
                "audioURL": s3_mp3_url,
                "transcriptSummary": transcript_summary,
            }

            options = {"upsert": True, "return_document": True}

            # 5) Update MongoDB and delete local files.
            await mongo_db["transcripts"].find_one_and_update(
                {"_id": transcript_id}, {"$set": transcript_payload}, **options
            )

            # 6) Delete local files & send SQS Message to embedding queue.
            delete_local_file(f"{video_title}.mp3")

            delete_local_file(f"{video_title}.txt")

            embedding_payload = {
                "_id": transcript_id,
                "transcriptURL": s3_transcript_url,
            }

            send_embedding_sqs_message(embedding_payload)

            # DELETE after finishing development
            if PYTHON_MODE == "development":
                break

    except ValueError as e:
        if mp3_file_name:
            delete_local_file(mp3_file_name)
        if transcript_file_name:
            delete_local_file(transcript_file_name)
        print(f"❌ Value Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
