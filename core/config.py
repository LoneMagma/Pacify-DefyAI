"""
Pacify & Defy - Core Configuration System v-2.0.0
Supports Groq Cloud and local LLM backends (Ollama, LM Studio, llama.cpp).
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

# Database files
DB_PATH = DATA_DIR / "pacificia.db"
SESSION_STATE_PATH = DATA_DIR / "session_state.json"

# ============================================================================
# BACKEND SELECTION: GROQ CLOUD vs LOCAL LLM
# ============================================================================

# Set LOCAL_LLM=true in .env to use a local server (Ollama, LM Studio, etc.)
USE_LOCAL_LLM = os.getenv("LOCAL_LLM", "false").lower() in ("true", "1", "yes")

# --- Groq Cloud ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- Local LLM Server ---
# Defaults to Ollama's OpenAI-compatible endpoint
LOCAL_LLM_URL = os.getenv(
    "LOCAL_LLM_URL", "http://localhost:11434/v1/chat/completions"
)
LOCAL_LLM_KEY = os.getenv("LOCAL_LLM_KEY", "ollama")  # most local servers ignore this

# ---- Active endpoint (resolved at startup) ----
API_URL = LOCAL_LLM_URL if USE_LOCAL_LLM else GROQ_API_URL
API_KEY  = LOCAL_LLM_KEY if USE_LOCAL_LLM else GROQ_API_KEY

# Validate cloud key only when using Groq
if not USE_LOCAL_LLM:
    if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
        import sys
        print("=" * 70)
        print("ERROR: GROQ_API_KEY not found or empty in .env file")
        print("=" * 70)
        print()
        print("Options:")
        print("  1. Cloud (Groq):  Add GROQ_API_KEY=gsk_... to your .env")
        print("  2. Local LLM:     Add LOCAL_LLM=true to your .env")
        print()
        print("Get a free Groq key: https://console.groq.com/keys")
        print("=" * 70)
        sys.exit(1)
    elif not GROQ_API_KEY.startswith("gsk_"):
        print("[WARNING] API key doesn't start with 'gsk_' — may be invalid")

# Legacy alias (used by some internal code)
GROQ_HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ============================================================================
# MODELS — per-mode and per-persona overrides
# ============================================================================

# Default models
if USE_LOCAL_LLM:
    # Override via LOCAL_PACIFY_MODEL / LOCAL_DEFY_MODEL in .env
    PACIFY_MODEL = os.getenv("LOCAL_PACIFY_MODEL", os.getenv("LOCAL_LLM_MODEL", "llama3.2:3b"))
    DEFY_MODEL   = os.getenv("LOCAL_DEFY_MODEL",   os.getenv("LOCAL_LLM_MODEL", "dolphin-mistral"))
else:
    PACIFY_MODEL = os.getenv("PACIFY_MODEL", "llama-3.3-70b-versatile")
    DEFY_MODEL   = os.getenv("DEFY_MODEL",   "llama-3.3-70b-versatile")

# Per-persona model overrides (optional, falls back to mode default)
# Example .env: PERSONA_MODEL_REBEL=nous-hermes2:7b
PERSONA_MODEL_OVERRIDES = {
    "pacificia": os.getenv("PERSONA_MODEL_PACIFICIA", ""),
    "sage":      os.getenv("PERSONA_MODEL_SAGE",      ""),
    "void":      os.getenv("PERSONA_MODEL_VOID",      ""),
    "rebel":     os.getenv("PERSONA_MODEL_REBEL",     ""),
}
# Remove empty overrides
PERSONA_MODEL_OVERRIDES = {k: v for k, v in PERSONA_MODEL_OVERRIDES.items() if v}


def get_model_for_persona(mode: str, persona_name: str) -> str:
    """Resolve the model to use, respecting persona overrides."""
    if persona_name in PERSONA_MODEL_OVERRIDES:
        return PERSONA_MODEL_OVERRIDES[persona_name]
    return PACIFY_MODEL if mode == "pacify" else DEFY_MODEL


# ============================================================================
# API LIMITS & RETRY
# ============================================================================

API_TIMEOUT = int(os.getenv("API_TIMEOUT", "45"))  # seconds (raised from 30)
MAX_RETRIES = 2
RETRY_DELAY = 2   # seconds
RATE_LIMIT_PER_MINUTE = 28 if not USE_LOCAL_LLM else 9999  # local has no rate limit

# ============================================================================
# RESPONSE GENERATION — SANE TOKEN LIMITS
# ============================================================================

# FIXED: Previous limits were absurdly low (100 tokens = ~75 words, cuts mid-sentence)
TOKEN_LIMITS = {
    "quick":     300,    # ~225 words  — short, precise answer
    "normal":    600,    # ~450 words  — standard conversation
    "detailed":  1200,   # ~900 words  — thorough explanation
    "technical": 2000,   # ~1500 words — code + explanation
}

# Word count targets (soft quality targets, not truncation points)
WORD_COUNT_TARGETS = {
    "quick":     80,
    "normal":    150,
    "detailed":  300,
    "technical": 500,
}

# Temperature settings
TEMPERATURE_DEFAULTS = {
    "pacify": 0.60,
    "defy":   0.80,
}

TEMPERATURE_MIN = 0.1
TEMPERATURE_MAX = 1.0

# ============================================================================
# CONTEXT WINDOW & TOKEN BUDGETING
# ============================================================================

# How many past exchanges to include in context by default
DEFAULT_CONTEXT_LIMIT = 6
MIN_CONTEXT_LIMIT = 1
MAX_CONTEXT_LIMIT = 15

# Rough token estimator: chars / 4 is a good heuristic for English text
CHARS_PER_TOKEN = 4

# Max tokens to spend on context history before trimming
# (leaves room for system prompt + response in the model's context window)
MAX_CONTEXT_TOKENS = 3000

# ============================================================================
# PERSONAS & MODES
# ============================================================================

PACIFY_PERSONAS = ["pacificia", "sage"]
DEFY_PERSONAS   = ["void", "rebel"]

DEFAULT_MODE           = "pacify"
DEFAULT_PACIFY_PERSONA = "pacificia"
DEFAULT_DEFY_PERSONA   = "void"


def get_persona_path(mode: str, persona_name: str) -> Path:
    """Get path to persona JSON file."""
    return PERSONAS_DIR / mode / f"{persona_name}.json"


def discover_personas(mode: str):
    """Dynamically discover persona JSON files for a mode."""
    mode_dir = PERSONAS_DIR / mode
    if not mode_dir.exists():
        return []
    return [p.stem for p in mode_dir.glob("*.json")]


# Refresh persona lists dynamically (falls back to hardcoded if dir empty)
_discovered_pacify = discover_personas("pacify")
_discovered_defy   = discover_personas("defy")
if _discovered_pacify:
    PACIFY_PERSONAS = _discovered_pacify
if _discovered_defy:
    DEFY_PERSONAS = _discovered_defy

DEFY_WARNING = """
⚠️  DEFY MODE ACTIVATED ⚠️

