import logging
import os
import re
import subprocess
import time

import boto3

from services.aws.ssm import get_secret
from services.utils.types.main import s3DownloadConvertResult

s3_client = boto3.client("s3")


def delete_local_file(file_path: str):
    """Deletes the local MP3 file after uploading to S3."""
    try:
        if file_path and os.path.exists(file_path):
            logging.info(f"🔎 Trying to delete: {file_path}")
            os.remove(file_path)
            print(f"🗑️ Deleted local file: {file_path}")
        else:
            print(f"⚠️ File not found or invalid: {file_path}")
    except Exception as e:
        print(f"❌ Failed to delete file {file_path}: {e}")


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
) -> None:
    """Try downloading from S3 with retries and exponential backoff."""
    for attempt in range(retries):
        try:
            with open(local_path, "wb") as f:
                s3_client.download_fileobj(bucket, s3_key, f)
            if os.path.exists(local_path):
                return
        except Exception:
            logging.error("An exception occurred in download_with_retry", exc_info=True)
            wait = delay * (2**attempt)
            logging.warning(f"S3 not ready yet. Retrying in {wait}s...")
            time.sleep(wait)

    raise Exception(f"Failed to download {s3_key} from S3 after {retries} attempts.")


def download_and_convert_from_s3(s3_key: str) -> s3DownloadConvertResult | None:
    """
    Downloads .mp3 or .mp4 files from S3 using the s3_key.
    Converts .mp4 files to .mp3 files.
    Returns: dict of sanitized file_name and file_extension.
    """

    try:
        bucket_name = get_secret("/alwayssaved/AWS_BUCKET")
        if not bucket_name:
            raise ValueError("AWS_BUCKET not set in SSM.")

        base_filename = os.path.basename(s3_key)  # e.g., video1.mp4
        base_title, file_extension = os.path.splitext(base_filename)
        base_file_local_path = base_filename

        print(f"📥 Downloading from S3: s3://{bucket_name}/{s3_key}")

        # File is successfully downloaded or an Exception is raised
        download_with_retry(bucket_name, s3_key, base_file_local_path)

        print(f"🎞️ Download complete: {base_file_local_path}")

        if file_extension == ".mp3":
            return {
                "file_name": sanitize_filename(base_title),
                "file_extension": file_extension,
            }

        video_title = convert_mp4_to_mp3(base_file_local_path, base_title)
        print(f"✅ MP3 created: {video_title}.mp3")

        return {"file_name": video_title, "file_extension": file_extension}

    except Exception as e:
        print(f"❌ Error in download_and_convert_from_s3: {e}")
        return None
