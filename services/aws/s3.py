import os

import boto3
import boto3.exceptions


def upload_to_s3(s3_client: boto3.client, file_name) -> None:

    try:
        bucket_name = os.getenv("AWS_BUCKET")

        if bucket_name is None:
            raise ValueError("AWS_BUCKET environment variable is not set.")

        file_abs_path = os.path.abspath(file_name)
        s3_client.upload_file(file_abs_path, bucket_name, file_name)

        return file_name

    except boto3.exceptions.S3UploadFailedError as e:
        print(f"❌ Error uploading file to s3: {e}")
        return None

    except ValueError as e:
        print(f"❌ Value Error: {e}")
        return None
