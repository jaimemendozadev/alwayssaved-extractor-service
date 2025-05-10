from typing import TypedDict


class FilePayload(TypedDict):
    s3_url: str
    s3_key: str
