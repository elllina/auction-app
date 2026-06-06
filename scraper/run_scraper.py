"""
run_scraper.py — Entry point for the Railway cron job.

Flow:
  1. Validate env vars
  2. Test DB connection
  3. Copart: scrape → normalize → write to DB
  4. (IAAI: stub, to be implemented)
  5. Print summary
"""

import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
import psycopg2

load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scraper")

# ── Environment ───────────────────────────────────────────────────────────────

DATABASE_URL    = os.environ.get("DATABASE_URL", "")
PROXY_HOST      = os.environ.get("PROXY_HOST", "")
PROXY_PORT      = os.environ.get("PROXY_PORT", "80")
PROXY_USER      = os.environ.get("PROXY_USER", "")
PROXY_PASS      = os.environ.get("PROXY_PASS", "")
COPART_EMAIL    = os.environ.get("COPART_EMAIL", "")
COPART_PASSWORD = os.environ.get("COPART_PASSWORD", "")

# Comma-separated search queries, e.g. "bmw m3,audi rs,mercedes amg"
# Leave blank to scrape everything (very slow — millions of results)
COPART_QUERIES  = [
    q.strip()
    for q in os.environ.get("COPART_QUERIES", "bmw,audi,mercedes,toyota,honda").split(",")
    if q.strip()
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _get_proxy_cfg() -> dict | None:
    if not PROXY_HOST:
        return None
    return {
        "host": PROXY_HOST,
        "port": PROXY_PORT,
        "user": PROXY_USER,
        "pass": PROXY_PASS,
    }


def _test_db() -> bool:
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        log.info("DB connected ✓")
        return True
    except Exception as exc:
        log.error("DB connection failed: %s", exc)
        return False


def _validate_env() -> bool:
    missing = []
    if not DATABASE_URL:
        missing.append("DATABASE_URL")
    if not COPART_EMAIL:
        missing.append("COPART_EMAIL")
    if not COPART_PASSWORD:
        missing.append("COPART_PASSWORD")
    if missing:
        log.error("Missing required env vars: %s", ", ".join(missing))
        return False
    return True


# ── Scrapers ──────────────────────────────────────────────────────────────────

def run_copart() -> tuple[int, int]:
    """
    Scrape Copart → normalize → upsert.
    Returns (inserted, updated).
    """
    from copart_scraper import scrape_copart
    from normalizer    import normalize_copart_lot
    from db_writer     import upsert_lots_chunked

    proxy_cfg = _get_proxy_cfg()
    log.info("Copart queries: %s", COPART_QUERIES)

    buffer: list[dict] = []
    total_raw  = 0
    total_ins  = 0
    total_upd  = 0

    for raw_lot in scrape_copart(queries=COPART_QUERIES, proxy_cfg=proxy_cfg):
        total_raw += 1
        try:
            normalized = normalize_copart_lot(raw_lot)
            buffer.append(normalized)
        except Exception as exc:
            log.warning("Normalize error for lot %s: %s", raw_lot.get("lotNumberStr"), exc)
            continue

        # Flush to DB every 200 lots to avoid huge memory usage
        if len(buffer) >= 200:
            ins, upd = upsert_lots_chunked(buffer)
            total_ins += ins
            total_upd += upd
            buffer.clear()

    # Flush remainder
    if buffer:
        ins, upd = upsert_lots_chunked(buffer)
        total_ins += ins
        total_upd += upd

    log.info(
        "Copart done: %d raw lots → %d inserted, %d updated",
        total_raw, total_ins, total_upd,
    )
    return total_ins, total_upd


def run_iaai() -> tuple[int, int]:
    """IAAI scraper — stub, to be implemented."""
    log.info("IAAI scraper: not yet implemented, skipping")
    return 0, 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    start = datetime.now(timezone.utc)

    log.info("=" * 60)
    log.info("Scraper started at %s", start.strftime("%Y-%m-%d %H:%M:%S UTC"))
    db_host = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "???"
    log.info("Database: %s", db_host)
    log.info("Proxy: %s:%s", PROXY_HOST, PROXY_PORT) if PROXY_HOST else log.info("Proxy: none")
    log.info("=" * 60)

    # ── Pre-flight checks ──────────────────────────────────────────────────
    if not _validate_env():
        sys.exit(1)

    if not _test_db():
        log.error("Aborting — cannot connect to database")
        sys.exit(1)

    # ── Run scrapers ───────────────────────────────────────────────────────
    total_ins = 0
    total_upd = 0

    try:
        ins, upd = run_copart()
        total_ins += ins
        total_upd += upd
    except Exception as exc:
        log.error("Copart scraper failed: %s", exc, exc_info=True)

    try:
        ins, upd = run_iaai()
        total_ins += ins
        total_upd += upd
    except Exception as exc:
        log.error("IAAI scraper failed: %s", exc, exc_info=True)

    # ── Summary ────────────────────────────────────────────────────────────
    end     = datetime.now(timezone.utc)
    elapsed = (end - start).total_seconds()

    log.info("=" * 60)
    log.info("Start:    %s", start.strftime("%Y-%m-%d %H:%M:%S UTC"))
    log.info("End:      %s", end.strftime("%Y-%m-%d %H:%M:%S UTC"))
    log.info("Duration: %.1f seconds", elapsed)
    log.info("Result:   %d inserted, %d updated", total_ins, total_upd)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
