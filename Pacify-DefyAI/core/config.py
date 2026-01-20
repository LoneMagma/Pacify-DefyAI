"""
Pacify & Defy - Core Configuration System v-1.0.0
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# PROJECT STRUCTURE
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
CORE_DIR = BASE_DIR / "core"
PERSONAS_DIR = BASE_DIR / "personas"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
EXPORTS_DIR = BASE_DIR / "exports"
TESTS_DIR = BASE_DIR / "tests"

# Ensure critical directories exist
for directory in [DATA_DIR, LOGS_DIR, EXPORTS_DIR, PERSONAS_DIR]:
    directory.mkdir(exist_ok=True)

# Database and session files
DB_PATH = DATA_DIR / "pacificia.db"
SESSION_STATE_PATH = DATA_DIR / "session_state.json"

# ============================================================================
# API CONFIGURATION
# ============================================================================

# Groq API (Used for both modes currently)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Validate API key on import
if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
    import sys
    print("=" * 70)
    print("ERROR: GROQ_API_KEY not found or empty in .env file")
    print("=" * 70)
    print()
    print("Please create a .env file with your Groq API key:")
    print("  GROQ_API_KEY=gsk_your_key_here")
    print()
    print("Get your key from: https://console.groq.com/keys")
    print("=" * 70)
    sys.exit(1)
elif not GROQ_API_KEY.startswith("gsk_"):
    print("=" * 70)
    print("WARNING: API key doesn't start with 'gsk_' - may be invalid")
    print(f"Current key starts with: {GROQ_API_KEY[:10]}")
    print("=" * 70)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Models
PACIFY_MODEL = "llama-3.3-70b-versatile"
DEFY_MODEL = "llama-3.3-70b-versatile"

# Headers
GROQ_HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# API Limits & Retry
API_TIMEOUT = 30  # seconds
MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds
RATE_LIMIT_PER_MINUTE = 30  # Groq free tier

# ============================================================================
# RESPONSE GENERATION - FLUID LIMITS
# ============================================================================

# Token allocation (guidelines, not hard limits)
TOKEN_GUIDELINES = {
    "quick": 40,        # Short answers (1-2 sentences)
    "normal": 100,      # Standard conversation (2-4 sentences)
    "detailed": 350,    # In-depth responses (4-6 sentences)
    "technical": 800,  # Increased for complete code examples   # Code/technical content (Sage/Rebel)
}

# Word count targets (soft targets for quality, not truncation points)
WORD_COUNT_TARGETS = {
    "quick": 40,        # ~1-2 sentences
    "normal": 80,       # ~2-4 sentences (default)
    "detailed": 140,    # ~4-6 sentences
    "technical": 200,   # Code explanations
}

# Temperature settings (creativity control)
TEMPERATURE_DEFAULTS = {
    "pacify": 0.60,     # Balanced, consistent
    "defy": 0.80,       # Slightly more creative
}

# Temperature range for /set temperature
TEMPERATURE_MIN = 0.1
TEMPERATURE_MAX = 1.0

# ============================================================================
# PERSONAS & MODES
# ============================================================================

# Available personas
PACIFY_PERSONAS = ["pacificia", "sage"]
DEFY_PERSONAS = ["void", "rebel"]

# Defaults
DEFAULT_MODE = "pacify"
DEFAULT_PACIFY_PERSONA = "pacificia"
DEFAULT_DEFY_PERSONA = "void"

# Persona file helper
def get_persona_path(mode: str, persona_name: str) -> Path:
    """Get path to persona JSON file."""
    return PERSONAS_DIR / mode / f"{persona_name}.json"

# Mode warning message
DEFY_WARNING = """
⚠️  DEFY MODE ACTIVATED ⚠️

This mode has NO content restrictions.
- Uncensored responses
- No refusal training
- Technical freedom
- Controversial topics allowed

The AI will follow your lead without moral lectures.

