import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Dict, List

import boto3
import yt_dlp
from botocore.exceptions import BotoCoreError, ClientError
from bson.objectid import ObjectId
from dotenv import load_dotenv

from services.aws.ssm import get_secret

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient

youtube_url = ""
s3_video_url = ()


shorter_videos: List[str] = []

s3_video_list: List[str] = []

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
sqs_client: "SQSClient" = boto3.client("sqs", region_name=AWS_REGION)


load_dotenv()


def _generate_fake_sqs_msg(python_mode: str) -> Dict[str, Any]:

    fake_payload: Dict[str, Any] = {"Messages": []}

    user_id = str(ObjectId())

    fake_payload["Messages"].append(
        {
            "MessageId": str(uuid.uuid4()),
            "ReceiptHandle": str(uuid.uuid4()),
            "Body": json.dumps(
                {
                    "user_id": user_id,
                    "media_uploads": [
                        {
                            "note_id": str(ObjectId()),
                            "user_id": user_id,
                            "s3_key": (
                                youtube_url
                                if python_mode == "development"
                                else s3_video_url
                            ),
                        }
                    ],
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
        user_id = str(ObjectId())

        test_payload = {
            "user_id": user_id,
            "media_uploads": [
                {
                    "note_id": str(ObjectId()),
                    "user_id": user_id,
                    "s3_key": test_s3_url,
                }
            ],
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


def _download_video_from_url(
    video_url: str,
) -> None:

    try:
        print("📥 Downloading full MP4 from YouTube...")

        ydl_opts: Dict[str, Any] = {
            "format": "best[ext=mp4]/best",  # enforce a usable mp4 file
            "merge_output_format": "mp4",
            "outtmpl": "%(title)s.%(ext)s",  # still saves with YouTube title
            "quiet": False,
            "noplaylist": True,
            "ignoreerrors": True,
            "nopart": True,
            "overwrites": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

            # This gives you the actual, real filepath yt-dlp saved to
            output_path = info.get("requested_downloads", [{}])[0].get("filepath")

        if not output_path or not os.path.exists(output_path):
            raise yt_dlp.DownloadError(f"❌ Full MP4 not downloaded: {output_path}")

        print(f"✅ Downloaded video: {output_path}")

    except yt_dlp.DownloadError as e:
        print(f"❌ yt-dlp Error in download_video_or_audio: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error in download_video_or_audio: {e}")

    return None


def _get_youtube_videos(youtube_urls: List[str]):
    for url in youtube_urls:
        print(f"🚀 Initiate {url} download...")
        _download_video_from_url(url)
