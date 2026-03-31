#!/usr/bin/env python3
"""Load project configuration."""

import os

import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    # Resolve participants from env vars
    thread = config.get("thread", {})
    if "participants_env" in thread:
        thread["participants"] = [
            os.environ.get(var, "") for var in thread["participants_env"]
        ]

    # Resolve test_mode send_to from env var
    test_mode = config.get("test_mode", {})
    if "send_to_env" in test_mode:
        test_mode["send_to"] = os.environ.get(test_mode["send_to_env"], "")

    return config
