# ============================================================
# Dockerfile for Daily Telegram Scraper
# ============================================================

FROM python:3.11-slim

# Install system dependencies (tmux for worker sessions)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tmux \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create necessary directories
RUN mkdir -p output/batches output/tmp_batches logs input session

# Default command: run the full scraper pipeline
CMD ["bash", "run_full_scraper.sh"]
