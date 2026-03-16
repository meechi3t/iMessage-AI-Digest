#!/usr/bin/env python3
"""Publish HTML digest to GitHub Pages via git commit and push."""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def publish(commit_message: str = "Update weekly digest"):
    """Stage docs/, commit, and push to GitHub."""
    os.chdir(PROJECT_ROOT)

    # Stage docs directory and weekly-digests
    subprocess.run(["git", "add", "docs/"], check=True)
    subprocess.run(["git", "add", "weekly-digests/"], check=True)
    subprocess.run(["git", "add", "data/state/processed_links.json"], check=False)
    subprocess.run(["git", "add", "data/state/video_catalog.json"], check=False)

    # Check if there are staged changes
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True,
    )

    if result.returncode == 0:
        print("No changes to publish.")
        return False

    # Commit
    subprocess.run(
        ["git", "commit", "-m", commit_message],
        check=True,
    )

    # Push
    result = subprocess.run(
        ["git", "push"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Push failed: {result.stderr}")
        print("Changes committed locally. Push manually with: git push")
        return False

    print("Published to GitHub Pages successfully.")
    return True


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Update weekly digest"
    publish(msg)
