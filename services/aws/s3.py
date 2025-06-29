import os

import boto3
import boto3.exceptions
from bson.objectid import ObjectId
from pymongo import AsyncMongoClient

from services.aws.ssm import get_secret
from services.utils.types.main import BaseFilePayload, FilePayload


async def upload_s3_file_record_in_db(
    s3_client: boto3.client,
    mongo_client: AsyncMongoClient,
    base_file_payload: BaseFilePayload,
) -> FilePayload:
    """
    Creates a new MongoDB File, uploads the File to s3, then updates the newly created File document with the s3_key.

    file_name is the media file name with .extension
    """

    user_id = base_file_payload["user_id"]
    note_id = base_file_payload["note_id"]
    file_name = base_file_payload["file_name"]

    base_s3_key = f"{user_id}/{note_id}"

    try:
        bucket_name = get_secret("/alwayssaved/AWS_BUCKET")
        bucket_base_url = get_secret("/alwayssaved/AWS_BUCKET_BASE_URL")

        if bucket_name is None or bucket_base_url is None:
            raise ValueError(
                "AWS_BUCKET or BUCKET_BASE_URL environment variables are not set."
            )

        file_abs_path = os.path.abspath(file_name)

        if not os.path.exists(file_abs_path):
            raise FileNotFoundError(f"File does not exist: {file_abs_path}")

        _, file_extension = os.path.splitext(file_name)

        new_file_payload = {
            "user_id": user_id,
            "note_id": note_id,
            "file_name": file_name,
            "file_type": file_extension,
        }

        insert_result = (
            await mongo_client.get_database("alwayssaved")
            .get_collection("files")
            .insert_one(new_file_payload)
        )

        new_file_id = insert_result.inserted_id

        target_s3_key = f"{base_s3_key}/{new_file_id}/{file_name}"

        s3_client.upload_file(file_abs_path, bucket_name, target_s3_key)

        await mongo_client.get_database("alwayssaved").get_collection(
            "files"
        ).find_one_and_update(
            {"_id": ObjectId(new_file_id)}, {"$set": {"s3_key": target_s3_key}}
        )

        return {"s3_key": target_s3_key, "file_id": new_file_id}

    except boto3.exceptions.S3UploadFailedError as e:
        print(f"❌ Error uploading file to s3 in upload_to_s3: {e}")

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")

    except ValueError as e:
        print(f"❌ Value Error in upload_to_s3: {e}")

    return {"s3_key": "", "file_id": ""}
