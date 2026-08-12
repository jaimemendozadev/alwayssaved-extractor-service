import json
import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Dict, List

import boto3
import whisper
import yt_dlp
from botocore.exceptions import BotoCoreError, ClientError
from bson.objectid import ObjectId
from dotenv import load_dotenv

from services.aws.ssm import get_secret
from services.utils.main import format_timestamp

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient

youtube_url = ""
s3_video_url = ()


shorter_videos: List[str] = []

s3_video_list: List[str] = []

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
sqs_client: "SQSClient" = boto3.client("sqs", region_name=AWS_REGION)

# dev_utils/main.py lives at <project_root>/dev_utils/main.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_DIR = os.path.expanduser("~/Downloads")

WHISPER_MODEL_NAME = "base"


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


def _resolve_media_path(file_name_or_path: str) -> str:
    """
    Looks up a media file by absolute path, then in the project root,
    then in ~/Downloads. Raises FileNotFoundError if none match.
    """

    if os.path.isabs(file_name_or_path) and os.path.exists(file_name_or_path):
        return file_name_or_path

    project_root_path = os.path.join(PROJECT_ROOT, file_name_or_path)
    if os.path.exists(project_root_path):
        return project_root_path

    downloads_path = os.path.join(DOWNLOADS_DIR, file_name_or_path)
    if os.path.exists(downloads_path):
        return downloads_path

    raise FileNotFoundError(
        f"❌ Could not find '{file_name_or_path}' in project root or ~/Downloads."
    )


def _mp4_to_mp3_keep_original(mp4_abs_path: str) -> str:
    """
    Converts an .mp4 file to .mp3 via ffmpeg WITHOUT deleting the source .mp4.
    Writes the .mp3 alongside the .mp4 (same directory).
    """

    base_title, _ = os.path.splitext(mp4_abs_path)
    mp3_abs_path = f"{base_title}.mp3"

    command = [
        "ffmpeg",
        "-i",
        mp4_abs_path,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ab",
        "192k",
        "-y",
        mp3_abs_path,
    ]

    subprocess.run(command, check=True)

    return mp3_abs_path


def transcribe_local_media(
    file_name_or_path: str, include_timestamps: bool = True
) -> str | None:
    """
    Accepts a local .mp4 or .mp3 file (bare filename, or full path).
      - .mp4 files are converted to .mp3 (source .mp4 is kept).
      - .mp3 files are used as-is.
    Transcribes the resulting .mp3 with Whisper and writes a timestamped
    .txt transcript to the project root. Nothing is deleted. Returns the
    transcript's abs path, or None on failure.
    """

    try:
        media_path = _resolve_media_path(file_name_or_path)

        base_filename = os.path.basename(media_path)
        file_name, file_extension = os.path.splitext(base_filename)

        if file_extension == ".mp4":
            print(f"🎬 Converting {base_filename} to .mp3 (keeping original .mp4)...")
            mp3_abs_path = _mp4_to_mp3_keep_original(media_path)
        elif file_extension == ".mp3":
            mp3_abs_path = media_path
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")

        if not os.path.exists(mp3_abs_path):
            raise FileNotFoundError(f"❌ Expected mp3 not found: {mp3_abs_path}")

        print(f"🧠 Loading Whisper model '{WHISPER_MODEL_NAME}'...")
        model = whisper.load_model(WHISPER_MODEL_NAME)

        print(f"📝 Transcribing {mp3_abs_path}...")
        result = model.transcribe(mp3_abs_path, fp16=False)

        transcript_abs_path = os.path.join(PROJECT_ROOT, f"{file_name}.txt")

        with open(transcript_abs_path, mode="w", encoding="utf-8") as file:
            if include_timestamps:
                for segment in result["segments"]:
                    line_timestamp = format_timestamp(segment["start"])
                    line_text = segment["text"].strip()
                    file.write(f"{line_timestamp}: {line_text}\n")
            else:
                file.write(result["text"])

        print(f"✅ Transcript saved: {transcript_abs_path}")
        return transcript_abs_path

    except Exception as e:
        print(f"❌ Error in transcribe_local_media: {e}")
        return None


# _get_youtube_videos(["https://www.youtube.com/watch?v=x2VHFgyawPE"])

# Example usage:
# transcribe_local_media("my_video.mp4")             # project root or ~/Downloads, timestamps on
# transcribe_local_media("my_audio.mp3", False)       # plain text, no timestamps
# transcribe_local_media("/absolute/path/clip.mp4")   # full path also works
