# Use official Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  sqlite3 \
  tzdata \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

# Copy project files
COPY . .

# Create logs directory
RUN mkdir -p mailreef_automation/logs logs

# Production launch: all 3 daemons under supervised auto-restart.
#   - IVYBOUND_SUMMER sender   (truckice, 88 inboxes)
#   - BAHAMAS_RETREAT sender   (competitionhand, 80 inboxes)
#   - Bahamas executive scraper (24/7, auto-syncs verified leads to Sheet)
ENV PYTHON_BIN=python3
CMD ["bash", "start_all.sh"]
