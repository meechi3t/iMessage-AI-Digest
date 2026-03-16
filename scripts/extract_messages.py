#!/usr/bin/env python3
"""Extract messages from the last N days for a given chat GUID."""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.config_loader import load_config

# Apple's epoch: Jan 1, 2001 00:00:00 UTC
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def apple_timestamp_to_datetime(ts: int) -> datetime:
    """Convert Apple Core Data timestamp (nanoseconds since 2001-01-01) to datetime."""
    if ts is None or ts == 0:
        return None
    # Some timestamps are in seconds, some in nanoseconds
    if ts > 1e15:
        seconds = ts / 1e9
    elif ts > 1e12:
        seconds = ts / 1e6
    else:
        seconds = ts
    return APPLE_EPOCH + timedelta(seconds=seconds)


def decode_attributed_body(blob: bytes) -> str:
    """Extract plain text from NSAttributedString binary (streamtyped) format.

    The text is stored after a 'NSString' marker followed by a length-prefixed
    payload.  The byte sequence is typically:
        NSString \\x01 \\x9X \\x84 \\x01 + <length_bytes> <utf-8 text> \\x86
    """
    if not blob:
        return ""

    try:
        # Locate the NSString marker — the actual message text follows it
        idx = blob.find(b"NSString")
        if idx < 0:
            return ""

        # Skip past "NSString" and the next few control bytes to reach the '+'
        search_start = idx + len(b"NSString")
        plus_idx = blob.find(b"+", search_start)
        if plus_idx < 0 or plus_idx > search_start + 10:
            return ""

        # After '+', the next bytes encode the string length, then the UTF-8 text.
        # The length encoding varies: single byte for short strings, multi-byte for longer.
        text_start = plus_idx + 1

        # Read length: if first byte has high bit set (>=0x80), it's a multi-byte length
        length_byte = blob[text_start]
        if length_byte < 0x80:
            # Single byte length
            text_length = length_byte
            text_start += 1
        else:
            # Multi-byte: first byte = 0x81 means 1 byte follows, 0x82 = 2 bytes, etc.
            num_length_bytes = length_byte & 0x7F
            text_length = int.from_bytes(
                blob[text_start + 1 : text_start + 1 + num_length_bytes],
                byteorder="big",
            )
            text_start += 1 + num_length_bytes

        text_bytes = blob[text_start : text_start + text_length]
        return text_bytes.decode("utf-8", errors="replace").strip()

    except Exception:
        return ""


def extract_messages(chat_guid: str, lookback_days: int, config: dict) -> list[dict]:
    """Query messages from the chat in the last lookback_days."""
    db_path = os.path.expanduser(config["messages_db"])
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Calculate cutoff as Apple timestamp (nanoseconds since 2001-01-01)
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    apple_cutoff_seconds = (cutoff - APPLE_EPOCH).total_seconds()
    apple_cutoff_ns = int(apple_cutoff_seconds * 1e9)

    query = """
        SELECT
            m.ROWID,
            m.guid as message_guid,
            m.text,
            m.attributedBody,
            m.date as apple_date,
            m.is_from_me,
            h.id as sender_id
        FROM message m
        JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        JOIN chat c ON cmj.chat_id = c.ROWID
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE c.guid = ?
          AND m.date > ?
        ORDER BY m.date ASC
    """

    rows = conn.execute(query, (chat_guid, apple_cutoff_ns)).fetchall()
    conn.close()

    messages = []
    for row in rows:
        dt = apple_timestamp_to_datetime(row["apple_date"])
        # Prefer text column; fall back to decoding attributedBody
        text = row["text"] or ""
        if not text and row["attributedBody"]:
            text = decode_attributed_body(row["attributedBody"])
        messages.append({
            "rowid": row["ROWID"],
            "message_guid": row["message_guid"],
            "text": text,
            "timestamp": dt.isoformat() if dt else None,
            "is_from_me": bool(row["is_from_me"]),
            "sender_id": row["sender_id"],
        })

    print(f"Extracted {len(messages)} messages from the last {lookback_days} days")
    return messages


if __name__ == "__main__":
    cfg = load_config()
    cache_path = os.path.join(PROJECT_ROOT, cfg["paths"]["thread_cache"])
    with open(cache_path) as f:
        thread = json.load(f)
    msgs = extract_messages(thread["chat_guid"], cfg["lookback_days"], cfg)
    for m in msgs:
        print(f"[{m['timestamp']}] {m['sender_id']}: {m['text'][:80]}")
