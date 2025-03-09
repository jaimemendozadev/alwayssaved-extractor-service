"""
Main extractor service file
"""

from services.audio_extractor.main import download_audio


def run_extractor_service():
    # Example Usage:
    download_audio("https://www.youtube.com/watch?v=8Ve5SAFPYZ8")


run_extractor_service()
