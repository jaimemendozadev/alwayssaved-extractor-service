# CUDA 11.8 + cuDNN8 — matches the NVIDIA drivers on AWS Deep Learning AMI
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/.cache
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Python 3.11 is in ubuntu 22.04 universe repo; ffmpeg required by whisper
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository universe \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project manifest and lockfile before source (maximize layer cache)
COPY pyproject.toml uv.lock ./

# Install production deps into /app/.venv
RUN uv sync --frozen --no-dev --python python3.11

# Install GPU PyTorch INTO the project venv (not system Python)
# Must target the venv uv sync just created, not the system interpreter
RUN uv pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu118 \
    --python /app/.venv/bin/python

COPY . .

CMD ["uv", "run", "python", "service.py"]
