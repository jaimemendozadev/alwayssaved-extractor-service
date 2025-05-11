import json
import os
from typing import TYPE_CHECKING, Any, Dict, TypedDict

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from bson import ObjectId

from services.aws.ssm import get_secret

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
sqs_client: "SQSClient" = boto3.client("sqs", region_name=AWS_REGION)


def get_extractor_sqs_request() -> Dict[str, Any]:

    extractor_push_queue_url = get_secret("/alwayssaved/EXTRACTOR_PUSH_QUEUE_URL")

    try:
        return sqs_client.receive_message(
            QueueUrl=extractor_push_queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,  # <-- long polling
            VisibilityTimeout=3000,  # <-- 50 mins worst-case processing time
        )

    except ClientError as e:
        print(
            f"❌ SQS ClientError in get_extractor_sqs_request: {e.response.get('Error', {}).get('Message', str(e))}"
        )
    except BotoCoreError as e:
        print(f"❌ BotoCoreError in get_extractor_sqs_request: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error in get_extractor_sqs_request: {str(e)}")

    return {}


class EmbeddingPayload(TypedDict):
    note_id: ObjectId
    transcript_url: str


def send_embedding_sqs_message(sqs_payload: EmbeddingPayload) -> None:
    """Sends a message to the SQS embedding_push_queue indicating the transcript is ready for the embedding process."""

    embedding_push_queue_url = get_secret("/alwayssaved/EMBEDDING_PUSH_QUEUE_URL")

    if not embedding_push_queue_url:
        print("⚠️ ERROR: SQS Queue URL not set!")
        return

    try:
        payload_json = json.dumps(sqs_payload)

        response = sqs_client.send_message(
            QueueUrl=embedding_push_queue_url,
            MessageBody=payload_json,
        )

        print(
            f"✅ SQS Message Sent in send_embedding_sqs_message! Message ID: {response['MessageId']}"
        )

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending SQS message in send_embedding_sqs_message: {e.response['Error']['Message']}"
        )

    except BotoCoreError as e:
        print(f"❌ Boto3 Internal Error in send_embedding_sqs_message: {str(e)}")

    except Exception as e:
        print(f"❌ Unexpected Error in send_embedding_sqs_message: {str(e)}")


def delete_extractor_sqs_message(incoming_sqs_msg: Dict[str, Any]) -> None:
    try:
        extractor_push_queue_url = get_secret("/alwayssaved/EXTRACTOR_PUSH_QUEUE_URL")

        if not extractor_push_queue_url:
            raise ValueError(
                "⚠️ ERROR: SQS Queue URL not set for delete_extractor_sqs_message!"
            )

        receipt_handle = incoming_sqs_msg.get("ReceiptHandle", "")

        if len(receipt_handle) == 0:
            raise ValueError(
                "⚠️ ERROR: Missing ReceiptHandle to delete processed message from Extractor Push Queue!"
            )

        sqs_client.delete_message(
            QueueUrl=extractor_push_queue_url, ReceiptHandle=receipt_handle
        )
        print(
            f"✅ SQS Message Deleted from Extractor Push Queue: {incoming_sqs_msg['MessageId']}"
        )

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending SQS message: {e.response['Error']['Message']}"
        )

    except BotoCoreError as e:
        print(f"❌ Boto3 Internal Error in delete_extractor_sqs_message: {str(e)}")

    except ValueError as e:
        print(f"❌ Unexpected Error in delete_extractor_sqs_message: {str(e)}")
