"""
Main extractor service file
"""

import boto3
import whisper
from dotenv import load_dotenv

from services.audio_extractor.main import download_audio
from services.audio_transcription.main import transcribe_audio_file
from services.utils.main import delete_local_file

load_dotenv()
s3cClient = boto3.client("s3")
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

        transcript_abs_path = os.path.abspath(transcript_name)

        s3Client.upload_file(transcript_abs_path, bucket_name, video_title)
        delete_local_file(f"{video_title}.mp3")
        delete_local_file(f"{video_title}.txt")

    except ValueError as e:
        print(f"❌ Value Error: {e}")


run_extractor_service()
