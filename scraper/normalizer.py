"""
normalizer.py — Maps raw Copart API lot dicts to our Prisma Vehicle schema.

Prisma Vehicle model:
  id            Int            @id @default(autoincrement())
  externalId    String         @unique   ← "COPART-<lotNumberStr>"
  source        AuctionSource            ← "COPART"
  vin           String?                  ← fv  (may be partially masked)
  year          Int?                     ← lcy
  make          String?                  ← mkn
  model         String?                  ← lm
  trim          String?                  ← ltd
  odometer      Int?                     ← orr  (raw odometer reading)
  condition     String?                  ← lcd  (e.g. "RUNS AND DRIVES")
  primaryDamage String?                  ← dd   (e.g. "FRONT END")
  location      String?                  ← yn   (e.g. "MA - NORTH BOSTON")
  saleDate      DateTime?               ← lad  (epoch ms → ISO datetime)
  currentBid    Float?                   ← dynamicLotDetails.currentBid
  buyNowPrice   Float?                   ← bnp  (0 means no buy-now)
  images        String[]                 ← [tims] thumbnail + detail URL pattern
  rawData       Json?                    ← full raw lot dict
  createdAt     DateTime       @default(now())
  updatedAt     DateTime       @updatedAt
"""

from datetime import datetime, timezone


def _epoch_ms_to_iso(epoch_ms: int | float | None) -> str | None:
    """Convert Copart epoch-milliseconds timestamp to ISO-8601 string or None."""
    if not epoch_ms or epoch_ms <= 0:
        return None
    try:
        dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
        return dt.isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def _thumb_to_full(thumb_url: str | None) -> list[str]:
    """
    Copart thumbnail URLs end in _thb.jpg.
    The full-size image is the same URL with _f.jpg.
    Return [thumbnail, full] or [] if no URL.
    """
    if not thumb_url:
        return []
    full_url = thumb_url.replace("_thb.jpg", "_f.jpg")
    return [thumb_url, full_url]


def normalize_copart_lot(raw: dict) -> dict:
    """
    Convert one raw Copart lot dict to a normalised Vehicle dict
    ready for db_writer.upsert().

    Returns a dict matching the Prisma Vehicle model (snake_case, Python types).
    """
    lot_num = str(raw.get("lotNumberStr") or raw.get("ln", ""))

    dynamic   = raw.get("dynamicLotDetails", {})
    current_bid_raw = dynamic.get("currentBid", 0)
    buy_now_raw     = raw.get("bnp", 0)

    odometer_raw = raw.get("orr")          # raw odometer reading
    try:
        odometer = int(float(odometer_raw)) if odometer_raw else None
    except (TypeError, ValueError):
        odometer = None

    try:
        current_bid = float(current_bid_raw) if current_bid_raw else None
    except (TypeError, ValueError):
        current_bid = None

    try:
        buy_now = float(buy_now_raw) if buy_now_raw else None
        if buy_now == 0.0:
            buy_now = None
    except (TypeError, ValueError):
        buy_now = None

    # ── Field mapping ──────────────────────────────────────────────────────
    return {
        "externalId":    f"COPART-{lot_num}",
        "source":        "COPART",
        "vin":           raw.get("fv") or None,
        "year":          raw.get("lcy") or None,
        "make":          raw.get("mkn") or None,
        "model":         raw.get("lm") or None,
        "trim":          raw.get("ltd") or None,
        "odometer":      odometer,
        "condition":     raw.get("lcd") or None,
        "primaryDamage": raw.get("dd") or None,
        "location":      raw.get("yn") or None,
        "saleDate":      _epoch_ms_to_iso(raw.get("lad")),
        "currentBid":    current_bid,
        "buyNowPrice":   buy_now,
        "images":        _thumb_to_full(raw.get("tims")),
        "rawData":       raw,           # store full JSON blob
    }


def normalize_batch(raw_lots: list[dict]) -> list[dict]:
    """Normalize a list of raw lots. Skips lots with no lot number."""
    normalized = []
    for raw in raw_lots:
        if not (raw.get("lotNumberStr") or raw.get("ln")):
            continue
        try:
            normalized.append(normalize_copart_lot(raw))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to normalize lot %s: %s",
                raw.get("lotNumberStr", "?"), exc,
            )
    return normalized
