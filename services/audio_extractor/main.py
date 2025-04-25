import os
import re
import subprocess
from typing import Any, Dict

import yt_dlp

from services.aws.ssm import get_secret


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()


def convert_mp4_to_mp3(mp4_path: str, video_title: str) -> str:
    sanitized_title = sanitize_filename(video_title)
    mp3_file = f"{sanitized_title}.mp3"

    if not os.path.exists(mp4_path):
        raise FileNotFoundError(f"❌ MP4 file not found: {mp4_path}")

    print("🎧 Extracting audio from MP4 using ffmpeg...")

    command = [
        "ffmpeg",
        "-i",
        mp4_path,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ab",
        "192k",
        "-y",
        mp3_file,
    ]

    subprocess.run(command, check=True)
    print(f"✅ Audio extracted to: {mp3_file}")

    return sanitized_title


def download_video_or_audio(video_url: str, dev_mode: bool = False) -> str | None:
    """
    DEV MODE: Download full .mp4, convert to .mp3, return path to .mp3
    PROD MODE: Download .mp3 directly using yt_dlp
    """

    try:
        if dev_mode:
            print("📥 [DEV MODE] Downloading full MP4 from YouTube...")

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
                video_title = info.get("title", "unknown_video")

            print(f"video_title: {video_title}")
            print(f"output_path: {output_path}")
            print(f"os.path.exists(output_path): {os.path.exists(output_path)}")

            if not output_path or not os.path.exists(output_path):
                raise yt_dlp.DownloadError(f"❌ Full MP4 not downloaded: {output_path}")

            print(f"✅ Downloaded video: {output_path}")
            sanitized_title = convert_mp4_to_mp3(output_path, video_title)
            return sanitized_title

        else:
            print("🏭 [PROD MODE] Downloading MP3 audio only...")

            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "outtmpl": "%(title)s.%(ext)s",
                "quiet": False,
                "noplaylist": True,
                "ignoreerrors": True,
                "nopart": True,
                "overwrites": True,
            }

            bucket_name = get_secret("/notecasts/AWS_BUCKET")
            if not bucket_name:
                raise ValueError("AWS_BUCKET not set in SSM.")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                video_title = sanitize_filename(info.get("title", "unknown_video"))

            mp3_path = f"{video_title}.mp3"
            if not os.path.exists(mp3_path):
                raise yt_dlp.DownloadError("❌ MP3 not downloaded.")

            print(f"✅ Audio downloaded: {mp3_path}")
            return video_title

    except yt_dlp.DownloadError as e:
        print(f"❌ yt-dlp Error: {e}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg failed to extract audio: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return None
