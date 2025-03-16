"""
audio_extractor service file
"""

import os
import re
from typing import Any, Dict

import yt_dlp

from services.aws.ssm import get_secret


def sanitize_filename(filename: str) -> str:
    """Removes invalid filename characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()


def download_audio(youtube_url: str) -> str | None:
    """Main donwload_audio function"""
    # Extract video metadata
    ydl_opts: Dict[str, Any] = {"quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            youtube_url, download=False
        )  # Get metadata without downloading
        video_title = sanitize_filename(info.get("title", "unknown_video"))

    # Download audio with correct filename
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": video_title,
        "quiet": False,
        "noplaylist": True,
        "ignoreerrors": True,
        "nopart": True,
        "overwrites": True,
    }

    try:
        bucket_name = get_secret("/notecasts/AWS_BUCKET")

        if bucket_name is None:
            raise ValueError("AWS_BUCKET environment variable is not set.")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        mp3_file_name = f"{video_title}.mp3"
        mp3_abs_path = os.path.abspath(mp3_file_name)

        if os.path.exists(mp3_abs_path) is False:
            raise yt_dlp.DownloadError(
                "There was a problem downloading the YouTube video."
            )

        print(f"✅ Audio downloaded successfully: {video_title}")

        return video_title

    except yt_dlp.DownloadError as e:
        print(f"❌ Error downloading audio: {e}")
        return None
    except ValueError as e:
        print(f"❌ Value Error: {e}")
        return None
