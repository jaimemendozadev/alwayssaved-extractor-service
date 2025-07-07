from typing import TypedDict


class FilePayload(TypedDict):
    s3_key: str
    file_id: str


class s3MediaUpload(TypedDict):
    s3_key: str
    note_id: str
    user_id: str


class BaseFilePayload(TypedDict):
    user_id: str
    note_id: str
    file_name: str


class ExtractorStatus(TypedDict):
    s3_key: str
    status: str
    mp3_file_name: str
    transcript_file_name: str
