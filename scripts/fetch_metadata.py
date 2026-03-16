#!/usr/bin/env python3
"""Fetch video metadata from YouTube and X/Twitter."""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.parse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def fetch_youtube_metadata(url: str) -> dict:
    """Fetch YouTube video metadata using yt-dlp."""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--no-download",
                "--print-json",
                "--no-playlist",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "duration": data.get("duration"),
                "uploader": data.get("uploader", ""),
                "upload_date": data.get("upload_date", ""),
                "view_count": data.get("view_count"),
                "tags": data.get("tags", []),
                "categories": data.get("categories", []),
            }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error fetching YouTube metadata for {url}: {e}")

    return {"title": "", "description": "", "duration": None}


def fetch_x_metadata(url: str) -> dict:
    """Fetch X/Twitter post metadata.

    Strategy:
    1. Try the public oEmbed API (no auth required) for tweet text.
    2. Fall back to yt-dlp.
    3. Fall back to scraping Open Graph tags via nitter/direct fetch.
    """
    # --- Strategy 1: Twitter/X oEmbed API ---
    try:
        oembed_url = (
            "https://publish.twitter.com/oembed?"
            + urllib.parse.urlencode({"url": url, "omit_script": "true"})
        )
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        # The html field contains the tweet text wrapped in markup
        html = data.get("html", "")
        # Extract text from the blockquote
        text_match = re.search(
            r'<blockquote[^>]*><p[^>]*>(.*?)</p>', html, re.DOTALL
        )
        tweet_text = ""
        if text_match:
            tweet_text = re.sub(r'<[^>]+>', ' ', text_match.group(1)).strip()

        author = data.get("author_name", "")
        return {
            "title": tweet_text[:120] if tweet_text else author,
            "description": tweet_text,
            "duration": None,
            "uploader": author,
            "author_url": data.get("author_url", ""),
        }
    except Exception as e:
        print(f"  oEmbed failed for {url}: {e}")

    # --- Strategy 2: yt-dlp fallback ---
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-download", "--print-json", url],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "title": data.get("title", "") or data.get("description", "")[:100],
                "description": data.get("description", ""),
                "duration": data.get("duration"),
                "uploader": data.get("uploader", "") or data.get("uploader_id", ""),
            }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"  yt-dlp failed for {url}: {e}")

    return {"title": "", "description": "", "duration": None}


def fetch_metadata(link: dict) -> dict:
    """Fetch metadata for a video link based on platform."""
    platform = link.get("platform", "")
    url = link.get("normalized_url", link.get("url", ""))

    if platform == "youtube":
        metadata = fetch_youtube_metadata(url)
    elif platform == "x":
        metadata = fetch_x_metadata(url)
    else:
        metadata = {"title": "", "description": ""}

    link["metadata"] = metadata
    print(f"  Fetched metadata: {metadata.get('title', 'N/A')[:60]}")
    return link
