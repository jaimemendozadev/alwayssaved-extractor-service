import os
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from mypy_boto3_ssm import SSMClient

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

ssm_client: SSMClient = boto3.client("ssm", region_name=AWS_REGION)


def get_secret(param_name: str) -> Optional[str]:
    try:
        response = ssm_client.get_parameter(Name=param_name, WithDecryption=True)
        return response["Parameter"]["Value"]

    except ClientError as e:
        print(
            f"❌ SSM ClientError: {e.response.get('Error', {}).get('Message', str(e))}"
        )
    except BotoCoreError as e:
        print(f"❌ BotoCoreError in SSM: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error in get_secret: {str(e)}")

    return None
