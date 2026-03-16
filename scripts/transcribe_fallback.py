#!/usr/bin/env python3
"""Fallback local transcription using Faster-Whisper."""

import os
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.config_loader import load_config


def download_audio(url: str, output_path: str) -> str | None:
    """Download audio from a video URL using yt-dlp."""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-x",
                "--audio-format", "wav",
                "--audio-quality", "0",
                "-o", output_path,
                url,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        # yt-dlp may change extension
        base = os.path.splitext(output_path)[0]
        for ext in [".wav", ".m4a", ".mp3", ".opus", ".webm"]:
            candidate = base + ext
            if os.path.exists(candidate):
                return candidate
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  Audio download error: {e}")
        return None


def transcribe_with_whisper(audio_path: str, model_name: str = "small") -> str | None:
    """Transcribe audio using faster-whisper."""
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, language="en")

        transcript_parts = []
        for segment in segments:
            transcript_parts.append(segment.text.strip())

        transcript = " ".join(transcript_parts)
        print(f"  Transcribed: {len(transcript)} chars ({info.language}, {info.language_probability:.0%})")
        return transcript

    except ImportError:
        print("  faster-whisper not installed, skipping transcription")
        return None
    except Exception as e:
        print(f"  Transcription error: {e}")
        return None


def transcribe_fallback(link: dict, transcripts_dir: str) -> dict:
    """Download audio and transcribe if no transcript is available."""
    if link.get("transcript"):
        return link  # Already has transcript

    config = load_config()
    model_name = config.get("transcription", {}).get("model", "small")
    url = link.get("normalized_url", link.get("url", ""))
    video_id = link.get("video_id", "unknown")

    os.makedirs(transcripts_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_output = os.path.join(tmpdir, f"{video_id}.%(ext)s")
        audio_path = download_audio(url, audio_output)

        if not audio_path:
            print(f"  Could not download audio for {url}")
            link["transcript"] = None
            link["transcript_source"] = "failed"
            return link

        transcript = transcribe_with_whisper(audio_path, model_name)

    if transcript:
        # Save transcript
        txt_path = os.path.join(transcripts_dir, f"{video_id}.txt")
        with open(txt_path, "w") as f:
            f.write(transcript)
        link["transcript"] = transcript
        link["transcript_source"] = "whisper"
    else:
        link["transcript"] = None
        link["transcript_source"] = "failed"

    return link
