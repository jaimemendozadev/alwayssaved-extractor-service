import os

import boto3
import boto3.exceptions

from services.aws.sqs import send_sqs_message
from services.aws.ssm import get_secret


def upload_to_s3(s3_client: boto3.client, file_name) -> None:

    try:
        bucket_name = get_secret("/notecasts/AWS_BUCKET")
        bucket_base_url = get_secret("/notecasts/AWS_BUCKET_BASE_URL")

        if bucket_name is None or bucket_base_url is None:
            raise ValueError(
                "AWS_BUCKET or BUCKET_BASE_URL environment variables are not set."
            )

        file_abs_path = os.path.abspath(file_name)
        s3_client.upload_file(file_abs_path, bucket_name, file_name)

        send_sqs_message(f"{bucket_base_url}/{file_name}")

        return file_name

    except boto3.exceptions.S3UploadFailedError as e:
        print(f"❌ Error uploading file to s3: {e}")
        return None

    except ValueError as e:
        print(f"❌ Value Error: {e}")
        return None
