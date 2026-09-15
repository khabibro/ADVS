FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
ENV PADDLE_OCR_DEVICE=cpu \
    PADDLE_OCR_LANG=korean \
    PADDLE_OCR_REC_MODEL_NAME=korean_PP-OCRv5_mobile_rec \
    PADDLE_OCR_DET_MODEL_NAME=PP-OCRv5_mobile_det \
    PADDLE_OCR_CACHE_DIR=/app/storage/paddleocr-cache \
    PADDLE_PDX_CACHE_HOME=/app/storage/paddleocr-cache
RUN pip install --no-cache-dir ".[dev,paddle]"
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