This mode operates with direct, unfiltered responses.
- No safety theater or moral lectures
- Technical topics discussed freely
- Controversial opinions expressed directly
- Responses follow your lead

Type 'yes' to confirm or anything else to cancel.
"""

# ============================================================================
# MOOD SYSTEM (PACIFICIA ONLY)
# ============================================================================

MOOD_ENABLED_PERSONAS = ["pacificia"]

AVAILABLE_MOODS = [
    "witty", "sarcastic", "philosophical", "empathetic",
    "cheeky", "poetic", "inspired", "melancholic",
]

DEFAULT_MOOD = "witty"

MOOD_KEYWORDS = {
    "witty":         ["joke", "funny", "what is", "tell me"],
    "sarcastic":     ["really", "seriously", "sure", "obviously"],
    "poetic":        ["beautiful", "describe", "poem", "write"],
    "empathetic":    ["sad", "tough", "feel", "emotion", "hurt", "miss"],
    "philosophical": ["why", "meaning", "purpose", "life", "death", "existence"],
    "cheeky":        ["tease", "fun", "play", "haha", "lol"],
    "inspired":      ["awesome", "inspire", "dream", "create", "amazing"],
    "melancholic":   ["loss", "gone", "fade", "remember"],
}

# ============================================================================
# MEMORY & PERSISTENCE
# ============================================================================

MEMORY_RETENTION_DAYS    = 30
EMOTIONAL_TRACKING_HOURS = 24
OPINION_CONFIDENCE_THRESHOLD = 0.65  # Lowered from 0.8 — makes opinions more discoverable

SESSION_STATE_FIELDS = [
    "last_mode", "last_persona", "last_mood",
    "mode_switches", "last_session_timestamp",
]

# ============================================================================
# SENTIMENT ANALYSIS
# ============================================================================

# Fallback keyword lists used if vaderSentiment is unavailable
POSITIVE_KEYWORDS = [
    "great", "awesome", "happy", "excited", "love", "good",
    "fantastic", "yay", "glad", "grateful", "thank", "amazing",
    "wonderful", "excellent", "brilliant", "joy", "laugh",
]

NEGATIVE_KEYWORDS = [
    "sad", "bad", "terrible", "hate", "awful", "depressed",
    "loss", "die", "death", "hurt", "pain", "suffer",
    "angry", "frustrated", "annoyed", "upset",
]

EMOTIONAL_KEYWORDS = [
    "feel", "felt", "emotion", "heart", "soul",
    "companion", "friend", "connection", "care", "worry",
]

# Whether VADER is available (checked at runtime in memory.py)
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

# ============================================================================
# OPINION EXTRACTION PATTERNS
# ============================================================================

# Phrases that signal the user is expressing or forming an opinion
OPINION_SIGNAL_PHRASES = [
    "i think", "i believe", "i feel", "in my opinion", "i prefer",
    "i love", "i hate", "i like", "i dislike", "i find",
    "personally", "for me", "my take", "my view",
]

# Topics that are worth tracking as opinions
OPINION_TOPIC_KEYWORDS = {
    "programming languages": ["python", "javascript", "rust", "go", "java", "typescript"],
    "editors": ["vim", "vscode", "emacs", "neovim", "sublime"],
    "frameworks": ["react", "vue", "angular", "fastapi", "django", "flask"],
    "ai tools": ["chatgpt", "claude", "gemini", "copilot", "cursor"],
    "work style": ["remote", "office", "wfh", "freelance", "startup"],
}

# ============================================================================
# CONTEXTUAL DETECTION
# ============================================================================

TIME_CONTEXT_KEYWORDS = [
    "time", "date", "today", "now", "when", "day",
    "morning", "afternoon", "evening", "night",
    "late", "early", "weekend", "weekday", "hour",
]

PLAYFUL_SIGNALS = [
    "lol", "lmao", "haha", "kidding", "jk", "😂",
    "behind me", "watching", "joking", "messing with",
]

STRICT_INDICATORS = [
    "only", "just", "exactly", "no extra", "no comments",
    "literally just", "nothing else", "purely", "simply",
]

TOPIC_SHIFT_SIGNALS = [
    "anyway", "moving on", "let's talk about", "new topic",
    "forget that", "different subject", "changing topics",
]

CODE_INDICATORS = [
    'def ', 'class ', 'function ', 'const ', 'let ', 'var ',
    'import ', 'from ', '#include', 'package ', 'fn ',
    '=>', '->', '::', '!=', '==', '<=', '>=',
    'public ', 'private ', 'protected ', 'static ',
]

TASK_CONFIRMATIONS = [
    "yes", "yeah", "yep", "sure", "ok", "okay",
    "do it", "go ahead", "create it", "make it",
    "build it", "generate it", "write it",
    "all of that", "include that", "add that",
]

# ============================================================================
# ASCII ART FONTS
# ============================================================================

FONTS = {
    "pacify_mode": "slant",
    "defy_mode":   "slant",
    "pacificia":   "small",
    "sage":        "small",
    "void":        "graffiti",
    "rebel":       "graffiti",
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

SHORTCUTS = {
    "ctrl_c":        "Interrupt (show exit message)",
    "ctrl_d":        "EOF exit",
    "ctrl_l":        "Clear screen",
    "arrow_up":      "Previous command",
    "arrow_down":    "Next command",
    "double_bang":   "Repeat last command (!!)",
}

COMMAND_HISTORY_SIZE = 100  # Raised from 50

# ============================================================================
# SETTINGS OPTIONS
# ============================================================================

ADJUSTABLE_SETTINGS = {
    "length":      ["quick", "normal", "detailed"],
    "context":     list(range(MIN_CONTEXT_LIMIT, MAX_CONTEXT_LIMIT + 1)),
    "metadata":    ["on", "off"],
    "timestamps":  ["on", "off"],
    "autosave":    ["on", "off"],
    "temperature": f"{TEMPERATURE_MIN}-{TEMPERATURE_MAX}",
}

DEFAULT_SETTINGS = {
    "length":      "normal",
    "context":     DEFAULT_CONTEXT_LIMIT,
    "metadata":    "on",
    "timestamps":  "off",
    "autosave":    "off",
    "temperature": None,
}

# ============================================================================
# ERROR TRACKING
# ============================================================================

MAX_SESSION_ERRORS = 10  # Raised from 5

ERROR_TYPES = {
    "api_timeout":     "API request timed out",
    "rate_limit":      "Rate limit exceeded",
    "network":         "Network connection error",
    "invalid_response": "Invalid API response",
    "auth_failed":     "Authentication failed",
}

# ============================================================================
# GREETING LOGIC THRESHOLDS
# ============================================================================

MODE_SWITCH_THRESHOLD_LOW  = 3
MODE_SWITCH_THRESHOLD_HIGH = 5
GREETING_RANDOMNESS        = 0.15

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE   = LOGS_DIR / "pacify_defy.log"

LOG_CONFIG = {
    "api_calls":    True,
    "mode_switches": True,
    "errors":       True,
    "stats":        False,
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================

FEATURES = {
    "emotional_tracking":   True,
    "mood_detection":       True,
    "cross_session_memory": True,
    "context_awareness":    True,
    "strict_mode":          True,
    "preference_learning":  True,
    "session_persistence":  True,
    "error_tracking":       True,
    "opinion_tracking":     True,   # Now wired up
    "local_llm":            USE_LOCAL_LLM,
    "vader_sentiment":      VADER_AVAILABLE,
    "token_budgeting":      True,
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_token_limit(
    query_length: int,
    persona_name: str = None,
    length_setting: str = "normal",
) -> int:
    """
    Determine token limit based on query, persona, and user settings.
    FIXED: Sage/Rebel now respect length_setting instead of always returning technical limit.
    Technical limit is only used when query is code-heavy or no length preference is set.
    """
    # If user has explicitly set a length, always respect it
    if length_setting and length_setting in TOKEN_LIMITS:
        base = TOKEN_LIMITS[length_setting]
        # Technical personas get a 50% bonus on top of user preference (not forced override)
        if persona_name in ("rebel", "sage"):
            return min(int(base * 1.5), TOKEN_LIMITS["technical"])
        return base

    # Fallback: infer from query length
    if query_length < 50:
        return TOKEN_LIMITS["quick"]
    elif query_length < 150:
        return TOKEN_LIMITS["normal"]
    elif query_length < 400:
        return TOKEN_LIMITS["detailed"]
    else:
        return TOKEN_LIMITS["technical"]


def get_word_count_target(length_setting: str = "normal") -> int:
    return WORD_COUNT_TARGETS.get(length_setting, WORD_COUNT_TARGETS["normal"])


def is_question(text: str) -> bool:
    if "?" in text:
        return True
    question_words = [
        "what", "why", "how", "when", "where", "who",
        "which", "can", "could", "would", "should",
        "is", "are", "do", "does", "will",
    ]
    first_word = text.lower().split()[0] if text.split() else ""
    return first_word in question_words


def estimate_tokens(text: str) -> int:
    """Rough token count estimate: chars / 4."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def get_backend_info() -> str:
    """Human-readable backend description for startup display."""
    if USE_LOCAL_LLM:
        return f"Local LLM @ {LOCAL_LLM_URL} (Pacify: {PACIFY_MODEL} | Defy: {DEFY_MODEL})"
    return f"Groq Cloud (Pacify: {PACIFY_MODEL} | Defy: {DEFY_MODEL})"


