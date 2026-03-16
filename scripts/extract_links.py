#!/usr/bin/env python3
"""Extract video links from messages."""

import re
import sys
import os
from urllib.parse import urlparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Regex to find URLs in text
URL_PATTERN = re.compile(
    r'https?://[^\s<>"\'\)]+',
    re.IGNORECASE,
)

SUPPORTED_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "x.com",
    "twitter.com",
    "www.twitter.com",
    "mobile.twitter.com",
}


def is_video_link(url: str) -> bool:
    """Check if URL is from a supported video platform."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain in SUPPORTED_DOMAINS
    except Exception:
        return False


def extract_links(messages: list[dict]) -> list[dict]:
    """Extract video links from a list of messages."""
    links = []
    seen_urls = set()

    for msg in messages:
        text = msg.get("text", "")
        if not text:
            continue

        # Skip iMessage reactions (Liked, Laughed at, Emphasized, etc.)
        if re.match(r'^(Liked|Loved|Disliked|Laughed at|Emphasized|Questioned)\s+"', text):
            continue

        urls = URL_PATTERN.findall(text)
        for url in urls:
            # Clean trailing punctuation and unicode artifacts
            url = url.rstrip(".,;:!?)\u201c\u201d\u2026\u00ab\u00bb\"'")

            if not is_video_link(url):
                continue

            if url in seen_urls:
                continue
            seen_urls.add(url)

            links.append({
                "url": url,
                "message_text": text,
                "sender_id": msg.get("sender_id"),
                "timestamp": msg.get("timestamp"),
                "is_from_me": msg.get("is_from_me", False),
            })

    print(f"Extracted {len(links)} video links from {len(messages)} messages")
    return links
