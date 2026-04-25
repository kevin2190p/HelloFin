FROM python:3.11-slim

# Hugging Face Spaces requires the container to run as UID 1000.
# This block also keeps it compatible with docker-compose (which doesn't care).
RUN useradd -m -u 1000 user
WORKDIR /app

# System deps for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

# Create writable directories for audio + logs
RUN mkdir -p /app/audios /app/logs && chown -R user:user /app

USER user

# Listen on $PORT if provided (HF Spaces sets it to 7860), else 8000 for docker-compose.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
