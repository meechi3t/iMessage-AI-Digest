# iMessage AI Video Digest

Automated weekly digest of AI-related videos shared in an iMessage group chat. Runs locally on macOS, scans for YouTube and X/Twitter video links, transcribes and summarizes them, publishes to GitHub Pages, and sends a notification back to the chat.

## Architecture

```
iMessage (chat.db)
    │
    ▼
┌──────────────────────┐
│  discover_thread.py   │  Find group chat by participant numbers
│  extract_messages.py  │  Query last 7 days of messages
│  extract_links.py     │  Pull YouTube/X video URLs
│  normalize_links.py   │  Canonicalize and deduplicate URLs
│  classify_ai_relevance│  Keyword-based AI content filter
│  fetch_metadata.py    │  yt-dlp metadata extraction
│  fetch_transcripts.py │  YouTube captions via yt-dlp
│  transcribe_fallback  │  Faster-Whisper local transcription
│  summarize_digest.py  │  Claude API structured summaries
│  build_markdown.py    │  Generate Markdown digest
│  build_html.py        │  Convert to styled HTML
│  update_archive.py    │  Maintain archive index
│  publish_github_pages │  git commit + push to docs/
│  send_imessage.scpt   │  AppleScript notification
└──────────────────────┘
    │
    ▼
GitHub Pages (docs/)  +  iMessage notification
```

## Setup

### Prerequisites

```bash
# Install Homebrew packages
brew install ffmpeg yt-dlp python@3.14

# Create virtual environment
cd imessage-video-digest
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Whisper Setup

```bash
pip install faster-whisper
```

The `small` model will be downloaded automatically on first use (~500MB).

### Anthropic API Key

Set your API key for Claude-powered summaries:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Add to `~/.zshrc` for persistence.

### macOS Permissions

Grant these permissions in System Settings > Privacy & Security:

- **Full Disk Access** — for Terminal/iTerm (to read `~/Library/Messages/chat.db`)
- **Automation** — allow Terminal to control Messages (for sending iMessages)

### GitHub Pages Setup

1. Create a GitHub repo for this project
2. Push the code
3. In repo Settings > Pages, set source to "Deploy from a branch", branch `main`, folder `/docs`
4. Update `config/config.yaml` with your `repo_url` and `site_url`

### Configuration

Edit `config/config.yaml`:

- Set participant phone numbers
- Set GitHub Pages URLs
- Adjust lookback days, transcription model, etc.

## Usage

### Manual Run

```bash
source venv/bin/activate
python scripts/run_digest.py
```

### Scheduled (launchd)

Install the launch agent for weekly Monday runs:

```bash
cp launchd/com.local.imessage-video-digest.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.local.imessage-video-digest.plist
```

To unload:

```bash
launchctl unload ~/Library/LaunchAgents/com.local.imessage-video-digest.plist
```

Check status:

```bash
launchctl list | grep imessage-video-digest
```

### Testing Individual Steps

```bash
# Discover and cache the thread GUID
python scripts/discover_thread.py

# Extract messages (requires cached thread)
python scripts/extract_messages.py
```

## Project Structure

```
├── config/config.yaml          # Main configuration
├── scripts/                    # All pipeline scripts
│   ├── run_digest.py          # Main orchestrator
│   ├── discover_thread.py     # Thread discovery
│   ├── extract_messages.py    # Message extraction
│   ├── extract_links.py       # Link extraction
│   ├── normalize_links.py     # URL normalization
│   ├── classify_ai_relevance.py  # AI content filter
│   ├── fetch_metadata.py      # Video metadata
│   ├── fetch_transcripts.py   # Caption retrieval
│   ├── transcribe_fallback.py # Whisper transcription
│   ├── summarize_digest.py    # Claude API summaries
│   ├── build_markdown.py      # Markdown generation
│   ├── build_html.py          # HTML generation
│   ├── update_archive.py      # Archive maintenance
│   ├── publish_github_pages.py # Git publish
│   └── send_imessage.scpt     # iMessage via AppleScript
├── data/state/                 # Persistent state
├── weekly-digests/             # Historical digests
├── docs/                       # GitHub Pages source
└── launchd/                    # macOS scheduler
```

## Outputs

- `weekly-digests/YYYY-MM-DD/` — dated digest folders with MD, HTML, metadata, transcripts
- `docs/latest.html` — most recent digest
- `docs/archive.html` — index of all past digests
- `docs/YYYY-MM-DD.html` — individual digest pages
