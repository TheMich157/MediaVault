# Base image with Python 3.11 Slim
FROM python:3.11-slim

# Install system dependencies (FFmpeg for video/audio processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary runtime directories
RUN mkdir -p /app/downloads/instagram /app/downloads/tiktok /app/data/sessions /app/data/zips

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=3000
ENV PYTHONUNBUFFERED=1

EXPOSE 3000

# Run MediaVault Web Studio
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "3000", "--no-browser"]
