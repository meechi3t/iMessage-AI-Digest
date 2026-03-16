#!/usr/bin/env python3
"""Classify whether a video link is AI-related using available metadata."""

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.config_loader import load_config

AI_KEYWORDS = [
    r"\bAI\b",
    r"\bartificial intelligence\b",
    r"\bLLM\b",
    r"\bLLMs\b",
    r"\blarge language model\b",
    r"\bgenerative AI\b",
    r"\bgen AI\b",
    r"\bGPT\b",
    r"\bClaude\b",
    r"\bGemini\b",
    r"\bChatGPT\b",
    r"\bOpenAI\b",
    r"\bAnthrop",
    r"\bDeepMind\b",
    r"\bmachine learning\b",
    r"\bdeep learning\b",
    r"\bneural net",
    r"\btransformer\b",
    r"\bdiffusion model",
    r"\bfine.?tun",
    r"\bRAG\b",
    r"\bretrieval.augmented",
    r"\bvector database",
    r"\bembedding",
    r"\bagent\b",
    r"\bagents\b",
    r"\bagentic\b",
    r"\bmultimodal\b",
    r"\bcomputer vision\b",
    r"\bNLP\b",
    r"\bnatural language",
    r"\btext.to.",
    r"\bimage generation",
    r"\bstable diffusion",
    r"\bmidjourney\b",
    r"\bDALL.E",
    r"\bSora\b",
    r"\breinforcement learning",
    r"\bRLHF\b",
    r"\bAI safety\b",
    r"\balignment\b",
    r"\bAI infrastructure",
    r"\bGPU\b",
    r"\bTPU\b",
    r"\bNVIDIA\b",
    r"\bAI startup",
    r"\bAI research",
    r"\brobotics?\b",
    r"\bautonomous\b",
    r"\bcopilot\b",
    r"\bcoding assistant",
    r"\bcode generation",
    r"\bMistral\b",
    r"\bLlama\b",
    r"\bopen.?source.*model",
    r"\bhugging\s?face\b",
]

AI_PATTERNS = [re.compile(kw, re.IGNORECASE) for kw in AI_KEYWORDS]

# Strong signals — a single match is enough
STRONG_KEYWORDS = [
    r"\bLLM\b",
    r"\bLLMs\b",
    r"\blarge language model",
    r"\bgenerative AI\b",
    r"\bChatGPT\b",
    r"\bOpenAI\b",
    r"\bAnthrop",
    r"\bDeepMind\b",
    r"\bGPT-[345]\b",
    r"\bClaude\b",
    r"\bmultimodal\b",
    r"\bAI agent",
    r"\bagentic\b",
    r"\bRLHF\b",
    r"\bdiffusion model",
    r"\bfine.?tun",
]

STRONG_PATTERNS = [re.compile(kw, re.IGNORECASE) for kw in STRONG_KEYWORDS]


def classify_ai_relevance(link: dict) -> dict:
    """Classify whether a link's content is AI-related.

    Uses title, description, message text, and any transcript snippet.
    Returns the link dict with ai_relevance fields added.
    """
    # Gather all available text
    text_sources = []

    metadata = link.get("metadata", {})
    if metadata.get("title"):
        text_sources.append(metadata["title"])
    if metadata.get("description"):
        text_sources.append(metadata["description"][:2000])
    if metadata.get("tags"):
        text_sources.append(" ".join(metadata["tags"]))

    if link.get("message_text"):
        text_sources.append(link["message_text"])

    if link.get("transcript_snippet"):
        text_sources.append(link["transcript_snippet"])

    combined_text = " ".join(text_sources)

    if not combined_text.strip():
        link["ai_relevance"] = False
        link["ai_relevance_confidence"] = "low"
        link["ai_relevance_reason"] = "No text available for classification"
        return link

    # Count keyword matches
    match_count = sum(1 for p in AI_PATTERNS if p.search(combined_text))
    strong_match_count = sum(1 for p in STRONG_PATTERNS if p.search(combined_text))

    # Classification logic
    if strong_match_count >= 2 or match_count >= 5:
        relevance = True
        confidence = "high"
        reason = f"Strong AI signals: {strong_match_count} strong, {match_count} total keyword matches"
    elif strong_match_count >= 1 or match_count >= 3:
        relevance = True
        confidence = "medium"
        reason = f"Moderate AI signals: {strong_match_count} strong, {match_count} total keyword matches"
    elif match_count >= 1:
        # Single weak match — might be tangential
        relevance = False
        confidence = "low"
        reason = f"Weak AI signals: only {match_count} keyword match(es), likely tangential"
    else:
        relevance = False
        confidence = "high"
        reason = "No AI-related keywords found"

    link["ai_relevance"] = relevance
    link["ai_relevance_confidence"] = confidence
    link["ai_relevance_reason"] = reason

    status = "RELEVANT" if relevance else "EXCLUDED"
    print(f"  [{status}] ({confidence}) {reason}")

    return link
