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


def _resolve_embedded_urls(tweet_text: str) -> str:
    """Follow any t.co or other short URLs in tweet text, fetch their page metadata."""
    urls = re.findall(r'https?://t\.co/\S+|https?://(?:bit\.ly|ow\.ly|tinyurl\.com)/\S+', tweet_text)
    extra_text_parts = []
    for short_url in urls[:3]:  # limit to 3 embedded URLs
        try:
            page_meta = fetch_web_metadata(short_url)
            if page_meta.get("title"):
                extra_text_parts.append(page_meta["title"])
            if page_meta.get("description"):
                extra_text_parts.append(page_meta["description"])
        except Exception:
            pass
    return " ".join(extra_text_parts)


def fetch_x_metadata(url: str) -> dict:
    """Fetch X/Twitter post metadata.

    Strategy:
    1. Try the public oEmbed API (no auth required) for tweet text.
    2. Follow any embedded URLs to get linked page metadata.
    3. Fall back to yt-dlp.
    4. Fall back to scraping Open Graph tags via nitter/direct fetch.
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

        # Follow embedded URLs to get linked page context
        embedded_text = _resolve_embedded_urls(tweet_text)
        description = f"{tweet_text} {embedded_text}".strip() if embedded_text else tweet_text

        author = data.get("author_name", "")
        return {
            "title": tweet_text if tweet_text else author,
            "description": description,
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


def fetch_web_metadata(url: str) -> dict:
    """Fetch metadata from a generic web page via Open Graph / meta tags."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            # Read just the first 50KB to find meta tags
            html = resp.read(50000).decode("utf-8", errors="ignore")

        title = ""
        description = ""

        # Try og:title first
        og_title = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html)
        if og_title:
            title = og_title.group(1)
        else:
            # Fall back to <title> tag
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()

        # og:description
        og_desc = re.search(r'<meta[^>]*property="og:description"[^>]*content="([^"]*)"', html)
        if og_desc:
            description = og_desc.group(1)
        else:
            meta_desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
            if meta_desc:
                description = meta_desc.group(1)

        # og:site_name as uploader
        site = re.search(r'<meta[^>]*property="og:site_name"[^>]*content="([^"]*)"', html)
        site_name = site.group(1) if site else ""

        return {
            "title": title,
            "description": description,
            "duration": None,
            "uploader": site_name,
        }
    except Exception as e:
        print(f"  Web metadata failed for {url}: {e}")
        return {"title": "", "description": "", "duration": None}


def fetch_metadata(link: dict) -> dict:
    """Fetch metadata for a link based on platform."""
    platform = link.get("platform", "")
    url = link.get("normalized_url", link.get("url", ""))

    if platform == "youtube":
        metadata = fetch_youtube_metadata(url)
    elif platform == "x":
        metadata = fetch_x_metadata(url)
    else:
        metadata = fetch_web_metadata(url)

    link["metadata"] = metadata
    print(f"  Fetched metadata: {metadata.get('title', 'N/A')[:60]}")
    return link
