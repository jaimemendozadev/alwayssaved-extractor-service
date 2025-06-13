import logging
import os
import re
import subprocess
import time
from typing import Any, Dict

import boto3
import yt_dlp
from botocore.exceptions import ClientError

from services.aws.ssm import get_secret

s3_client = boto3.client("s3")


def delete_local_file(file_path: str):
    """Deletes the local MP3 file after uploading to S3."""
    abs_path = os.path.abspath(file_path)
    logging.info(f"🔎 Trying to delete: {abs_path}")

    try:
        os.remove(abs_path)
        logging.info(f"🗑️ Deleted {abs_path}")
    except FileNotFoundError:
        logging.warning(f"⚠️ File not found: {abs_path}")
    except Exception as e:
        logging.error(f"❌ Error deleting file {abs_path}: {e}")


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()


def convert_mp4_to_mp3(mp4_path: str, video_title: str) -> str:
    sanitized_title = sanitize_filename(video_title)
    mp3_file = f"{sanitized_title}.mp3"

    if not os.path.exists(mp4_path):
        raise FileNotFoundError(f"❌ MP4 file not found: {mp4_path}")

    print("🎧 Extracting audio from MP4 using ffmpeg...")

    command = [
        "ffmpeg",
        "-i",
        mp4_path,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ab",
        "192k",
        "-y",
        mp3_file,
    ]

    subprocess.run(command, check=True)
    print(f"✅ Audio extracted to: {mp3_file}")

    return sanitized_title


def download_with_retry(
    bucket: str, s3_key: str, local_path: str, retries: int = 5, delay: int = 2
):
    """Try downloading from S3 with retries and exponential backoff."""
    for attempt in range(retries):
        try:
            with open(local_path, "wb") as f:
                s3_client.download_fileobj(bucket, s3_key, f)
            if os.path.exists(local_path):
                return
        except ClientError as e:
            if e.response["Error"]["Code"] in ["404", "403", "NoSuchKey"]:
                wait = delay * (2**attempt)
                logging.warning(f"S3 not ready yet. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Failed to download {s3_key} from S3 after {retries} attempts.")


def download_and_convert_from_s3(s3_key: str) -> str | None:
    """
    Downloads an .mp4 file from S3 using the s3_key and converts it to .mp3.
    Returns: sanitized video title (base filename without extension)
    """

    try:
        bucket_name = get_secret("/alwayssaved/AWS_BUCKET")
        if not bucket_name:
            raise ValueError("AWS_BUCKET not set in SSM.")

        base_filename = os.path.basename(s3_key)  # e.g., video1.mp4
        base_title, _ = os.path.splitext(base_filename)
        mp4_local_path = base_filename

        print(f"📥 Downloading from S3: s3://{bucket_name}/{s3_key}")
        download_with_retry(bucket_name, s3_key, mp4_local_path)

        print(f"🎞️ Download complete: {mp4_local_path}")

        video_title = convert_mp4_to_mp3(mp4_local_path, base_title)
        print(f"✅ MP3 created: {video_title}.mp3")

        return video_title

    except Exception as e:
        print(f"❌ Error in download_and_convert_from_s3: {e}")
        return None


def _download_video_from_url(
    video_url: str,
) -> None:
    """
    development MODE: Download full .mp4, convert to .mp3, return path to .mp3
    production MODE: Download .mp3 directly using yt_dlp
    """

    try:
        print("📥 [DEV MODE] Downloading full MP4 from YouTube...")

        ydl_opts: Dict[str, Any] = {
            "format": "best[ext=mp4]/best",  # enforce a usable mp4 file
            "merge_output_format": "mp4",
            "outtmpl": "%(title)s.%(ext)s",  # still saves with YouTube title
            "quiet": False,
            "noplaylist": True,
            "ignoreerrors": True,
            "nopart": True,
            "overwrites": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

            # This gives you the actual, real filepath yt-dlp saved to
            output_path = info.get("requested_downloads", [{}])[0].get("filepath")

        if not output_path or not os.path.exists(output_path):
            raise yt_dlp.DownloadError(f"❌ Full MP4 not downloaded: {output_path}")

        print(f"✅ Downloaded video: {output_path}")

    except yt_dlp.DownloadError as e:
        print(f"❌ yt-dlp Error in download_video_or_audio: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error in download_video_or_audio: {e}")

    return None
