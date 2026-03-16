#!/usr/bin/env python3
"""Discover the iMessage group thread by participant phone numbers and cache the GUID."""

import json
import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.config_loader import load_config


def normalize_phone(phone: str) -> str:
    """Strip to digits only."""
    return "".join(c for c in phone if c.isdigit())


def discover_thread(config: dict) -> dict:
    """Find the group chat GUID by matching participant phone numbers."""
    db_path = os.path.expanduser(config["messages_db"])
    participants = [normalize_phone(p) for p in config["thread"]["participants"]]
    cache_path = os.path.join(PROJECT_ROOT, config["paths"]["thread_cache"])

    # Check cache first
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            cached = json.load(f)
        if cached.get("chat_guid"):
            print(f"Using cached thread GUID: {cached['chat_guid']}")
            return cached

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Find all group chats
    chats = conn.execute(
        "SELECT c.ROWID, c.guid, c.display_name, c.chat_identifier "
        "FROM chat c WHERE c.style = 43"  # 43 = group chat
    ).fetchall()

    matched_guid = None
    for chat in chats:
        chat_id = chat["ROWID"]
        # Get handles for this chat
        handles = conn.execute(
            "SELECT h.id FROM handle h "
            "JOIN chat_handle_join chj ON h.ROWID = chj.handle_id "
            "WHERE chj.chat_id = ?",
            (chat_id,),
        ).fetchall()

        handle_numbers = {normalize_phone(h["id"]) for h in handles}

        # Check if all target participants are in this chat
        if all(p in handle_numbers for p in participants):
            # Prefer exact match on participant count for small groups
            if len(handle_numbers) == len(participants):
                matched_guid = chat["guid"]
                break
            elif matched_guid is None:
                matched_guid = chat["guid"]

    conn.close()

    if not matched_guid:
        raise RuntimeError(
            f"Could not find group chat with participants: {participants}"
        )

    result = {
        "thread_name": config["thread"]["name"],
        "chat_guid": matched_guid,
        "participants": config["thread"]["participants"],
    }

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Discovered and cached thread GUID: {matched_guid}")
    return result


if __name__ == "__main__":
    cfg = load_config()
    result = discover_thread(cfg)
    print(json.dumps(result, indent=2))
