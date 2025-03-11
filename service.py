"""
Main extractor service file
"""

import boto3
import whisper
from dotenv import load_dotenv

from services.audio_extractor.main import download_audio
from services.audio_transcription.main import transcribe_audio_file
from services.aws.s3 import upload_to_s3
from services.utils.main import delete_local_file

load_dotenv()
s3_client = boto3.client("s3")
whisper_model = whisper.load_model("turbo")


def run_extractor_service():
    try:
        video_title = download_audio("https://www.youtube.com/watch?v=8Ve5SAFPYZ8")

        if video_title is None:
            raise ValueError(
                "Video File was not downloaded. Cannot proceed any further."
            )

        transcript_name = transcribe_audio_file(video_title, whisper_model)

        if transcript_name is None:
            delete_local_file(f"{video_title}.mp3")
            raise ValueError("Audio was not transcribed. Cannot proceed further")

        uploaded_file_name = upload_to_s3(s3_client, transcript_name)

        if uploaded_file_name is None:
            delete_local_file(f"{video_title}.mp3")
            delete_local_file(f"{video_title}.txt")
            raise ValueError(
                "Transcript was not uploaded to s3. Cannot proceed further"
            )

        delete_local_file(f"{video_title}.mp3")
        delete_local_file(f"{video_title}.txt")

    except ValueError as e:
        print(f"❌ Value Error: {e}")


run_extractor_service()
