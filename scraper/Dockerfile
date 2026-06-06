FROM python:3.11-slim

# Install Chromium and ChromeDriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY scraper/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy scraper source
COPY scraper/ ./

# Env vars are injected by Railway at runtime — never at build time
CMD ["python", "run_scraper.py"]
