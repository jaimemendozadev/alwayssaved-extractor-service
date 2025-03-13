import json
import os

import boto3

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

sqs_client = boto3.client("sqs", region_name=AWS_REGION)


def send_sqs_message(s3_transcript_url: str):
    """Sends a message to the SQS queue indicating the transcript is ready."""

    EXTRACTOR_PUSH_QUEUE_URL = os.getenv("EXTRACTOR_PUSH_QUEUE_URL")

    if not EXTRACTOR_PUSH_QUEUE_URL:
        print("⚠️ ERROR: SQS Queue URL not set!")
        return

    message_body = {"s3_transcript_url": s3_transcript_url}

    try:
        response = sqs_client.send_message(
            QueueUrl=EXTRACTOR_PUSH_QUEUE_URL, MessageBody=json.dumps(message_body)
        )
        print(f"✅ SQS Message Sent! Message ID: {response['MessageId']}")
    except Exception as e:
        print(f"❌ ERROR sending SQS message: {e}")
