"""
audio_extractor service file
"""

import os
import re
from typing import Any

import yt_dlp


def sanitize_filename(filename: str) -> str:
    """Removes invalid filename characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()


def delete_local_file(file_path: str):
    """Deletes the local MP3 file after uploading to S3."""
    abs_path = os.path.abspath(file_path)
    print(f"🔎 Trying to delete: {abs_path}")

    if os.path.exists(abs_path):
        os.remove(abs_path)
        print(f"🗑️ Deleted {abs_path}")
    else:
        print(f"⚠️ File not found: {abs_path}")


def download_audio(youtube_url: str):
    """Main donwload_audio function"""
    # Extract video metadata
    ydl_opts: dict[str, Any] = {"quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            youtube_url, download=False
        )  # Get metadata without downloading
        video_title = sanitize_filename(info.get("title", "unknown_video"))

    # Define output filename using video title
    output_path = f"{video_title}"

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
        "outtmpl": output_path,
        "quiet": False,
        "noplaylist": True,
        "ignoreerrors": True,
        "nopart": True,
        "overwrites": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        print(f"✅ Audio downloaded successfully: {output_path}")
        delete_local_file(os.path.abspath(f"{output_path}.mp3"))

    except yt_dlp.DownloadError as e:
        print(f"❌ Error downloading audio: {e}")
        return None
