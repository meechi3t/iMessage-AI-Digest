#!/usr/bin/env python3
"""Convert Markdown digest to HTML with styling."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg: #f0f2f5;
            --card-bg: #ffffff;
            --text: #1a1a2e;
            --text-secondary: #4a5568;
            --text-muted: #718096;
            --heading: #1a202c;
            --heading2: #2d3748;
            --heading3: #553c9a;
            --border: #e2e8f0;
            --border-light: #edf2f7;
            --link: #3182ce;
            --link-hover: #2c5282;
            --accent: #6366f1;
            --accent-light: #e0e7ff;
            --accent-text: #4338ca;
            --overview-bg: linear-gradient(135deg, #f0f4ff 0%, #e8ecff 100%);
            --overview-border: #6366f1;
            --tag-bg: #eef2ff;
            --tag-text: #4338ca;
            --tag-border: #c7d2fe;
            --quote-bg: #f7fafc;
            --quote-border: #cbd5e0;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
            --shadow: 0 4px 20px rgba(0,0,0,0.06);
            --shadow-lg: 0 10px 40px rgba(0,0,0,0.08);
            --section-bg: #fafbfc;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #0d1117;
                --card-bg: #161b22;
                --text: #e6edf3;
                --text-secondary: #b1bac4;
                --text-muted: #8b949e;
                --heading: #f0f6fc;
                --heading2: #e6edf3;
                --heading3: #d2a8ff;
                --border: #30363d;
                --border-light: #21262d;
                --link: #58a6ff;
                --link-hover: #79c0ff;
                --accent: #8b5cf6;
                --accent-light: #1e1b4b;
                --accent-text: #c4b5fd;
                --overview-bg: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
                --overview-border: #8b5cf6;
                --tag-bg: #1e1b4b;
                --tag-text: #c4b5fd;
                --tag-border: #3b3575;
                --quote-bg: #0d1117;
                --quote-border: #30363d;
                --shadow-sm: 0 1px 3px rgba(0,0,0,0.2);
                --shadow: 0 4px 20px rgba(0,0,0,0.2);
                --shadow-lg: 0 10px 40px rgba(0,0,0,0.3);
                --section-bg: #0d1117;
            }}
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            line-height: 1.7;
            color: var(--text);
            background: var(--bg);
            padding: 2rem 1rem;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 860px;
            margin: 0 auto;
        }}
        /* Header */
        .header {{
            background: var(--card-bg);
            border-radius: 16px;
            box-shadow: var(--shadow);
            padding: 2.5rem 3rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border-light);
        }}
        .header h1 {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--heading);
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
        }}
        .header-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        .header-meta span {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .stat-badge {{
            display: inline-flex;
            align-items: center;
            background: var(--accent-light);
            color: var(--accent-text);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
        }}
        /* Overview */
        .overview {{
            background: var(--overview-bg);
            border-radius: 16px;
            box-shadow: var(--shadow);
            padding: 2rem 2.5rem;
            margin-bottom: 1.5rem;
            border-left: 4px solid var(--overview-border);
            border: 1px solid var(--border-light);
            border-left: 4px solid var(--overview-border);
        }}
        .overview h2 {{
            font-size: 1.3rem;
            color: var(--heading2);
            margin-bottom: 1rem;
            border: none;
            padding: 0;
        }}
        .overview h3 {{
            font-size: 1.05rem;
            color: var(--heading3);
            margin-top: 1.2rem;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }}
        .overview ul {{
            margin: 0.4rem 0 0.8rem 1.2rem;
        }}
        .overview li {{
            margin: 0.35rem 0;
            color: var(--text-secondary);
        }}
        .themes {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }}
        .themes .tag {{
            font-size: 0.85rem;
            padding: 0.3rem 0.8rem;
        }}
        /* Video cards */
        .video-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-light);
            border-radius: 16px;
            box-shadow: var(--shadow-sm);
            padding: 2rem 2.5rem;
            margin-bottom: 1.25rem;
            transition: box-shadow 0.2s ease, transform 0.2s ease;
        }}
        .video-card:hover {{
            box-shadow: var(--shadow-lg);
            transform: translateY(-1px);
        }}
        .video-card h2 {{
            font-size: 1.4rem;
            color: var(--heading2);
            margin-bottom: 0.3rem;
            border: none;
            padding: 0;
            font-weight: 700;
            letter-spacing: -0.01em;
        }}
        .video-card blockquote {{
            background: var(--quote-bg);
            border-left: 3px solid var(--quote-border);
            padding: 0.6rem 1rem;
            margin: 0.5rem 0 1rem 0;
            border-radius: 0 8px 8px 0;
            color: var(--text-secondary);
            font-size: 0.92rem;
            font-style: italic;
        }}
        .video-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem 1.5rem;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 1.2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-light);
        }}
        .video-meta a {{
            color: var(--link);
            text-decoration: none;
        }}
        .video-meta a:hover {{
            color: var(--link-hover);
            text-decoration: underline;
        }}
        .video-card h3 {{
            font-size: 1rem;
            margin-top: 1.3rem;
            margin-bottom: 0.5rem;
            color: var(--heading3);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-size: 0.8rem;
        }}
        .video-card ul {{
            margin: 0.3rem 0 0.5rem 1.2rem;
        }}
        .video-card li {{
            margin: 0.4rem 0;
            color: var(--text-secondary);
            line-height: 1.6;
        }}
        /* Tags */
        .tag {{
            display: inline-block;
            background: var(--tag-bg);
            color: var(--tag-text);
            padding: 0.2rem 0.65rem;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 500;
            border: 1px solid var(--tag-border);
            margin: 0.15rem;
        }}
        .tags-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-top: 1rem;
            padding-top: 0.8rem;
            border-top: 1px solid var(--border-light);
        }}
        /* General elements */
        h2 {{
            font-size: 1.3rem;
            margin-top: 2rem;
            margin-bottom: 0.8rem;
            color: var(--heading2);
            border-bottom: 2px solid var(--border);
            padding-bottom: 0.3rem;
        }}
        h3 {{
            font-size: 1rem;
            margin-top: 1.2rem;
            margin-bottom: 0.5rem;
            color: var(--heading3);
        }}
        p {{
            margin: 0.5rem 0;
            color: var(--text-secondary);
        }}
        strong {{
            color: var(--text);
        }}
        ul {{
            margin: 0.5rem 0 0.5rem 1.5rem;
        }}
        li {{
            margin: 0.3rem 0;
        }}
        hr {{
            border: none;
            margin: 0;
        }}
        a {{
            color: var(--link);
            text-decoration: none;
        }}
        a:hover {{
            color: var(--link-hover);
            text-decoration: underline;
        }}
        blockquote {{
            background: var(--quote-bg);
            border-left: 3px solid var(--quote-border);
            padding: 0.6rem 1rem;
            margin: 0.5rem 0;
            border-radius: 0 8px 8px 0;
            color: var(--text-secondary);
            font-style: italic;
        }}
        .footer {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.8rem;
            margin-top: 2rem;
            padding: 1.5rem;
        }}
        @media (max-width: 640px) {{
            .header, .overview, .video-card {{
                padding: 1.5rem;
                border-radius: 12px;
            }}
            .header h1 {{ font-size: 1.5rem; }}
            .header-meta {{ gap: 0.75rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
        <div class="footer">
            Generated by Tip10 Technologies
        </div>
    </div>
</body>
</html>"""


def markdown_to_html_content(md_text: str) -> str:
    """Convert markdown to HTML content."""
    try:
        import markdown
        return markdown.markdown(md_text, extensions=["extra", "smarty"])
    except ImportError:
        # Basic fallback conversion
        import re
        html = md_text
        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        # Links
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
        # List items
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        # Paragraphs
        html = re.sub(r'\n\n', '</p><p>', html)
        html = f'<p>{html}</p>'
        # Horizontal rules
        html = html.replace('<p>---</p>', '<hr>')
        return html


def build_html(md_text: str, title: str = "Weekly AI Video Digest") -> str:
    """Build a styled HTML page from markdown text."""
    content = markdown_to_html_content(md_text)
    return HTML_TEMPLATE.format(title=title, content=content)
