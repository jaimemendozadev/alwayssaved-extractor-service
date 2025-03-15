import os

import boto3

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

ssm_client = boto3.client("ssm", region_name=AWS_REGION)


def get_secret(param_name):
    """Fetches secret from AWS Parameter Store."""

    response = ssm_client.get_parameter(Name=param_name, WithDecryption=True)
    return response["Parameter"]["Value"]
