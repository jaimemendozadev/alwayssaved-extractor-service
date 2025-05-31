from typing import TypedDict


class FilePayload(TypedDict):
    s3_bucket: str
    s3_key: str


class s3MediaUpload(TypedDict):
    s3_key: str
    note_id: str
    user_id: str
