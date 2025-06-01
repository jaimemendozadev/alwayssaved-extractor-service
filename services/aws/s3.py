import os
from typing import TypedDict

import boto3
import boto3.exceptions
from motor.motor_asyncio import AsyncIOMotorDatabase

from services.aws.ssm import get_secret
from services.utils.types.main import FilePayload


class BaseFilePayload(TypedDict):
    user_id: str
    note_id: str
    file_name: str


# TODO Need to create a new File document with s3_key in the following format: /{fileOwner}/{noteID}/{fileID}/{fileName}.{fileExtension}
async def upload_s3_file_record_in_db(
    s3_client: boto3.client,
    mongo_client: AsyncIOMotorDatabase,
    base_file_payload: BaseFilePayload,
) -> FilePayload:
    """
    base_s3_key is "{user_id}/{note_id}"
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

        target_s3_key = f"{base_s3_key}/{file_name}"

        _, file_extension = os.path.splitext(target_s3_key)

        s3_client.upload_file(file_abs_path, bucket_name, target_s3_key)

        new_file_payload = {
            "user_id": user_id,
            "note_id": note_id,
            "s3_key": target_s3_key,
            "file_name": file_name,
            "file_type": file_extension,
        }

        new_file = await mongo_client["files"].insert_one(new_file_payload)

        return {"s3_bucket": bucket_name, "s3_key": target_s3_key}

    except boto3.exceptions.S3UploadFailedError as e:
        print(f"❌ Error uploading file to s3 in upload_to_s3: {e}")
        return {"s3_bucket": "", "s3_key": ""}

    except ValueError as e:
        print(f"❌ Value Error in upload_to_s3: {e}")
        return {"s3_bucket": "", "s3_key": ""}
