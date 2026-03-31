#!/usr/bin/env python3
"""Summarize video transcripts into structured digest notes using Claude API."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.config_loader import load_config

SUMMARY_PROMPT = """You are an expert AI/tech analyst creating an in-depth summary for a weekly digest read by engineers and founders.

Video Title: {title}
Platform: {platform}
URL: {url}

Transcript/Description:
{content}

Produce a detailed, insightful summary in this exact format (use markdown):

### TL;DR
(1-2 sentence executive summary of the core message)

### Key Points
- (5-10 detailed bullet points. Go beyond surface-level observations — explain the *why* and *so what* behind each point. Include specific names, numbers, tools, or frameworks mentioned.)

### Technical Details
- (Any specific tools, models, APIs, architectures, frameworks, or technical approaches discussed. If none, write "N/A")

### Industry Implications
- (2-4 bullets on what this means for the broader AI ecosystem — how it affects developers, startups, enterprises, or the competitive landscape)

### Interesting Ideas
- (Novel insights, contrarian takes, or thought-provoking concepts worth remembering. Explain why each idea matters.)

### AI Topic Tags
(Assign 1-5 tags from: agents, LLMs, multimodal, AI startups, infrastructure, coding tools, robotics, research, open source, safety)
Tags: tag1, tag2, tag3

Write for a technical audience. Be specific and substantive — avoid generic filler like "this is interesting" or "AI is changing things." Extract maximum insight from the source material."""

OVERALL_SUMMARY_PROMPT = """You are creating an overview for a weekly AI video digest read by engineers and founders.

Here are the individual video summaries:

{video_summaries}

Write the overview using this exact format:

### Themes This Week
- (bullet for each major theme, 4-6 bullets)

### Highlights
- (the 3-5 most notable takeaways across all content — be specific, name names/tools/ideas)

### Signal vs Noise
- (1-2 bullets on what seems like a real trend vs what's hype)

Write for a technical audience. Be specific and punchy — no filler."""


def summarize_video(link: dict) -> dict:
    """Generate a structured summary for a single video."""
    title = link.get("metadata", {}).get("title", "Untitled")
    platform = link.get("platform", "unknown")
    url = link.get("normalized_url", link.get("url", ""))

    # Use transcript if available, fall back to description
    content = link.get("transcript", "")
    if not content:
        content = link.get("metadata", {}).get("description", "")
    if not content:
        content = link.get("message_text", "No content available")

    # Truncate very long transcripts
    if len(content) > 15000:
        content = content[:15000] + "\n\n[Transcript truncated]"

    prompt = SUMMARY_PROMPT.format(
        title=title,
        platform=platform,
        url=url,
        content=content,
    )

    try:
        import anthropic
        client = anthropic.Anthropic(timeout=120.0)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = response.content[0].text
        link["summary"] = summary
        link["ai_tags"] = _extract_tags(summary)
        print(f"  Summarized: {title[:50]}")
    except Exception as e:
        print(f"  Summary error for {title}: {e}")
        link["summary"] = _fallback_summary(link)
        link["ai_tags"] = []

    return link


def generate_overall_summary(links: list[dict]) -> str:
    """Generate an overall digest summary across all videos."""
    video_summaries = []
    for link in links:
        title = link.get("metadata", {}).get("title", "Untitled")
        summary = link.get("summary", "No summary available")
        video_summaries.append(f"**{title}**\n{summary}")

    combined = "\n\n---\n\n".join(video_summaries)
    prompt = OVERALL_SUMMARY_PROMPT.format(video_summaries=combined)

    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"  Overall summary error: {e}")
        return "Weekly digest of AI-related videos shared in the group chat."


def _extract_tags(summary: str) -> list[str]:
    """Extract AI topic tags from summary text."""
    valid_tags = {
        "agents", "llms", "multimodal", "ai startups", "infrastructure",
        "coding tools", "robotics", "research", "open source", "safety",
    }
    tags = []
    for line in summary.split("\n"):
        if line.lower().startswith("tags:"):
            raw = line.split(":", 1)[1]
            for tag in raw.split(","):
                tag = tag.strip().lower()
                if tag in valid_tags:
                    tags.append(tag)
    return tags


def _fallback_summary(link: dict) -> str:
    """Generate a basic summary when API is unavailable."""
    title = link.get("metadata", {}).get("title", "Untitled")
    desc = link.get("metadata", {}).get("description", "")[:300]
    return f"### Key Points\n- Video: {title}\n- {desc}\n\n### AI Topic Tags\nTags: (classification pending)"
