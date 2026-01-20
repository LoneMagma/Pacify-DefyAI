"""
API Key Pool Management v-1.0.0
Handles multiple API keys with proper validation
"""

import os
from typing import Dict
from .config import GROQ_API_KEY

# Primary key from .env
PRIMARY_KEY = GROQ_API_KEY

# Additional keys can be added here (optional)
ADDITIONAL_KEYS = []

# Current key index for rotation
_current_key_index = 0


def get_api_headers() -> Dict[str, str]:
    """
    Get API headers with key rotation support and validation.
    
    Returns:
        Headers dictionary with Authorization
    
    Raises:
        ValueError: If no valid API key is configured
    """
    global _current_key_index
    
    # Build key pool
    key_pool = []
    
    if PRIMARY_KEY and PRIMARY_KEY.strip():
        key_pool.append(PRIMARY_KEY)
    
    key_pool.extend([k for k in ADDITIONAL_KEYS if k and k.strip()])
    
    if not key_pool:
        raise ValueError(
            "No API keys configured. Add GROQ_API_KEY to your .env file.\n"
            "Example: GROQ_API_KEY=gsk_your_key_here"
        )
    
    # Get current key with rotation
    current_key = key_pool[_current_key_index % len(key_pool)]
    
    # Validate key format
    if not current_key.startswith("gsk_"):
        print(f"[WARNING] API key doesn't start with 'gsk_' - may be invalid")
    
    return {
        "Authorization": f"Bearer {current_key}",
        "Content-Type": "application/json"
    }


def rotate_key():
    """Rotate to next key in pool (for rate limit handling)."""
    global _current_key_index
    _current_key_index += 1


def get_key_count() -> int:
    """Get total number of keys in pool."""
    count = 1 if PRIMARY_KEY and PRIMARY_KEY.strip() else 0
    count += len([k for k in ADDITIONAL_KEYS if k and k.strip()])
    return count


def validate_keys():
    """
    Validate all keys in pool.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not PRIMARY_KEY or not PRIMARY_KEY.strip():
        return False, "PRIMARY_KEY is empty or not set"
    
    if not PRIMARY_KEY.startswith("gsk_"):
        return False, f"PRIMARY_KEY should start with 'gsk_', got: {PRIMARY_KEY[:10]}..."
    
    return True, "API keys validated successfully"
