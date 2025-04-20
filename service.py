"""
Main extractor service file
"""

import asyncio
import os

import boto3
import whisper
from dotenv import load_dotenv

from services.audio_extractor.main import download_audio
from services.audio_transcription.main import transcribe_audio_file
from services.aws.s3 import upload_to_s3
from services.utils.main import _generate_fake_sqs_msg, delete_local_file
from services.utils.mongodb.main import create_mongodb_instance

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

s3_client = boto3.client("s3", region_name=AWS_REGION)
whisper_model = whisper.load_model("turbo")


"""
# Transcript

{
  _id: ObjectId,
  title: String,
  dateCreated: Date,
  dateDeleted: Date,
  videoURL: String,
  audioURL: String,
  transcriptURL: String,
}
"""


async def main():
    mp3_file_name = None
    transcript_file_name = None

    try:
        mongo_db = create_mongodb_instance()
        _fake_sqs_msg = _generate_fake_sqs_msg()

        videoURL = _fake_sqs_msg.get("videoURL")
        userID = _fake_sqs_msg.get("userID")
        transcriptID = _fake_sqs_msg.get("transcriptID")

        video_title = download_audio(videoURL)

        if video_title is None:
            raise ValueError(
                "Video File was not downloaded. Cannot proceed any further."
            )

        mp3_file_name = f"{video_title}.mp3"

        transcript_file_name = transcribe_audio_file(video_title, whisper_model)

        if transcript_file_name is None:
            raise ValueError("Audio was not transcribed. Cannot proceed further")

        base_s3_key = f"{userID}/{transcriptID}"

        uploaded_files = upload_to_s3(s3_client, base_s3_key, video_title)

        if len(uploaded_files) == 0:
            raise ValueError(
                "Transcript and mp3 files were not uploaded to s3. Cannot proceed further"
            )

        delete_local_file(f"{video_title}.mp3")
        delete_local_file(f"{video_title}.txt")

    except ValueError as e:
        if mp3_file_name:
            delete_local_file(mp3_file_name)

        if transcript_file_name:
            delete_local_file(transcript_file_name)

        print(f"❌ Value Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
