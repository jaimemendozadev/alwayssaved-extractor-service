"""
Main extractor service file
"""

import os

import boto3
import whisper
from dotenv import load_dotenv

from services.audio_extractor.main import download_audio
from services.audio_transcription.main import transcribe_audio_file
from services.aws.s3 import upload_to_s3
from services.utils.main import _generate_fake_sqs_msg, delete_local_file

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

s3_client = boto3.client("s3", region_name=AWS_REGION)
whisper_model = whisper.load_model("turbo")


def run_extractor_service():
    mp3_file_name = None
    transcript_file_name = None

    try:
        _fake_sqs_msg = _generate_fake_sqs_msg()
        video_url = _fake_sqs_msg
        video_title = download_audio(video_url)

        if video_title is None:
            raise ValueError(
                "Video File was not downloaded. Cannot proceed any further."
            )

        mp3_file_name = f"{video_title}.mp3"

        transcript_file_name = transcribe_audio_file(video_title, whisper_model)

        if transcript_file_name is None:
            raise ValueError("Audio was not transcribed. Cannot proceed further")

        uploaded_file_name = upload_to_s3(s3_client, transcript_file_name)

        if uploaded_file_name is None:
            raise ValueError(
                "Transcript was not uploaded to s3. Cannot proceed further"
            )

        delete_local_file(f"{video_title}.mp3")
        delete_local_file(f"{video_title}.txt")

    except ValueError as e:
        if mp3_file_name:
            delete_local_file(mp3_file_name)

        if transcript_file_name:
            delete_local_file(transcript_file_name)

        print(f"❌ Value Error: {e}")


run_extractor_service()
