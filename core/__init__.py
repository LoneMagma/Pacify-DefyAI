"""
Pacify & Defy - Core Package v-1.0.0
"""

from .config import (
    BASE_DIR,
    DB_PATH,
    PERSONAS_DIR,
    GROQ_API_KEY,
    PACIFY_MODEL,
    DEFY_MODEL,
    DEFAULT_MODE,
    PACIFY_PERSONAS,
    DEFY_PERSONAS,
    validate_config,
    get_config_summary,
    get_token_limit,
    is_question,
)

from .memory import MemoryManager
from .brain import Brain, PacifyBrain

__version__ = "1.0.0"
__all__ = [
    "BASE_DIR",
    "DB_PATH",
    "PERSONAS_DIR",
    "GROQ_API_KEY",
    "PACIFY_MODEL",
    "DEFY_MODEL",
    "MODES",
    "DEFAULT_MODE",
    "PACIFY_PERSONAS",
    "DEFY_PERSONAS",
    "validate_config",
    "get_config_summary",
    "get_token_limit",
    "is_question",
    "MemoryManager",
    "Brain",
    "PacifyBrain",
]
