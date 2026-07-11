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


"""Converts .mp4 to .mp3 file and immediately deletes .mp4 file."""


def convert_mp4_to_mp3(base_filename: str) -> None:

    base_title, _ = os.path.splitext(base_filename)

    sanitized_title = sanitize_filename(base_title)

    mp3_file = f"{sanitized_title}.mp3"

    if not os.path.exists(base_filename):
        raise FileNotFoundError(f"❌ MP4 file not found: {base_filename}")

    command = [
        "ffmpeg",
        "-i",
        base_filename,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ab",
        "192k",
        "-y",
        mp3_file,
    ]

    subprocess.run(command, check=True)

    delete_local_file(base_filename)


def download_with_retry(
    bucket_name: str, s3_key: str, retries: int = 5, delay: int = 2
) -> None:
    """Try downloading from S3 with retries and exponential backoff."""

    base_filename = os.path.basename(s3_key)  # e.g., video1.mp4

    for attempt in range(retries):
        try:
            with open(base_filename, "wb") as f:
                s3_client.download_fileobj(bucket_name, s3_key, f)
            if os.path.exists(base_filename):
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
      - Deletes local .mp4 file.
    Returns: dict of sanitized file_name and file_extension.
    """

    try:
        bucket_name = get_secret("/alwayssaved/AWS_BUCKET")
        if not bucket_name:
            raise ValueError("AWS_BUCKET not set in SSM.")

        base_filename = os.path.basename(s3_key)  # e.g., video1.mp4

        base_title, file_extension = os.path.splitext(base_filename)

        # File is successfully downloaded or an Exception is raised
        download_with_retry(bucket_name, s3_key)

        sanitized_filename = sanitize_filename(base_title)

        if file_extension == ".mp3":
            return {
                "file_name": sanitized_filename,
                "file_extension": file_extension,
            }

        convert_mp4_to_mp3(base_filename)

        return {"file_name": sanitized_filename, "file_extension": file_extension}

    except Exception as e:
        print(f"❌ Error in download_and_convert_from_s3: {e}")
        return None
