import os
from typing import List

import boto3
import boto3.exceptions

from services.aws.ssm import get_secret
from services.utils.types.main import FilePayload


def upload_to_s3(
    s3_client: boto3.client, base_s3_key, video_title
) -> List[FilePayload]:

    try:
        bucket_name = get_secret("/alwayssaved/AWS_BUCKET")
        bucket_base_url = get_secret("/alwayssaved/AWS_BUCKET_BASE_URL")

        uploaded_files: List[FilePayload] = []

        if bucket_name is None or bucket_base_url is None:
            raise ValueError(
                "AWS_BUCKET or BUCKET_BASE_URL environment variables are not set."
            )

        files_to_upload = [f"{video_title}.txt", f"{video_title}.mp3"]

        for file in files_to_upload:
            file_abs_path = os.path.abspath(file)
            target_s3_key = f"{base_s3_key}/{file}"
            full_s3_url = f"{bucket_base_url}/{bucket_name}/{target_s3_key}"

            print(f"full_s3_url: {full_s3_url} \n")

            uploaded_files.append({"s3_url": full_s3_url, "s3_key": target_s3_key})

            s3_client.upload_file(file_abs_path, bucket_name, target_s3_key)

        return uploaded_files

    except boto3.exceptions.S3UploadFailedError as e:
        print(f"❌ Error uploading file to s3: {e}")
        return []

    except ValueError as e:
        print(f"❌ Value Error: {e}")
        return []
