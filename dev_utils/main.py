import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from bson.objectid import ObjectId
from dotenv import load_dotenv
from mypy_boto3_sqs import SQSClient

from services.aws.ssm import get_secret

youtube_url = "https://www.youtube.com/watch?v=k82RwXqZHY8"
s3_video_url = "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/How+China%E2%80%99s+New+AI+Model+DeepSeek+Is+Threatening+U.S.+Dominance.mp4"
s3_video_list = [
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/Geoffrey+Hinton+%EF%BD%9C+On+working+with+Ilya%2C+choosing+problems%2C+and+the+power+of+intuition.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/How+China%E2%80%99s+New+AI+Model+DeepSeek+Is+Threatening+U.S.+Dominance.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/Ilya+Sutskever%EF%BC%9A+Deep+Learning+%EF%BD%9C+Lex+Fridman+Podcast+%2394.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/Jensen+Huang%2C+Founder+and+CEO+of+NVIDIA.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/NVIDIA+CEO+Jensen+Huang's+Vision+for+the+Future.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/Palmer+Luckey+Wants+to+Be+Silicon+Valley's+War+King+%EF%BD%9C+The+Circuit.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/The+AI+Arsenal+That+Could+Stop+World+War+III+%EF%BD%9C+Palmer+Luckey+%EF%BD%9C+TED.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/The+Race+to+Harness+Quantum+Computing's+Mind-Bending+Power+%EF%BD%9C+The+Future+With+Hannah+Fry.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/Yann+LeCun%EF%BC%9A+Deep+Learning%2C+ConvNets%2C+and+Self-Supervised+Learning+%EF%BD%9C+Lex+Fridman+Podcast+%2336.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/GM%E2%80%99s+%24280+Billion+Bet+on+EVs+%EF%BD%9C+Mary+Barra+%EF%BD%9C+The+Circuit+with+Emily+Chang.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/When+JPMorgan+CEO+Jamie+Dimon+Speaks%2C+the+World+Listens+%EF%BD%9C+The+Circuit.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/Leading+in+a+Time+of+Change%EF%BC%9A+Jamie+Dimon%2C+Chairman+and+CEO%2C+JP+Morgan+Chase.mp4",
    "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/Leading+in+a+Time+of+Change%EF%BC%9A+Jamie+Dimon%2C+Chairman+and+CEO%2C+JP+Morgan+Chase.mp4",
]

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
sqs_client: SQSClient = boto3.client("sqs", region_name=AWS_REGION)


load_dotenv()


def _generate_fake_sqs_msg(python_mode: str) -> Dict[str, Any]:

    fake_payload: Dict[str, Any] = {"Messages": []}

    fake_payload["Messages"].append(
        {
            "MessageId": str(uuid.uuid4()),
            "Body": json.dumps(
                {
                    "note_id": str(ObjectId()),
                    "user_id": str(ObjectId()),
                    "s3_key": (
                        youtube_url if python_mode == "development" else s3_video_url
                    ),
                }
            ),
        }
    )

    return fake_payload


def _send_one_extractor_sqs_message(test_s3_url: str) -> None:
    extractor_push_queue_url = get_secret("/alwayssaved/EXTRACTOR_PUSH_QUEUE_URL")

    if not extractor_push_queue_url:
        print(
            "⚠️ ERROR in _send_one_extractor_sqs_message: EXTRACTOR_PUSH_QUEUE_URL not set!"
        )
        return

    if not test_s3_url:
        print("⚠️ ERROR in _send_one_extractor_sqs_message: Missing s3_url")
        return

    try:
        test_payload = {
            "note_id": ObjectId(),
            "user_id": ObjectId(),
            "s3_key": test_s3_url,
        }

        print(f"sending test_payload to Extractor Service: {test_payload} \n")

        response = sqs_client.send_message(
            QueueUrl=extractor_push_queue_url,
            MessageBody=json.dumps(test_payload),
        )

        print(f"✅ Test SQS Message Sent! Message ID: {response['MessageId']} \n")

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending Test SQS message: {e.response['Error']['Message']} \n"
        )

    except BotoCoreError as e:
        print(
            f"❌ Boto3 Internal Error in send_test_extractor_sqs_message: {str(e)} \n"
        )

    except Exception as e:
        print(f"❌ Unexpected Error in send_test_extractor_sqs_message: {str(e)} \n")


def _upload_test_sqs_messages_to_extractor_queue(s3_urls: List[str]) -> None:

    if len(s3_urls) < 1:
        print(
            "⚠️ ERROR in _upload_test_sqs_messages_to_extractor_queue: s3_urls List is empty"
        )
        return

    try:
        with ThreadPoolExecutor() as executor:
            executor.map(_send_one_extractor_sqs_message, s3_urls)

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending Test SQS message: {e.response['Error']['Message']} \n"
        )

    except BotoCoreError as e:
        print(
            f"❌ Boto3 Internal Error in send_test_extractor_sqs_message: {str(e)} \n"
        )

    except Exception as e:
        print(f"❌ Unexpected Error in send_test_extractor_sqs_message: {str(e)} \n")
