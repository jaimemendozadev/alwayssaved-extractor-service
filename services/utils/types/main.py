from typing import TypedDict


class FilePayload(TypedDict):
    s3_bucket: str
    s3_key: str
