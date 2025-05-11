"""
MongoDB util functions file.
"""

import logging
import os
from typing import List, TypedDict

from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import NetworkTimeout, OperationFailure, ServerSelectionTimeoutError

from services.aws.ssm import get_secret
from services.utils.types.main import FilePayload


def create_mongodb_instance() -> AsyncIOMotorDatabase:
    mongo_db_user = get_secret("/alwayssaved/MONGO_DB_USER")

    mongo_db_password = get_secret("/alwayssaved/MONGO_DB_PASSWORD")

    mongo_db_base_uri = get_secret("/alwayssaved/MONGO_DB_BASE_URI")

    mongo_db_name = get_secret("/alwayssaved/MONGO_DB_NAME")

    mongo_db_cluster_name = get_secret("/alwayssaved/MONGO_DB_CLUSTER_NAME")

    if (
        mongo_db_user is None
        or mongo_db_password is None
        or mongo_db_base_uri is None
        or mongo_db_cluster_name is None
        or mongo_db_name is None
    ):
        raise ValueError("MONGO_DB environment variables are not set.")

    connection_string = f"mongodb+srv://{mongo_db_user}:{mongo_db_password}@{mongo_db_base_uri}/{mongo_db_name}?retryWrites=true&w=majority&appName={mongo_db_cluster_name}"

    # Create a new client and connect to the server
    client: AsyncIOMotorClient = AsyncIOMotorClient(connection_string)

    return client[mongo_db_name]


class NotePayload(TypedDict):
    note_id: str
    user_id: str


async def create_note_files(
    video_title: str,
    note_payload: NotePayload,
    file_payloads: List[FilePayload],
    mongo_client: AsyncIOMotorDatabase,
) -> List[ObjectId]:

    file_ids: List[ObjectId] = []

    try:

        for payload in file_payloads:
            note_ID = ObjectId(note_payload["note_id"])
            user_ID = ObjectId(note_payload["user_id"])
            s3_bucket = payload.get("s3_bucket", "")
            s3_key = payload.get("s3_key", "")
            _, file_extension = os.path.splitext(s3_key)

            file_extension = file_extension.lower()

            new_file_payload = {
                "user_id": user_ID,
                "note_id": note_ID,
                "s3_key": s3_key,
                "s3_bucket": s3_bucket,
                "file_name": video_title,
                "file_type": file_extension,
            }
            new_file = await mongo_client["files"].insert_one(new_file_payload)
            file_ids.append(new_file.inserted_id)

    except (ServerSelectionTimeoutError, NetworkTimeout) as conn_err:
        logging.error(f"MongoDB connection issue in create_note_files: {conn_err}")
    except OperationFailure as op_err:
        logging.error(f"MongoDB operation failed in create_note_files: {op_err}")
    except Exception as e:
        logging.exception(
            f"Unexpected error while inserting file document in create_note_files: {e}"
        )

    return file_ids
