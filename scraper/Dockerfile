FROM python:3.11-slim

WORKDIR /app

# Paths are relative to /scraper (Railway root directory for this service)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

# Env vars injected by Railway at runtime only — never at build time
CMD ["python", "run_scraper.py"]
