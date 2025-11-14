# ================================
# Stage 1: Base dependencies
# ================================
FROM python:3.11-slim-bookworm AS base

# Workdir
WORKDIR /app

# Avoid writing .pyc files and enable immediate flush
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system deps (ffmpeg required)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y git

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (core only — no WhisperX)
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire app
COPY . .

# Inject version (default "dev"; overwritten at build time)
ARG VERSION="dev"
RUN echo "{\"version\": \"${VERSION}\"}" > version.json


# ================================
# Stage 2: Image WITH WhisperX
# ================================
FROM base AS with_whisperx

# Install CPU PyTorch + WhisperX
RUN pip install --no-cache-dir \
    torch==2.2.2+cpu \
    torchaudio==2.2.2+cpu \
    -f https://download.pytorch.org/whl/torch_stable.html \
    && pip install --no-cache-dir whisperx==3.1.1

# Indicate WhisperX is available
ENV DEMO_AVAILABLE=1

# Expose API port
EXPOSE 8000

# Start backend
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]


# ================================
# Stage 3: Image WITHOUT WhisperX
# ================================
FROM base AS without_whisperx

# WhisperX disabled
ENV DEMO_AVAILABLE=0

# Expose API port
EXPOSE 8000

# Start backend
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
