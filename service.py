"""
Main extractor service file
"""

import os

import boto3
import whisper
from dotenv import load_dotenv

from services.audio_extractor.main import download_audio

load_dotenv()
client = boto3.client("s3")
whisper_model = whisper.load_model("turbo")


def run_extractor_service():
    try:
        video_title = download_audio("https://www.youtube.com/watch?v=8Ve5SAFPYZ8")

        if video_title is None:
            raise ValueError("")

        transcript_name = f"{video_title}.txt"
        mp3_file_name = f"{video_title}.mp3"

        audio_file = os.path.abspath(mp3_file_name)

        transcript_file = os.path.abspath(transcript_name)
        result = whisper_model.transcribe(audio_file, fp16=False)

        with open(file=f"{output_path}.txt", mode="w", encoding="utf-8") as file:
            file.write(result["text"])
            print(f"✅ Audio successfully transcribed: {output_path}")

        s3Client.upload_file(transcript_file, bucket_name, transcript_name)
        delete_local_file(audio_file)
        delete_local_file(transcript_file)

    except ValueError as e:
        print(f"❌ Value Error: {e}")


run_extractor_service()
