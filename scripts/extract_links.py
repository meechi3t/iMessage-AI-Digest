#!/usr/bin/env python3
"""Extract links from messages."""

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

# Domains to always ignore (not useful content)
IGNORED_DOMAINS = {
    "apple.com",
    "icloud.com",
    "googleapis.com",
    "gstatic.com",
    "bit.ly",  # too ambiguous without resolving
}

# Domains that never need metadata fetching (images, etc.)
IGNORED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".mp4", ".mov", ".mp3", ".wav",
}


def is_useful_link(url: str) -> bool:
    """Check if URL is worth processing (not an image, attachment, etc.)."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # Skip ignored domains
        for ignored in IGNORED_DOMAINS:
            if ignored in domain:
                return False

        # Skip direct media files
        for ext in IGNORED_EXTENSIONS:
            if path.endswith(ext):
                return False

        return True
    except Exception:
        return False


def get_platform(url: str) -> str:
    """Determine the platform from a URL."""
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return "web"

    if "youtube.com" in domain or "youtu.be" in domain:
        return "youtube"
    elif "x.com" in domain or "twitter.com" in domain:
        return "x"
    elif "github.com" in domain:
        return "github"
    elif "reddit.com" in domain:
        return "reddit"
    elif "arxiv.org" in domain:
        return "arxiv"
    elif "substack.com" in domain or "newsletter" in domain:
        return "newsletter"
    elif "medium.com" in domain:
        return "medium"
    else:
        return "web"


def extract_links(messages: list[dict]) -> list[dict]:
    """Extract all meaningful links from a list of messages."""
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

            if not is_useful_link(url):
                continue

            if url in seen_urls:
                continue
            seen_urls.add(url)

            links.append({
                "url": url,
                "platform": get_platform(url),
                "message_text": text,
                "sender_id": msg.get("sender_id"),
                "timestamp": msg.get("timestamp"),
                "is_from_me": msg.get("is_from_me", False),
            })

    print(f"Extracted {len(links)} links from {len(messages)} messages")
    return links
