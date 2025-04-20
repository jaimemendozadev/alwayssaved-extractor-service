import logging
import os
from typing import Any, Dict

from bson.objectid import ObjectId
from faker import Faker


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


def _generate_fake_user() -> Dict[str, Any]:
    fake = Faker()

    fake_user = {
        "_id": ObjectId(),
        "name": fake.name(),
        "email": fake.email(),
    }

    return fake_user
