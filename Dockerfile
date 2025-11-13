# --- Stage 1: Base dependencies ---
FROM python:3.11-slim-bookworm AS base

# Set the working directory in the container
WORKDIR /app

# Install FFmpeg (required for audio processing)
# Also install git for whisperx dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the core requirements file
COPY requirements.txt .

# Install core dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# --- Stage 2: Build with WhisperX support ---
FROM base AS with_whisperx

# Install PyTorch (CPU-only for broader compatibility in Docker) and torchaudio
# Then install whisperx
RUN pip install --no-cache-dir \
    torch==2.2.2+cpu \
    torchaudio==2.2.2+cpu \
    -f https://download.pytorch.org/whl/torch_stable.html \
    && pip install --no-cache-dir whisperx==3.1.1

# Set environment variable to enable demo features
ENV DEMO_AVAILABLE=1

# Expose the port that Gunicorn will listen on
EXPOSE 8000

# Run gunicorn to serve the Flask application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]

# --- Stage 3: Build without WhisperX support ---
FROM base AS without_whisperx

# Set environment variable to disable demo features
ENV DEMO_AVAILABLE=0

# Expose the port that Gunicorn will listen on
EXPOSE 8000

# Run gunicorn to serve the Flask application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]