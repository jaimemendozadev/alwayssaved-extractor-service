from typing import Any, Dict

from bson.objectid import ObjectId

youtube_url = "https://www.youtube.com/watch?v=1_gJp2uAjO0"
s3_video_url = "https://notecasts.s3.us-east-1.amazonaws.com/680a6fbcf471715298de5000/Palmer+Luckey+Wants+to+Be+Silicon+Valley's+War+King+%EF%BD%9C+The+Circuit.mp4"


def _generate_fake_sqs_msg(python_mode: str) -> Dict[str, Any]:

    return {
        "userID": ObjectId(),
        "transcriptID": ObjectId(),
        "videoURL": youtube_url if python_mode == "development" else s3_video_url,
    }
