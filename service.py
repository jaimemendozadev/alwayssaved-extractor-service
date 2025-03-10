"""
Main extractor service file
"""

import boto3
from dotenv import load_dotenv

from services.audio_extractor.main import download_audio

load_dotenv()
client = boto3.client("s3")


def run_extractor_service():
    # Example Usage:
    download_audio(client, "https://www.youtube.com/watch?v=8Ve5SAFPYZ8")


run_extractor_service()
