# ============================================================
# Dockerfile for Daily Telegram Scraper
# ============================================================

# ---------- Stage 1: build the React control panel ----------
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python app ----------
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

# Built control panel (served by `python3 -m web`)
COPY --from=frontend /frontend/dist ./frontend/dist

# Create necessary directories
RUN mkdir -p output/batches output/tmp_batches logs input session

# Default command: run the full scraper pipeline
CMD ["bash", "run_full_scraper.sh"]
