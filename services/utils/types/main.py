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
    file_path: str


class ExtractorStatus(TypedDict):
    s3_key: str
    status: str


class s3DownloadConvertResult(TypedDict):
    file_name: str
    file_extension: str
