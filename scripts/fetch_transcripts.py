#!/usr/bin/env python3
"""Fetch transcripts for YouTube videos via captions."""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def fetch_youtube_captions(url: str, output_dir: str) -> str | None:
    """Try to download YouTube captions using yt-dlp."""
    os.makedirs(output_dir, exist_ok=True)

    # Try auto-generated or manual subtitles
    for sub_flag in ["--write-auto-sub", "--write-sub"]:
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--skip-download",
                    sub_flag,
                    "--sub-lang", "en",
                    "--sub-format", "vtt",
                    "--convert-subs", "srt",
                    "-o", os.path.join(output_dir, "%(id)s.%(ext)s"),
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Check for .srt files in output dir
            for fname in os.listdir(output_dir):
                if fname.endswith(".srt"):
                    srt_path = os.path.join(output_dir, fname)
                    transcript = _parse_srt(srt_path)
                    if transcript and len(transcript.strip()) > 50:
                        # Save as plain text
                        txt_path = srt_path.replace(".srt", ".txt")
                        with open(txt_path, "w") as f:
                            f.write(transcript)
                        # Clean up SRT
                        os.remove(srt_path)
                        print(f"  Fetched captions: {len(transcript)} chars")
                        return transcript
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  Caption fetch error: {e}")
            continue

    return None


def _parse_srt(srt_path: str) -> str:
    """Parse SRT file to plain text, removing timestamps and indices."""
    lines = []
    with open(srt_path) as f:
        for line in f:
            line = line.strip()
            # Skip sequence numbers, timestamp lines, empty lines
            if not line:
                continue
            if line.isdigit():
                continue
            if "-->" in line:
                continue
            # Remove HTML-like tags from subtitles
            import re
            clean = re.sub(r"<[^>]+>", "", line)
            if clean and clean not in lines[-1:]:
                lines.append(clean)
    return " ".join(lines)


def fetch_transcript(link: dict, output_dir: str) -> dict:
    """Fetch transcript for a video link."""
    platform = link.get("platform", "")
    url = link.get("normalized_url", link.get("url", ""))

    if platform == "youtube":
        transcript = fetch_youtube_captions(url, output_dir)
        if transcript:
            link["transcript"] = transcript
            link["transcript_source"] = "captions"
            return link

    # No captions available — mark for fallback transcription
    link["transcript"] = None
    link["transcript_source"] = None
    return link
