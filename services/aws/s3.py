import os

import boto3
import boto3.exceptions

from services.aws.ssm import get_secret
from services.utils.types.main import FilePayload


def upload_to_s3(
    s3_client: boto3.client, base_s3_key: str, file_name: str
) -> FilePayload:
    """
    base_s3_key is "{user_id}/{note_id}"
    file_name is the media file name with .extension
    """

    try:
        bucket_name = get_secret("/alwayssaved/AWS_BUCKET")
        bucket_base_url = get_secret("/alwayssaved/AWS_BUCKET_BASE_URL")

        if bucket_name is None or bucket_base_url is None:
            raise ValueError(
                "AWS_BUCKET or BUCKET_BASE_URL environment variables are not set."
            )

        file_abs_path = os.path.abspath(file_name)

        target_s3_key = f"{base_s3_key}/{file_name}"

        s3_client.upload_file(file_abs_path, bucket_name, target_s3_key)

        return {"s3_bucket": bucket_name, "s3_key": target_s3_key}

    except boto3.exceptions.S3UploadFailedError as e:
        print(f"❌ Error uploading file to s3 in upload_to_s3: {e}")
        return {"s3_bucket": "", "s3_key": ""}

    except ValueError as e:
        print(f"❌ Value Error in upload_to_s3: {e}")
        return {"s3_bucket": "", "s3_key": ""}
