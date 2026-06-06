"""
db_writer.py — Upsert normalised Vehicle lots into PostgreSQL.

Uses raw psycopg2 (no ORM) so this module has zero Node.js / Prisma dependency.
The table name and column names match what Prisma generates from schema.prisma.

Prisma generates snake_case table names:  "Vehicle"  (quoted, case-sensitive)
Column names match camelCase → snake_case Prisma convention.
"""

import json
import logging
import os
from typing import Sequence

import psycopg2
import psycopg2.extras

log = logging.getLogger(__name__)

# ── Column list (must match Prisma-generated table exactly) ──────────────────
#
# Prisma maps camelCase field names → snake_case column names in PostgreSQL:
#   externalId    → "externalId"     (Prisma keeps camel in Postgres by default)
#
# Actually Prisma keeps camelCase column names in Postgres unless you use
# @map(). So we use the exact field names from schema.prisma.

_UPSERT_SQL = """
INSERT INTO "Vehicle" (
    "externalId",
    "source",
    "vin",
    "year",
    "make",
    "model",
    "trim",
    "odometer",
    "condition",
    "primaryDamage",
    "location",
    "saleDate",
    "currentBid",
    "buyNowPrice",
    "images",
    "rawData",
    "createdAt",
    "updatedAt"
)
VALUES (
    %(externalId)s,
    %(source)s,
    %(vin)s,
    %(year)s,
    %(make)s,
    %(model)s,
    %(trim)s,
    %(odometer)s,
    %(condition)s,
    %(primaryDamage)s,
    %(location)s,
    %(saleDate)s::timestamptz,
    %(currentBid)s,
    %(buyNowPrice)s,
    %(images)s,
    %(rawData)s::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT ("externalId") DO UPDATE SET
    "vin"          = EXCLUDED."vin",
    "year"         = EXCLUDED."year",
    "make"         = EXCLUDED."make",
    "model"        = EXCLUDED."model",
    "trim"         = EXCLUDED."trim",
    "odometer"     = EXCLUDED."odometer",
    "condition"    = EXCLUDED."condition",
    "primaryDamage"= EXCLUDED."primaryDamage",
    "location"     = EXCLUDED."location",
    "saleDate"     = EXCLUDED."saleDate",
    "currentBid"   = EXCLUDED."currentBid",
    "buyNowPrice"  = EXCLUDED."buyNowPrice",
    "images"       = EXCLUDED."images",
    "rawData"      = EXCLUDED."rawData",
    "updatedAt"    = NOW()
RETURNING (xmax = 0) AS inserted
"""
# xmax = 0 means a fresh INSERT (not an UPDATE)


def _prepare_row(lot: dict) -> dict:
    """Convert Python types to psycopg2-compatible types."""
    row = dict(lot)

    # source must be the Prisma enum string
    row["source"] = "COPART"

    # images: PostgreSQL text[] — psycopg2 needs a Python list
    if not isinstance(row.get("images"), list):
        row["images"] = []

    # rawData → JSON string (psycopg2 will pass it as ::jsonb)
    raw = row.get("rawData")
    if raw is not None and not isinstance(raw, str):
        row["rawData"] = json.dumps(raw, default=str)

    # saleDate: keep as ISO string; SQL casts to timestamptz
    # None is fine — psycopg2 sends NULL

    return row


def upsert_lots(lots: Sequence[dict], database_url: str | None = None) -> tuple[int, int]:
    """
    Upsert a list of normalised lot dicts.

    Returns:
        (inserted_count, updated_count)

    Raises on DB connection failure.
    """
    if not lots:
        return 0, 0

    db_url = database_url or os.environ["DATABASE_URL"]

    conn = psycopg2.connect(db_url)
    conn.autocommit = False

    inserted = 0
    updated  = 0

    try:
        with conn.cursor() as cur:
            for lot in lots:
                row = _prepare_row(lot)
                cur.execute(_UPSERT_SQL, row)
                result = cur.fetchone()
                if result and result[0]:   # inserted = True
                    inserted += 1
                else:
                    updated += 1

        conn.commit()
        log.info("DB write complete: %d inserted, %d updated", inserted, updated)

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return inserted, updated


def upsert_lots_chunked(
    lots: Sequence[dict],
    chunk_size: int = 200,
    database_url: str | None = None,
) -> tuple[int, int]:
    """
    Upsert in chunks to avoid huge transactions.
    Returns cumulative (inserted, updated).
    """
    total_inserted = 0
    total_updated  = 0

    for i in range(0, len(lots), chunk_size):
        chunk = lots[i : i + chunk_size]
        ins, upd = upsert_lots(chunk, database_url)
        total_inserted += ins
        total_updated  += upd
        log.debug(
            "Chunk %d–%d: %d ins / %d upd",
            i, i + len(chunk) - 1, ins, upd,
        )

    print(f"Saved {total_inserted} lots, updated {total_updated} lots")
    return total_inserted, total_updated
