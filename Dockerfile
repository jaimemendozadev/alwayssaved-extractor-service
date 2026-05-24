# Base image with CUDA 11.8 and cuDNN — matches the NVIDIA drivers on AWS Deep Learning AMI ami-0260c4d597dcc8641
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/.cache
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV UV_PYTHON=python3.11
ENV UV_NO_CACHE=1

# Install Python 3.11 and ffmpeg (required by openai-whisper and ffmpeg-python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy lockfile and project manifest before source to maximize layer caching
COPY pyproject.toml uv.lock ./

# Install only production dependencies from pyproject.toml (no dev group)
RUN uv sync --frozen --no-dev --python 3.11

# Install GPU-enabled PyTorch — separate index URL required, not in pyproject.toml
RUN uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --python 3.11

COPY . .

CMD ["uv", "run", "service.py"]
