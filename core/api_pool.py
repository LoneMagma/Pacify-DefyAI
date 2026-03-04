"""
API Key Pool Management v-2.0.0
Handles multiple API keys with rotation on 429 Rate Limit errors.
Supports both Groq Cloud and local LLM backends (no auth required).
"""

import time
from typing import Dict, List, Optional
from .config import API_KEY, API_URL, USE_LOCAL_LLM, GROQ_API_KEY

# ============================================================================
# KEY POOL
# ============================================================================

# Primary key (from config)
_PRIMARY_KEY = API_KEY

# Additional Groq keys for rotation (add more API keys here or via env vars)
# Example: add GROQ_API_KEY_2, GROQ_API_KEY_3, etc. to your .env
import os
_EXTRA_KEYS: List[str] = []
for i in range(2, 10):  # Checks GROQ_API_KEY_2 through GROQ_API_KEY_9
    extra = os.getenv(f"GROQ_API_KEY_{i}", "").strip()
    if extra:
        _EXTRA_KEYS.append(extra)

# Build pool (local LLM uses a single dummy key, no rotation needed)
_KEY_POOL: List[str] = []
if _PRIMARY_KEY and _PRIMARY_KEY.strip():
    _KEY_POOL.append(_PRIMARY_KEY.strip())
_KEY_POOL.extend(_EXTRA_KEYS)

# Current key index (module-level — shared across ALL Brain instances)
_current_key_index: int = 0

# Per-key cooldown tracking (key -> epoch when cooldown expires)
_key_cooldowns: Dict[str, float] = {}

# ============================================================================
# MODULE-LEVEL RATE LIMITER (shared across all Brain instances)
# ============================================================================

_call_count: int = 0
_rate_window_start: float = time.time()
_RATE_LIMIT = 28  # requests per 60-second window (conservative margin on Groq's 30/min)


def _check_rate_limit() -> None:
    """
    Enforce rate limit at module level so multiple Brain instances
    share the same counter (fixes the per-instance bug).
    """
    global _call_count, _rate_window_start

    if USE_LOCAL_LLM:
        return  # Local servers have no rate limit

    now = time.time()
    elapsed = now - _rate_window_start

    if elapsed >= 60.0:
        # New window
        _call_count = 0
        _rate_window_start = now

    if _call_count >= _RATE_LIMIT:
        wait = 60.0 - elapsed
        if wait > 0:
            time.sleep(wait)
        _call_count = 0
        _rate_window_start = time.time()

    _call_count += 1


# ============================================================================
# KEY MANAGEMENT
# ============================================================================

def get_api_headers() -> Dict[str, str]:
    """
    Get API headers with the current active key.
    For local LLM backends, returns a minimal header (no real auth needed).
    """
    global _current_key_index

    if USE_LOCAL_LLM:
        return {"Content-Type": "application/json"}

    if not _KEY_POOL:
        raise ValueError(
            "No API keys configured.\n"
            "Add GROQ_API_KEY to your .env, or set LOCAL_LLM=true for local servers."
        )

    # Skip keys that are in cooldown
    now = time.time()
    available = [
        (i, k) for i, k in enumerate(_KEY_POOL)
        if _key_cooldowns.get(k, 0) <= now
    ]

    if not available:
        # All keys in cooldown — wait for shortest one
        min_cooldown = min(_key_cooldowns.values())
        wait = max(0, min_cooldown - now)
        time.sleep(wait)
        available = list(enumerate(_KEY_POOL))

    # Round-robin among available
    idx, key = available[_current_key_index % len(available)]
    _current_key_index = (_current_key_index + 1) % len(available)

    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def rotate_on_rate_limit(key: Optional[str] = None) -> None:
    """
    Called when a 429 response is received.
    Marks the current key as cooling down for 60 seconds and rotates to next.
    """
    global _current_key_index

    if USE_LOCAL_LLM:
        return

    cooldown_key = key or (_KEY_POOL[_current_key_index % len(_KEY_POOL)] if _KEY_POOL else None)
    if cooldown_key:
        _key_cooldowns[cooldown_key] = time.time() + 60.0
        _current_key_index = (_current_key_index + 1) % max(len(_KEY_POOL), 1)


def get_key_count() -> int:
    """Total number of active keys in pool."""
    return len(_KEY_POOL)


def validate_keys() -> tuple:
    """Validate API key configuration."""
    if USE_LOCAL_LLM:
        return True, f"Local LLM mode — no key required (endpoint: {API_URL})"

    if not _KEY_POOL:
        return False, "No API keys configured"

    if not _KEY_POOL[0].startswith("gsk_"):
        return False, f"Primary key should start with 'gsk_', got: {_KEY_POOL[0][:10]}..."

    return True, f"{len(_KEY_POOL)} key(s) configured and validated"
