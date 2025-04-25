import logging
import os
from typing import Any, Dict

from bson.objectid import ObjectId

youtube_url = "https://www.youtube.com/watch?v=1_gJp2uAjO0"
s3_video_url = "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/Palmer+Luckey+Wants+to+Be+Silicon+Valley's+War+King+%EF%BD%9C+The+Circuit.mp4"

DEV_MODE = bool(os.getenv("DEV_MODE", False))


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


def _generate_fake_sqs_msg() -> Dict[str, Any]:

    return {
        "userID": ObjectId(),
        "transcriptID": ObjectId(),
        "videoURL": youtube_url if DEV_MODE else s3_video_url,
    }
