"""
Debug Helper - Enable verbose logging for troubleshooting v-1.0.0
"""

import os

# Set this to True to enable debug output
DEBUG_MODE = False


def debug_print(message: str, label: str = "DEBUG"):
    """Print debug message if DEBUG_MODE is enabled."""
    if DEBUG_MODE:
        print(f"[{label}] {message}")


def log_prompt(prompt: str):
    """Log full prompt being sent to API."""
    if DEBUG_MODE:
        print("\n" + "="*80)
        print("PROMPT BEING SENT:")
        print("="*80)
        print(prompt)
        print("="*80 + "\n")


def log_response(response: str):
    """Log raw API response."""
    if DEBUG_MODE:
        print("\n" + "="*80)
        print("RAW API RESPONSE:")
        print("="*80)
        print(response)
        print("="*80 + "\n")


__all__ = ['DEBUG_MODE', 'debug_print', 'log_prompt', 'log_response']
