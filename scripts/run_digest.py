#!/usr/bin/env python3
"""
Main orchestrator for the iMessage AI Video Digest.

Runs the full pipeline:
1. Discover thread
2. Extract messages
3. Extract & normalize links
4. Check against processed links
5. Fetch metadata
6. Classify AI relevance
7. Fetch transcripts (captions, then whisper fallback)
8. Summarize videos
9. Build markdown & HTML
10. Archive results
11. Publish to GitHub Pages
12. Send iMessage notification
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.config_loader import load_config
from scripts.discover_thread import discover_thread
from scripts.extract_messages import extract_messages
from scripts.extract_links import extract_links
from scripts.normalize_links import normalize_links
from scripts.fetch_metadata import fetch_metadata
from scripts.classify_ai_relevance import classify_ai_relevance
from scripts.fetch_transcripts import fetch_transcript
from scripts.transcribe_fallback import transcribe_fallback
from scripts.summarize_digest import summarize_video, generate_overall_summary
from scripts.build_markdown import build_markdown
from scripts.build_html import build_html
from scripts.update_archive import update_archive
from scripts.publish_github_pages import publish


def setup_logging(config: dict):
    """Configure structured logging."""
    logs_dir = os.path.join(PROJECT_ROOT, config["paths"]["logs_dir"])
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"digest_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


def load_processed_links(config: dict) -> dict:
    """Load the set of already-processed link URLs."""
    path = os.path.join(PROJECT_ROOT, config["paths"]["processed_links"])
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_processed_links(processed: dict, config: dict):
    """Save updated processed links."""
    path = os.path.join(PROJECT_ROOT, config["paths"]["processed_links"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(processed, f, indent=2)


def load_video_catalog(config: dict) -> list:
    """Load the video catalog."""
    path = os.path.join(PROJECT_ROOT, config["paths"]["video_catalog"])
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def save_video_catalog(catalog: list, config: dict):
    """Save updated video catalog."""
    path = os.path.join(PROJECT_ROOT, config["paths"]["video_catalog"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(catalog, f, indent=2, default=str)


def send_imessage(chat_guid: str, message: str):
    """Send a message to the iMessage thread via AppleScript."""
    script_path = os.path.join(PROJECT_ROOT, "scripts", "send_imessage.scpt")
    try:
        result = subprocess.run(
            ["osascript", script_path, chat_guid, message],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"iMessage send error: {result.stderr}")
            return False
        print("iMessage sent successfully.")
        return True
    except Exception as e:
        print(f"iMessage send failed: {e}")
        return False


def build_imessage_text(links: list[dict], config: dict) -> str:
    """Build the iMessage notification text."""
    site_url = config.get("github_pages", {}).get("site_url", "")
    count = len(links)

    # Collect top themes
    all_tags = []
    for link in links:
        all_tags.extend(link.get("ai_tags", []))
    # Get top 3 most common
    from collections import Counter
    top_themes = [tag for tag, _ in Counter(all_tags).most_common(3)]

    lines = [
        "Weekly Video Digest Ready",
        "",
        f"{count} AI video{'s' if count != 1 else ''} processed this week.",
    ]

    if top_themes:
        lines.append("")
        lines.append("Top themes:")
        for theme in top_themes:
            lines.append(f"• {theme}")

    if site_url:
        lines.append("")
        lines.append(f"Latest:\n{site_url}/latest.html")
        lines.append("")
        lines.append(f"Archive:\n{site_url}/archive.html")

    return "\n".join(lines)


def run(include_urls=None, no_notify=False, date_override=None):
    """Execute the full digest pipeline."""
    config = load_config()
    logger = setup_logging(config)
    run_timestamp = datetime.now(timezone.utc).isoformat()

    logger.info("=== Starting Weekly AI Video Digest ===")

    # Step 1: Discover thread
    logger.info("Step 1: Discovering iMessage thread...")
    thread = discover_thread(config)
    chat_guid = thread["chat_guid"]
    logger.info(f"Thread GUID: {chat_guid}")

    # Step 2: Extract messages
    logger.info("Step 2: Extracting messages...")
    messages = extract_messages(chat_guid, config["lookback_days"], config)
    if not messages:
        logger.info("No messages found in the lookback period. Exiting.")
        return

    # Step 3: Extract links
    logger.info("Step 3: Extracting video links...")
    raw_links = extract_links(messages)
    if not raw_links:
        logger.info("No video links found. Exiting.")
        return

    # Step 4: Normalize and deduplicate
    logger.info("Step 4: Normalizing links...")
    links = normalize_links(raw_links)

    # Step 5: Filter out already-processed links (unless force-included)
    force_urls = set(include_urls or [])
    processed = load_processed_links(config)
    new_links = [l for l in links if l["normalized_url"] not in processed or l["normalized_url"] in force_urls]
    if force_urls:
        forced = [l for l in new_links if l["normalized_url"] in force_urls]
        logger.info(f"Force-including {len(forced)} URL(s)")
    logger.info(f"New links to process: {len(new_links)} (skipped {len(links) - len(new_links)} already processed)")

    if not new_links:
        logger.info("All links already processed. Exiting.")
        return

    # Filter out links to this project's own GitHub Pages site
    site_url = config.get("github_pages", {}).get("site_url", "")
    if site_url:
        before = len(new_links)
        new_links = [l for l in new_links if not l.get("normalized_url", "").startswith(site_url)]
        skipped_self = before - len(new_links)
        if skipped_self:
            logger.info(f"Skipped {skipped_self} self-referencing link(s) from {site_url}")

    if not new_links:
        logger.info("No new links to process after filtering. Exiting.")
        return

    # Step 6: Fetch metadata
    logger.info("Step 6: Fetching metadata...")
    for link in new_links:
        try:
            fetch_metadata(link)
        except Exception as e:
            logger.error(f"Metadata fetch failed for {link['url']}: {e}")

    # Step 7: Classify AI relevance
    logger.info("Step 7: Classifying AI relevance...")
    for link in new_links:
        classify_ai_relevance(link)

    ai_links = [l for l in new_links if l.get("ai_relevance")]
    excluded = [l for l in new_links if not l.get("ai_relevance")]

    # If thread is trusted, include excluded links with low confidence
    if config.get("thread", {}).get("trusted", False) and excluded:
        for link in excluded:
            link["ai_relevance"] = True
            link["ai_relevance_confidence"] = "low"
            link["ai_relevance_reason"] = "Included via trusted thread (AI Masterminds)"
            print(f"  [INCLUDED] (low) Trusted thread override: {link.get('normalized_url', '')[:60]}")
        ai_links = [l for l in new_links if l.get("ai_relevance")]
        excluded = [l for l in new_links if not l.get("ai_relevance")]

    logger.info(f"AI-relevant: {len(ai_links)}, Excluded: {len(excluded)}")

    # Log excluded links
    for link in excluded:
        logger.info(f"  Excluded: {link.get('normalized_url')} — {link.get('ai_relevance_reason')}")

    if not ai_links:
        logger.info("No AI-relevant links found. Exiting.")
        # Still mark as processed
        for link in new_links:
            processed[link["normalized_url"]] = {
                "processed_at": run_timestamp,
                "ai_relevance": link.get("ai_relevance", False),
            }
        save_processed_links(processed, config)
        return

    # Step 8: Fetch transcripts
    logger.info("Step 8: Fetching transcripts...")
    date_str = date_override or datetime.now().strftime("%Y-%m-%d")
    digest_dir = os.path.join(PROJECT_ROOT, config["paths"]["digests_dir"], date_str)
    transcripts_dir = os.path.join(digest_dir, "transcripts")
    os.makedirs(transcripts_dir, exist_ok=True)

    for link in ai_links:
        try:
            fetch_transcript(link, transcripts_dir)
        except Exception as e:
            logger.error(f"Transcript fetch failed for {link['normalized_url']}: {e}")

    # Step 9: Fallback transcription
    logger.info("Step 9: Running fallback transcription for missing transcripts...")
    for link in ai_links:
        if not link.get("transcript"):
            try:
                transcribe_fallback(link, transcripts_dir)
            except Exception as e:
                logger.error(f"Transcription failed for {link['normalized_url']}: {e}")

    # Step 10: Summarize
    logger.info("Step 10: Summarizing videos...")
    for link in ai_links:
        try:
            summarize_video(link)
        except Exception as e:
            logger.error(f"Summary failed for {link['normalized_url']}: {e}")

    # Filter out links with no analyzable content (no metadata, transcript, or meaningful summary)
    before_filter = len(ai_links)
    analyzable = []
    unanalyzable = []
    for l in ai_links:
        title = l.get("metadata", {}).get("title", "").strip()
        desc = l.get("metadata", {}).get("description", "").strip()
        # A bare URL is not meaningful content
        if title.startswith("http://") or title.startswith("https://"):
            title = ""
        if desc.startswith("http://") or desc.startswith("https://"):
            desc = ""
        has_content = l.get("transcript") or title or desc
        if has_content or l.get("normalized_url") in force_urls:
            analyzable.append(l)
        else:
            unanalyzable.append(l)
    ai_links = analyzable
    if unanalyzable:
        logger.info(f"Dropped {len(unanalyzable)} link(s) with no analyzable content:")
        for link in unanalyzable:
            logger.info(f"  Skipped: {link.get('normalized_url')} — no title, description, or transcript available")

    if not ai_links:
        logger.info("No links with analyzable content remain. Exiting.")
        for link in new_links:
            processed[link["normalized_url"]] = {
                "processed_at": run_timestamp,
                "ai_relevance": link.get("ai_relevance", False),
            }
        save_processed_links(processed, config)
        return

    overall_summary = generate_overall_summary(ai_links)

    # Step 11: Build outputs
    logger.info("Step 11: Building digest outputs...")
    md_content = build_markdown(
        links=ai_links,
        overall_summary=overall_summary,
        thread_name=config["thread"]["name"],
        run_timestamp=run_timestamp,
        lookback_days=config["lookback_days"],
    )
    html_content = build_html(md_content)

    # Save to weekly-digests/YYYY-MM-DD/
    md_path = os.path.join(digest_dir, "digest.md")
    html_path = os.path.join(digest_dir, "digest.html")
    with open(md_path, "w") as f:
        f.write(md_content)
    with open(html_path, "w") as f:
        f.write(html_content)

    # Save metadata
    metadata = {
        "date": date_str,
        "run_timestamp": run_timestamp,
        "video_count": len(ai_links),
        "excluded_count": len(excluded),
        "links": [
            {
                "url": l["normalized_url"],
                "title": l.get("metadata", {}).get("title", ""),
                "platform": l.get("platform"),
                "ai_tags": l.get("ai_tags", []),
            }
            for l in ai_links
        ],
    }
    with open(os.path.join(digest_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    # Step 12: Update docs/
    logger.info("Step 12: Updating docs/ for GitHub Pages...")
    docs_dir = os.path.join(PROJECT_ROOT, config["paths"]["docs_dir"])
    os.makedirs(docs_dir, exist_ok=True)

    # Copy to docs/latest.html
    shutil.copy2(html_path, os.path.join(docs_dir, "latest.html"))
    # Copy date-specific version
    shutil.copy2(html_path, os.path.join(docs_dir, f"{date_str}.html"))
    # Update archive
    digests_dir = os.path.join(PROJECT_ROOT, config["paths"]["digests_dir"])
    update_archive(docs_dir, digests_dir)

    # Step 13: Update state
    logger.info("Step 13: Updating state files...")
    for link in new_links:
        processed[link["normalized_url"]] = {
            "processed_at": run_timestamp,
            "ai_relevance": link.get("ai_relevance", False),
        }
    save_processed_links(processed, config)

    catalog = load_video_catalog(config)
    for link in ai_links:
        catalog.append({
            "url": link["normalized_url"],
            "title": link.get("metadata", {}).get("title", ""),
            "platform": link.get("platform"),
            "ai_tags": link.get("ai_tags", []),
            "processed_at": run_timestamp,
            "digest_date": date_str,
        })
    save_video_catalog(catalog, config)

    # Step 14: Publish to GitHub Pages
    logger.info("Step 14: Publishing to GitHub Pages...")
    try:
        publish(f"Weekly digest: {date_str} ({len(ai_links)} videos)")
    except Exception as e:
        logger.error(f"Publish failed: {e}")

    # Step 15: Send iMessage
    if no_notify:
        logger.info("Step 15: Skipping iMessage (--no-notify)")
    else:
        test_mode = config.get("test_mode", {})
        if test_mode.get("enabled") and test_mode.get("send_to"):
            target = test_mode["send_to"]
            logger.info(f"Step 15: Sending iMessage (TEST MODE → {target})...")
        else:
            target = chat_guid
            logger.info("Step 15: Sending iMessage to group chat...")
        imessage_text = build_imessage_text(ai_links, config)
        try:
            send_imessage(target, imessage_text)
        except Exception as e:
            logger.error(f"iMessage send failed: {e}")

    logger.info(f"=== Digest complete: {len(ai_links)} videos processed ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="iMessage AI Video Digest")
    parser.add_argument("--include-url", action="append", default=[],
                        help="Force-include a URL (bypasses processed/content filters). Can be repeated.")
    parser.add_argument("--no-notify", action="store_true",
                        help="Skip sending iMessage notification (silent update).")
    parser.add_argument("--date", default=None,
                        help="Override digest date (YYYY-MM-DD). Appends to that week's digest.")
    args = parser.parse_args()
    run(include_urls=args.include_url, no_notify=args.no_notify, date_override=args.date)