Type 'yes' to confirm or anything else to cancel.
"""

# ============================================================================
# MOOD SYSTEM (PACIFICIA ONLY)
# ============================================================================

# Moods are ONLY for Pacificia persona
MOOD_ENABLED_PERSONAS = ["pacificia"]

AVAILABLE_MOODS = [
    "witty",
    "sarcastic",
    "philosophical",
    "empathetic",
    "cheeky",
    "poetic",
    "inspired",
    "melancholic",
]

DEFAULT_MOOD = "witty"

# Mood detection keywords (auto-detect for Pacificia)
MOOD_KEYWORDS = {
    "witty": ["joke", "funny", "what is", "tell me"],
    "sarcastic": ["really", "seriously", "sure", "obviously"],
    "poetic": ["beautiful", "describe", "poem", "write"],
    "empathetic": ["sad", "tough", "feel", "emotion", "hurt", "miss"],
    "philosophical": ["why", "meaning", "purpose", "life", "death", "existence"],
    "cheeky": ["tease", "fun", "play", "haha", "lol"],
    "inspired": ["awesome", "inspire", "dream", "create", "amazing"],
    "melancholic": ["loss", "gone", "fade", "remember"],
}

# ============================================================================
# MEMORY & CONTEXT
# ============================================================================

# Context window (number of previous exchanges to include)
DEFAULT_CONTEXT_LIMIT = 5
MIN_CONTEXT_LIMIT = 1
MAX_CONTEXT_LIMIT = 10

# Memory retention
MEMORY_RETENTION_DAYS = 30
EMOTIONAL_TRACKING_HOURS = 24

# Opinion tracking
OPINION_CONFIDENCE_THRESHOLD = 0.8

# ============================================================================
# SESSION STATE & PERSISTENCE
# ============================================================================

# What to persist across sessions
SESSION_STATE_FIELDS = [
    "last_mode",
    "last_persona", 
    "last_mood",
    "mode_switches",
    "last_session_timestamp",
]

# Greeting logic thresholds
MODE_SWITCH_THRESHOLD_LOW = 3   # 40% chance of witty comment
MODE_SWITCH_THRESHOLD_HIGH = 5  # 60% chance of witty comment
GREETING_RANDOMNESS = 0.15      # 15% base variation

# ============================================================================
# CONTEXTUAL AWARENESS
# ============================================================================

# Time context keywords (when to inject time/date)
TIME_CONTEXT_KEYWORDS = [
    "time", "date", "today", "now", "when", "day",
    "morning", "afternoon", "evening", "night",
    "late", "early", "weekend", "weekday", "hour"
]

# Playfulness indicators
PLAYFUL_SIGNALS = [
    "lol", "lmao", "haha", "kidding", "jk", "😂",
    "behind me", "watching", "joking", "messing with"
]

# Strict instruction indicators (follow exactly, no elaboration)
STRICT_INDICATORS = [
    "only", "just", "exactly", "no extra", "no comments",
    "literally just", "nothing else", "purely", "simply"
]

# Topic shift signals (clear context)
TOPIC_SHIFT_SIGNALS = [
    "anyway", "moving on", "let's talk about", "new topic",
    "forget that", "different subject", "changing topics"
]


# Code detection indicators
CODE_INDICATORS = [
    'def ', 'class ', 'function ', 'const ', 'let ', 'var ',
    'import ', 'from ', '#include', 'package ', 'fn ',
    '=>', '->', '::', '!=', '==', '<=', '>=',
    'public ', 'private ', 'protected ', 'static ',
]

# Task confirmation keywords (for Sage)
TASK_CONFIRMATIONS = [
    "yes", "yeah", "yep", "sure", "ok", "okay",
    "do it", "go ahead", "create it", "make it",
    "build it", "generate it", "write it",
    "all of that", "include that", "add that"
]

# ============================================================================
# SENTIMENT ANALYSIS (LOCAL)
# ============================================================================

POSITIVE_KEYWORDS = [
    "great", "awesome", "happy", "excited", "love", "good",
    "fantastic", "yay", "glad", "grateful", "thank", "amazing",
    "wonderful", "excellent", "brilliant", "joy", "laugh"
]

NEGATIVE_KEYWORDS = [
    "sad", "bad", "terrible", "hate", "awful", "depressed",
    "loss", "die", "death", "hurt", "pain", "suffer",
    "angry", "frustrated", "annoyed", "upset"
]

EMOTIONAL_KEYWORDS = [
    "feel", "felt", "emotion", "heart", "soul",
    "companion", "friend", "connection", "care", "worry"
]

# ============================================================================
# ASCII ART FONTS
# ============================================================================

# Font assignments
FONTS = {
    "pacify_mode": "slant",        # Mode banner
    "defy_mode": "slant",          # Mode banner
    "pacificia": "small",          # Persona
    "sage": "small",               # Persona
    "void": "graffiti",            # Persona
    "rebel": "graffiti",           # Persona
}

# ============================================================================
# GREETING TEMPLATES
# ============================================================================

GREETINGS = {
    "pacify": {
        "standard": [
            "Welcome back. Ready to chat?",
            "Hey there. What's on your mind?",
            "Good to see you again.",
        ],
        "mode_switch": [
            "Back in Pacify mode? Finding balance?",
            "Pacify again, huh? I'm here.",
            "Switching gears, I see. What do you need?",
        ]
    },
    "defy": {
        "standard": [
            "Back for more? Let's go.",
            "Defy mode active. What do you need?",
            "Ready when you are.",
        ],
        "mode_switch": [
            "Defy mode again? Someone's having a day.",
            "Three times in Defy? Rough week?",
            "You know where the good stuff is.",
            "Back to chaos, huh? Let's roll.",
        ]
    }
}

# ============================================================================
# TERMINAL SHORTCUTS
# ============================================================================

# Keyboard shortcuts supported
SHORTCUTS = {
    "ctrl_c": "Interrupt (show exit message)",
    "ctrl_d": "EOF exit",
    "ctrl_l": "Clear screen",
    "ctrl_u": "Clear line from cursor to start",
    "ctrl_k": "Kill line from cursor to end",
    "alt_backspace": "Delete word backward",
    "arrow_up": "Previous command",
    "arrow_down": "Next command",
    "double_bang": "Repeat last command (!!)",
}

# Command history size
COMMAND_HISTORY_SIZE = 50

# ============================================================================
# SETTINGS OPTIONS
# ============================================================================

# Available settings that can be adjusted via /set
ADJUSTABLE_SETTINGS = {
    "length": ["quick", "normal", "detailed"],
    "context": list(range(MIN_CONTEXT_LIMIT, MAX_CONTEXT_LIMIT + 1)),
    "metadata": ["on", "off"],
    "timestamps": ["on", "off"],
    "autosave": ["on", "off"],
    "temperature": f"{TEMPERATURE_MIN}-{TEMPERATURE_MAX}",
}

# Default settings
DEFAULT_SETTINGS = {
    "length": "normal",
    "context": DEFAULT_CONTEXT_LIMIT,
    "metadata": "on",
    "timestamps": "off",
    "autosave": "off",
    "temperature": None,  # Uses mode default
}

# ============================================================================
# ERROR TRACKING
# ============================================================================

# Session error tracking
MAX_SESSION_ERRORS = 5  # Keep last 5 errors in memory

# Error types
ERROR_TYPES = {
    "api_timeout": "API request timed out",
    "rate_limit": "Rate limit exceeded",
    "network": "Network connection error",
    "invalid_response": "Invalid API response",
    "auth_failed": "Authentication failed",
}

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = "INFO"
LOG_FILE = LOGS_DIR / "pacify_defy.log"

LOG_CONFIG = {
    "api_calls": True,
    "mode_switches": True,
    "errors": True,
    "stats": False,
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================

FEATURES = {
    "emotional_tracking": True,
    "mood_detection": True,
    "cross_session_memory": True,
    "context_awareness": True,
    "strict_mode": True,
    "preference_learning": True,
    "session_persistence": True,
    "error_tracking": True,
}

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config() -> tuple[bool, list[str]]:
    """
    Validate configuration on startup.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Check API key
    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY not found in .env file")
    
    # Check directories
    required_dirs = [DATA_DIR, LOGS_DIR, PERSONAS_DIR, EXPORTS_DIR]
    for dir_path in required_dirs:
        if not dir_path.exists():
            errors.append(f"Required directory missing: {dir_path}")
    
    # Check persona directories
    for mode in ["pacify", "defy"]:
        mode_dir = PERSONAS_DIR / mode
        if not mode_dir.exists():
            errors.append(f"Persona directory missing: {mode_dir}")
    
    return (len(errors) == 0, errors)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_token_limit(query_length: int, persona_name: str = None, length_setting: str = "normal") -> int:
    """
    Determine token limit based on query, persona, and user settings.
    
    Args:
        query_length: Length of user input in characters
        persona_name: Persona name (Sage/Rebel get more tokens)
        length_setting: User's length preference from /set length
    
    Returns:
        Token limit for API call
    """
    # Technical personas get more tokens
    if persona_name in ["rebel", "sage"]:
        return TOKEN_GUIDELINES["technical"]
    
    # Use length setting if specified
    if length_setting in TOKEN_GUIDELINES:
        return TOKEN_GUIDELINES[length_setting]
    
    # Otherwise, infer from query length
    if query_length < 50:
        return TOKEN_GUIDELINES["quick"]
    elif query_length < 150:
        return TOKEN_GUIDELINES["normal"]
    else:
        return TOKEN_GUIDELINES["detailed"]


