import json
import os
from typing import TypedDict

import boto3
from bson import ObjectId

from services.aws.ssm import get_secret


class EmbeddingPayload(TypedDict):
    _id: ObjectId
    transcriptURL: str


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

sqs_client = boto3.client("sqs", region_name=AWS_REGION)


def get_sqs_messages():
    """Gets messages from SQS extractor_push_queue to kick off transcription/summarization process."""
    pass


def send_embedding_sqs_message(sqs_payload: EmbeddingPayload):
    """Sends a message to the SQS embedding_push_queue indicating the transcript is ready for embedding process."""

    embedding_push_queue_url = get_secret("/notecasts/EMBEDDING_PUSH_QUEUE_URL")

    if not embedding_push_queue_url:
        print("⚠️ ERROR: SQS Queue URL not set!")
        return

    try:
        response = sqs_client.send_message(
            QueueUrl=embedding_push_queue_url, MessageBody=json.dumps(sqs_payload)
        )
        print(f"✅ SQS Message Sent! Message ID: {response['MessageId']}")

    except Exception as e:
        print(f"❌ ERROR sending SQS embedding_push message: {e}")
