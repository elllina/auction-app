"""
Copart scraper — uses the internal XHR search API discovered via DevTools.
No Selenium needed: pure HTTP via requests + session cookies from login.
"""

import os
import time
import json
import logging
from datetime import datetime
from typing import Generator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

COPART_BASE      = "https://www.copart.com"
LOGIN_URL        = f"{COPART_BASE}/public/login"
LOGIN_POST_URL   = f"{COPART_BASE}/public/login"
SEARCH_URL       = f"{COPART_BASE}/public/lots/search"

PAGE_SIZE        = 100          # max Copart allows
MAX_RETRIES      = 3
RETRY_DELAY      = 10           # seconds between retries
REQUEST_DELAY    = 1.5          # polite delay between pages

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": COPART_BASE,
    "Referer": f"{COPART_BASE}/lotSearchResults",
    "X-Requested-With": "XMLHttpRequest",
}


# ── Session setup ─────────────────────────────────────────────────────────────

def _make_session(proxy_cfg: dict | None) -> requests.Session:
    """Create a requests.Session with retry logic and optional proxy."""
    session = requests.Session()

    retry = Retry(
        total=0,                  # we handle retries ourselves
        backoff_factor=0,
        status_forcelist=[],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    if proxy_cfg and proxy_cfg.get("host"):
        host = proxy_cfg["host"]
        port = proxy_cfg.get("port", "80")
        user = proxy_cfg.get("user", "")
        pwd  = proxy_cfg.get("pass", "")

        if user and pwd:
            proxy_url = f"http://{user}:{pwd}@{host}:{port}"
        else:
            proxy_url = f"http://{host}:{port}"

        session.proxies = {"http": proxy_url, "https": proxy_url}
        log.info("Proxy configured: %s:%s", host, port)

    session.headers.update(HEADERS_BASE)
    return session


# ── Authentication ────────────────────────────────────────────────────────────

def _login(session: requests.Session, email: str, password: str) -> None:
    """
    Authenticate against Copart.
    1. GET /public/login  → obtain CSRF token (XSRF-TOKEN cookie)
    2. POST /public/login → establish authenticated session
    """
    log.info("Logging in as %s …", email)

    # Step 1: load login page to get CSRF token
    resp = session.get(LOGIN_URL, timeout=30)
    resp.raise_for_status()

    xsrf = session.cookies.get("XSRF-TOKEN", "")
    if not xsrf:
        # try header
        xsrf = resp.headers.get("X-XSRF-TOKEN", "")

    # Step 2: POST credentials
    payload = {
        "username": email,
        "password": password,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-XSRF-TOKEN": xsrf,
    }
    resp = session.post(
        LOGIN_POST_URL,
        data=payload,
        headers=headers,
        timeout=30,
        allow_redirects=True,
    )
    resp.raise_for_status()

    # Verify we got a session cookie
    if "G2JSESSIONID" not in session.cookies and "g2usersessionid" not in session.cookies:
        log.warning("Login may have failed — no session cookie found. Proceeding anyway.")
    else:
        log.info("Login successful")


# ── Search helpers ────────────────────────────────────────────────────────────

def _build_search_payload(query: str, page: int) -> dict:
    """Build the form-encoded payload that mirrors what the Copart UI sends."""
    return {
        "query":           f'["{query}"]',
        "filter":          "{}",
        "sort":            '["relevancy desc","auction_date_type desc","auction_date_utc asc"]',
        "page":            str(page),
        "size":            str(PAGE_SIZE),
        "start":           str(page * PAGE_SIZE),
        "watchListOnly":   "false",
        "freeFormSearch":  "true",
        "defaultSort":     "false",
        "hideImages":      "false",
        "rawParams":       "{}",
    }


def _search_page(
    session: requests.Session,
    query: str,
    page: int,
) -> dict:
    """POST one search page; returns the parsed JSON."""
    xsrf = session.cookies.get("XSRF-TOKEN", "")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-XSRF-TOKEN": xsrf,
    }
    payload = _build_search_payload(query, page)

    resp = session.post(
        SEARCH_URL,
        data=payload,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _search_page_with_retry(
    session: requests.Session,
    query: str,
    page: int,
) -> dict:
    """Wrap _search_page with MAX_RETRIES attempts."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _search_page(session, query, page)
        except Exception as exc:
            last_err = exc
            log.warning(
                "Search page %d attempt %d/%d failed: %s",
                page, attempt, MAX_RETRIES, exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise RuntimeError(f"Search page {page} failed after {MAX_RETRIES} attempts") from last_err


# ── Public API ────────────────────────────────────────────────────────────────

def scrape_copart(
    queries: list[str] | None = None,
    proxy_cfg: dict | None = None,
) -> Generator[dict, None, None]:
    """
    Authenticate, then paginate through all results for each query.
    Yields raw lot dicts (as returned by Copart API).

    Args:
        queries:   List of free-text search queries.
                   Defaults to [""] (all lots) — beware: millions of results.
        proxy_cfg: Optional dict with host/port/user/pass keys.
    """
    email    = os.environ["COPART_EMAIL"]
    password = os.environ["COPART_PASSWORD"]

    if queries is None:
        queries = [""]          # empty = browse all

    session = _make_session(proxy_cfg)

    # ── Login ──────────────────────────────────────────────────────────────
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _login(session, email, password)
            break
        except Exception as exc:
            log.warning("Login attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_DELAY)

    # ── Paginate each query ────────────────────────────────────────────────
    for query in queries:
        log.info("Searching Copart for: %r", query or "(all)")
        page           = 0
        total_yielded  = 0

        while True:
            data = _search_page_with_retry(session, query, page)

            if data.get("returnCode") != 1:
                log.error("Unexpected returnCode: %s", data.get("returnCode"))
                break

            results    = data["data"]["results"]
            content    = results.get("content", [])
            total_elems = results.get("totalElements", 0)

            if not content:
                log.info("Query %r: no more lots (page %d)", query or "(all)", page)
                break

            for lot in content:
                yield lot
                total_yielded += 1

            log.info(
                "Query %r: page %d — %d lots fetched (%d / %d total)",
                query or "(all)", page, len(content), total_yielded, total_elems,
            )

            # Stop if we've fetched everything
            if total_yielded >= total_elems or len(content) < PAGE_SIZE:
                break

            page += 1
            time.sleep(REQUEST_DELAY)
