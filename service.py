"""
Main extractor service file
"""

import asyncio
import os
import time

import boto3
import whisper
from dotenv import load_dotenv

from services.audio_extractor.main import download_video_or_audio
from services.audio_summary.main import summarize_transcript
from services.audio_transcription.main import transcribe_audio_file
from services.aws.s3 import upload_to_s3
from services.aws.sqs import send_embedding_sqs_message
from services.utils.main import _generate_fake_sqs_msg, delete_local_file
from services.utils.mongodb.main import create_mongodb_instance

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

s3_client = boto3.client("s3", region_name=AWS_REGION)
whisper_model = whisper.load_model("turbo")

DEV_MODE = os.getenv("DEV_MODE", False)


async def main():
    mp3_file_name = None
    transcript_file_name = None

    try:
        mongo_db = create_mongodb_instance()

        _fake_sqs_msg = _generate_fake_sqs_msg()

        video_url = _fake_sqs_msg.get("videoURL")

        user_id = _fake_sqs_msg.get("userID")

        transcript_id = _fake_sqs_msg.get("transcriptID")

        # 1) Download the audio file.
        audio_download_start_time = time.time()

        print(f"download_video_or_audio start at: {audio_download_start_time}")
        video_title = download_video_or_audio(video_url, DEV_MODE)

        print(f"video_title from download_video_or_audio: {video_title}")

        audio_download_end_time = time.time()
        audio_elapsed_time = audio_download_end_time - audio_download_start_time
        print(f"Elapsed time for audio download: {audio_elapsed_time} seconds")

        # Logs stop here... why? 🤔

        if video_title is None:
            raise ValueError(
                "Video File was not downloaded. Cannot proceed any further."
            )

        mp3_file_name = f"{video_title}.mp3"

        # 2) Transcribe audio file.
        transcribe_start_time = time.time()

        print(f"transcribe_audio_file start at: {transcribe_start_time}")
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
        db_result = await mongo_db["transcripts"].find_one_and_update(
            {"_id": transcript_id}, {"$set": transcript_payload}, **options
        )

        print(f"db_result {db_result}")

        # 6) Delete local files & send SQS Message to embedding queue.
        delete_local_file(f"{video_title}.mp3")
        delete_local_file(f"{video_title}.txt")

        embedding_payload = {
            "_id": transcript_id,
            "transcriptURL": s3_transcript_url,
        }

        send_embedding_sqs_message(embedding_payload)

    except ValueError as e:
        if mp3_file_name:
            delete_local_file(mp3_file_name)

        if transcript_file_name:
            delete_local_file(transcript_file_name)

        print(f"❌ Value Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
