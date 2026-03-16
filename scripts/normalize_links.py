#!/usr/bin/env python3
"""Normalize video URLs to canonical forms."""

import re
import sys
import os
from urllib.parse import urlparse, parse_qs, urlencode

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def normalize_youtube_url(url: str) -> str:
    """Normalize YouTube URLs to standard format."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if domain == "youtu.be":
        video_id = parsed.path.strip("/")
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

    if "youtube.com" in domain:
        params = parse_qs(parsed.query)
        video_id = params.get("v", [None])[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

        # Handle /shorts/, /live/, /embed/ paths
        for prefix in ("/shorts/", "/live/", "/embed/"):
            if parsed.path.startswith(prefix):
                video_id = parsed.path[len(prefix):].split("/")[0].split("?")[0]
                if video_id:
                    return f"https://www.youtube.com/watch?v={video_id}"

    return url


def normalize_twitter_url(url: str) -> str:
    """Normalize Twitter/X URLs to canonical form (strip tracking params)."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path

    # Always use x.com
    if "twitter.com" in domain:
        domain = "x.com"

    # Strip tracking query params (s, t, ref_src, etc.) — keep only path
    return f"https://x.com{path}"


def normalize_link(url: str) -> dict:
    """Normalize a URL and extract platform info."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if "youtube.com" in domain or "youtu.be" in domain:
        normalized = normalize_youtube_url(url)
        platform = "youtube"
        # Extract video ID
        params = parse_qs(urlparse(normalized).query)
        video_id = params.get("v", [None])[0]
    elif "x.com" in domain or "twitter.com" in domain:
        normalized = normalize_twitter_url(url)
        platform = "x"
        # Extract post ID from path
        match = re.search(r'/status/(\d+)', normalized)
        video_id = match.group(1) if match else None
    else:
        normalized = url
        platform = "unknown"
        video_id = None

    return {
        "original_url": url,
        "normalized_url": normalized,
        "platform": platform,
        "video_id": video_id,
    }


def normalize_links(links: list[dict]) -> list[dict]:
    """Normalize all links and deduplicate by normalized URL."""
    seen = set()
    normalized = []

    for link in links:
        info = normalize_link(link["url"])
        norm_url = info["normalized_url"]

        if norm_url in seen:
            continue
        seen.add(norm_url)

        link.update(info)
        normalized.append(link)

    print(f"Normalized {len(normalized)} unique links from {len(links)} raw links")
    return normalized