def is_question(text: str) -> bool:
    """
    Detect if user input is a question.
    
    Args:
        text: User input
    
    Returns:
        True if question detected
    """
    if "?" in text:
        return True
    
    question_words = [
        "what", "why", "how", "when", "where", "who",
        "which", "can", "could", "would", "should",
        "is", "are", "do", "does", "will"
    ]
    
    first_word = text.lower().split()[0] if text.split() else ""
    return first_word in question_words


def get_word_count_target(length_setting: str = "normal") -> int:
    """
    Get target word count based on length setting.
    
    Args:
        length_setting: User's length preference
    
    Returns:
        Target word count
    """
    return WORD_COUNT_TARGETS.get(length_setting, WORD_COUNT_TARGETS["normal"])


# ============================================================================
# CONFIG SUMMARY (DEBUG)
# ============================================================================

def get_config_summary() -> dict:
    """Get configuration summary for debugging."""
    return {
        "mode_default": DEFAULT_MODE,
        "pacify_model": PACIFY_MODEL,
        "defy_model": DEFY_MODEL,
        "context_limit": DEFAULT_CONTEXT_LIMIT,
        "token_guidelines": TOKEN_GUIDELINES,
        "word_targets": WORD_COUNT_TARGETS,
        "personas": {
            "pacify": PACIFY_PERSONAS,
            "defy": DEFY_PERSONAS,
        },
        "features": FEATURES,
        "api_key_loaded": bool(GROQ_API_KEY),
        "paths": {
            "data": str(DATA_DIR),
            "exports": str(EXPORTS_DIR),
            "logs": str(LOGS_DIR),
        }
    }


# ============================================================================
# STARTUP VALIDATION
# ============================================================================

_is_valid, _errors = validate_config()

if not _is_valid:
    import sys
    print("⚠️  Configuration Errors:")
    for error in _errors:
        print(f"   - {error}")
    print("\nFix these issues before running.")
    sys.exit(1)
