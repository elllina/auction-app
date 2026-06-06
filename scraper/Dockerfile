FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY scraper/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy scraper source
COPY scraper/ ./

# Env vars injected by Railway at runtime only — never at build time
CMD ["python", "run_scraper.py"]