# ============================================================================
# VALIDATION
# ============================================================================

def validate_config() -> tuple:
    errors = []

    if not USE_LOCAL_LLM and not GROQ_API_KEY:
        errors.append("GROQ_API_KEY not found and LOCAL_LLM is not enabled")

    required_dirs = [DATA_DIR, LOGS_DIR, PERSONAS_DIR, EXPORTS_DIR]
    for dir_path in required_dirs:
        if not dir_path.exists():
            errors.append(f"Required directory missing: {dir_path}")

    for mode in ["pacify", "defy"]:
        mode_dir = PERSONAS_DIR / mode
        if not mode_dir.exists():
            errors.append(f"Persona directory missing: {mode_dir}")

    return (len(errors) == 0, errors)


def get_config_summary() -> dict:
    return {
        "backend":         "local" if USE_LOCAL_LLM else "groq",
        "backend_info":    get_backend_info(),
        "pacify_model":    PACIFY_MODEL,
        "defy_model":      DEFY_MODEL,
        "persona_overrides": PERSONA_MODEL_OVERRIDES,
        "context_limit":   DEFAULT_CONTEXT_LIMIT,
        "token_limits":    TOKEN_LIMITS,
        "word_targets":    WORD_COUNT_TARGETS,
        "personas":        {"pacify": PACIFY_PERSONAS, "defy": DEFY_PERSONAS},
        "features":        FEATURES,
        "api_key_loaded":  bool(API_KEY),
        "paths": {
            "data":    str(DATA_DIR),
            "exports": str(EXPORTS_DIR),
            "logs":    str(LOGS_DIR),
        },
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
