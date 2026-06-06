import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Environment variables ────────────────────────────────────────────────────

DATABASE_URL     = os.environ['DATABASE_URL']

PROXY_HOST       = os.environ.get('PROXY_HOST', '')
PROXY_PORT       = os.environ.get('PROXY_PORT', '80')
PROXY_USER       = os.environ.get('PROXY_USER', '')
PROXY_PASS       = os.environ.get('PROXY_PASS', '')

COPART_EMAIL     = os.environ['COPART_EMAIL']
COPART_PASSWORD  = os.environ['COPART_PASSWORD']

IAAI_EMAIL       = os.environ['IAAI_EMAIL']
IAAI_PASSWORD    = os.environ['IAAI_PASSWORD']

# ── Helpers ──────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}", flush=True)


def get_proxy_config() -> dict | None:
    if not PROXY_HOST:
        return None
    return {
        'host': PROXY_HOST,
        'port': PROXY_PORT,
        'user': PROXY_USER,
        'pass': PROXY_PASS,
    }

# ── Scrapers ─────────────────────────────────────────────────────────────────

def scrape_copart() -> int:
    """Scrape Copart listings. Returns number of lots scraped."""
    log("Copart scraper starting...")
    proxy = get_proxy_config()
    # TODO: implement Copart login + search with Selenium
    lots_scraped = 0
    log(f"Copart: {lots_scraped} lots scraped")
    return lots_scraped


def scrape_iaai() -> int:
    """Scrape IAAI listings. Returns number of lots scraped."""
    log("IAAI scraper starting...")
    proxy = get_proxy_config()
    # TODO: implement IAAI login + search with Selenium
    lots_scraped = 0
    log(f"IAAI: {lots_scraped} lots scraped")
    return lots_scraped

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    log("=" * 50)
    log("Scraper started")
    log(f"Database: {DATABASE_URL.split('@')[-1]}")  # log host only, not credentials
    log(f"Proxy: {PROXY_HOST}:{PROXY_PORT}" if PROXY_HOST else "Proxy: none")
    log("=" * 50)

    total = 0

    try:
        copart_count = scrape_copart()
        total += copart_count
    except Exception as e:
        log(f"Copart ERROR: {e}")

    try:
        iaai_count = scrape_iaai()
        total += iaai_count
    except Exception as e:
        log(f"IAAI ERROR: {e}")

    log("=" * 50)
    log(f"{total} lots scraped in total")
    log("Done")
    log("=" * 50)


if __name__ == '__main__':
    main()
