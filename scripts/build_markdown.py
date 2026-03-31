#!/usr/bin/env python3
"""Build the Markdown digest file."""

import os
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def build_markdown(
    links: list[dict],
    overall_summary: str,
    thread_name: str,
    run_timestamp: str,
    lookback_days: int = 7,
) -> str:
    """Build a complete Markdown digest."""
    now = datetime.fromisoformat(run_timestamp)
    start_date = now - timedelta(days=lookback_days)

    lines = []
    lines.append(f"# Weekly AI Video Digest")
    lines.append("")
    lines.append(f"**Thread:** {thread_name}")
    lines.append(f"**Date Range:** {start_date.strftime('%B %d, %Y')} – {now.strftime('%B %d, %Y')}")
    lines.append(f"**Generated:** {now.strftime('%B %d, %Y at %I:%M %p')}")
    lines.append(f"**Videos Processed:** {len(links)}")
    lines.append("")

    # Overall summary
    lines.append("## Overview")
    lines.append("")
    lines.append(overall_summary)
    lines.append("")

    # Collect all tags
    all_tags = set()
    for link in links:
        all_tags.update(link.get("ai_tags", []))

    if all_tags:
        lines.append("**Top Themes:** " + ", ".join(sorted(all_tags)))
        lines.append("")

    lines.append("---")
    lines.append("")

    # Per-video sections
    for i, link in enumerate(links, 1):
        metadata = link.get("metadata", {})
        platform = link.get("platform", "unknown").title()
        url = link.get("normalized_url", link.get("url", ""))
        timestamp = link.get("timestamp", "")
        tags = link.get("ai_tags", [])
        uploader = metadata.get("uploader", "")

        # For X posts, use @uploader as the title since tweet text is too long
        raw_title = metadata.get("title", "Untitled")
        if link.get("platform") == "x" and uploader:
            title = f"@{uploader}" if not uploader.startswith("@") else uploader
            subtitle = raw_title
        else:
            title = raw_title
            subtitle = ""

        lines.append(f"## {i}. {title}")
        lines.append("")
        if subtitle:
            lines.append(f"> {subtitle}")
            lines.append("")
        lines.append(f"- **Source:** {platform}")
        lines.append(f"- **URL:** [{url}]({url})")
        lines.append(f"- **Shared on:** {timestamp}")
        if tags:
            lines.append(f"- **Tags:** {', '.join(tags)}")
        lines.append("")

        summary = link.get("summary", "No summary available.")
        lines.append(summary)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
