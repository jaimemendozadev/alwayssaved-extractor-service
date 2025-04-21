import os
import re

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


def WHITESPACE_HANDLER(k):
    return re.sub("\s+", " ", re.sub("\n+", " ", k.strip()))

MODEL_NAME = "csebuetnlp/mT5_multilingual_XLSum"
# TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME)
TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)


def summarize_transcript(video_title: str) -> str | None:

    if video_title is None:
        return None

    transcript_file_name = f"{video_title}.txt"
    file_abs_path = os.path.abspath(transcript_file_name)

    input_ids = TOKENIZER(
        [WHITESPACE_HANDLER(file_abs_path)],
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=512,
    )["input_ids"]

    output_ids = model.generate(
        input_ids=input_ids, max_length=84, no_repeat_ngram_size=2, num_beams=4
    )[0]

    summary = TOKENIZER.decode(
        output_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )

    print(f"transcript summary {summary}")
    print("\n")

    return summary
