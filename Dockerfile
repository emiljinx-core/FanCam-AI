FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FORCE_CPU=1

# FFmpeg is required for audio muxing; libgomp1 is needed by PyTorch/OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgomp1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only PyTorch first so the image stays much smaller.
COPY backend/requirements.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision \
 && pip install -r requirements.txt

# Includes yolov8n.pt, app code, and the OSNet weights in /app/weights.
COPY backend/ /app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
