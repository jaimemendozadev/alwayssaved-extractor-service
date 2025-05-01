import os
import re

import torch
from transformers import BartForConditionalGeneration, BartTokenizer

MODEL_NAME = "facebook/bart-large-cnn"
tokenizer = BartTokenizer.from_pretrained(MODEL_NAME)

# Detect device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = BartForConditionalGeneration.from_pretrained(MODEL_NAME).to(
    DEVICE
)  # Move model to GPU if available


def whitespace_handler(k):
    return re.sub("\s+", " ", re.sub("\n+", " ", k.strip()))


def summarize_transcript(video_title: str) -> str:

    if video_title is None:
        return ""

    transcript_file_name = f"{video_title}.txt"
    file_abs_path = os.path.abspath(transcript_file_name)

    with open(file_abs_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    inputs = tokenizer(
        [whitespace_handler(transcript_text)],
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=1024,
    )

    # 🧠 Only move tensors if running on CUDA
    if DEVICE == "cuda":
        inputs = {key: value.to(DEVICE) for key, value in inputs.items()}

    summary_ids = model.generate(
        inputs["input_ids"],
        num_beams=4,
        max_length=300,  # ⬆️ allows more content
        min_length=120,  # ⬆️ avoids 2-3 sentence summaries
        no_repeat_ngram_size=3,  # ⬆️ smoother output
        early_stopping=True,
    )
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    return summary
