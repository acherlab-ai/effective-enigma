# Bringh Bot Dockerfile for Railway
# ====================================

# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR=off

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# For EasyOCR (if used)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu 2>/dev/null || echo "PyTorch install skipped"
RUN pip install --no-cache-dir easyocr 2>/dev/null || echo "EasyOCR install skipped"

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Expose ports
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080').raise_for_status()" || exit 1

# Start both bot and admin
# Note: For production, you might want to use a process manager like supervisord
# But for Railway, we'll use a simple shell script
CMD ["/bin/bash", "-c", "python bot/app.py & python admin/app.py & wait"]
