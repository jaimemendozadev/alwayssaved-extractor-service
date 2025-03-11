import os


def delete_local_file(file_path: str) -> None:
    """Deletes the local MP3 file after uploading to S3."""
    abs_path = os.path.abspath(file_path)
    print(f"🔎 Trying to delete: {abs_path}")

    if os.path.exists(abs_path):
        os.remove(abs_path)
        print(f"🗑️ Deleted {abs_path}")
    else:
        print(f"⚠️ File not found: {abs_path}")
