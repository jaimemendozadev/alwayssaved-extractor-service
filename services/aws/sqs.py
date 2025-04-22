import json
import os
from typing import TypedDict

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from bson import ObjectId

from services.aws.ssm import get_secret


class EmbeddingPayload(TypedDict):
    _id: ObjectId
    transcriptURL: str


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
sqs_client = boto3.client("sqs", region_name=AWS_REGION)


def send_embedding_sqs_message(sqs_payload: EmbeddingPayload):
    """Sends a message to the SQS embedding_push_queue indicating the transcript is ready for embedding process."""

    embedding_push_queue_url = get_secret("/notecasts/EMBEDDING_PUSH_QUEUE_URL")

    if not embedding_push_queue_url:
        print("⚠️ ERROR: SQS Queue URL not set!")
        return

    try:
        # Serialize _id if it's an ObjectId
        payload_json = json.dumps(
            {
                **sqs_payload,
                "_id": str(sqs_payload["_id"]),
            }
        )

        response = sqs_client.send_message(
            QueueUrl=embedding_push_queue_url,
            MessageBody=payload_json,
        )

        print(f"✅ SQS Message Sent! Message ID: {response['MessageId']}")

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending SQS message: {e.response['Error']['Message']}"
        )

    except BotoCoreError as e:
        print(f"❌ Boto3 Internal Error: {str(e)}")

    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
