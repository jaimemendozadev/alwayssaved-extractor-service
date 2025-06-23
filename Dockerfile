# Start from NVIDIA's CUDA runtime + Ubuntu 22.04 base image
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/.cache

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-venv \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file first
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN python3 -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install GPU-enabled PyTorch explicitly (must come last to avoid overwrite)
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Copy rest of the application
COPY . .

# Expose ports if needed (optional)
# EXPOSE 8000

# Default command
CMD ["python3", "service.py"]
