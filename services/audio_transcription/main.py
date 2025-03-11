import os

import whisper


def transcribe_audio_file(video_title: str, whisper_model: whisper.model) -> str | None:
    transcript_name = f"{video_title}.txt"

    mp3_file_name = f"{video_title}.mp3"
    mp3_file_abs_path = os.path.abspath(mp3_file_name)

    result = whisper_model.transcribe(mp3_file_abs_path, fp16=False)

    with open(file=transcript_name, mode="w", encoding="utf-8") as file:
        file.write(result["text"])
        print(f"✅ Audio successfully transcribed: {video_title}")
        return video_title

    return None
