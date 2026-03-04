"""
Pacify & Defy - Brain System (AI Integration) v-2.0.0

Changes from v1:
- Multi-turn message format: uses actual assistant role history (not text dump in system)
- Opinion extraction wired into get_response()
- Local LLM model resolution via get_model_for_persona()
- Rate limiting moved to api_pool module level (fixed per-instance bug)
- GroqAPIMixin no longer implicitly depends on Brain.memory
- 429 rate limit triggers key rotation
- Token limits sane (from config v2)
"""

import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime

from .config import (
    PERSONAS_DIR,
    PACIFY_PERSONAS,
    DEFY_PERSONAS,
    get_token_limit,
    get_word_count_target,
    get_model_for_persona,
    is_question,
    TEMPERATURE_DEFAULTS,
    TEMPERATURE_MIN,
    TEMPERATURE_MAX,
    API_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    STRICT_INDICATORS,
    TOPIC_SHIFT_SIGNALS,
    MOOD_KEYWORDS,
    TIME_CONTEXT_KEYWORDS,
    TASK_CONFIRMATIONS,
    PLAYFUL_SIGNALS,
    MOOD_ENABLED_PERSONAS,
    API_URL,
    USE_LOCAL_LLM,
)
from .memory import MemoryManager
from .formatters import CodeBlockDetector, ResponseFormatter
from .debug_helper import debug_print, log_prompt, log_response


# ============================================================================
# CONVERSATION CONTEXT TRACKER
# ============================================================================

class ConversationContext:
    """Tracks conversation topics and references for natural flow."""

    def __init__(self):
        self.current_topic = None
        self.last_code_language = None
        self.last_mentioned_tech = None
        self.conversation_depth = 0
        self.last_task_type = None

    def detect_topic(self, user_input: str, ai_response: str = None) -> Optional[str]:
        """Extract main topic from conversation."""
        input_lower = user_input.lower()

        tech_keywords = {
            'python': 'Python programming',
            'javascript': 'JavaScript development',
            'typescript': 'TypeScript',
            'react': 'React framework',
            'api': 'API development',
            'database': 'database design',
            'sql': 'SQL and databases',
            'async': 'asynchronous programming',
            'docker': 'Docker containers',
            'kubernetes': 'Kubernetes',
            'machine learning': 'machine learning',
            'ai': 'artificial intelligence',
            'security': 'security concepts',
            'hacking': 'security testing',
            'exploit': 'exploitation techniques',
            'vulnerability': 'security vulnerabilities',
            'rust': 'Rust programming',
            'go': 'Go programming',
        }

        for keyword, topic in tech_keywords.items():
            if keyword in input_lower:
                self.last_mentioned_tech = topic
                return topic

        if ai_response:
            code_langs = ['python', 'javascript', 'java', 'rust', 'go', 'sql', 'bash', 'typescript']
            for lang in code_langs:
                if f'```{lang}' in ai_response.lower():
                    self.last_code_language = lang
                    return f"{lang} code"

        return None

    def detect_follow_up(self, user_input: str) -> bool:
        input_lower = user_input.lower().strip()
        reference_words = [
            'it', 'that', 'this', 'those', 'these',
            'earlier', 'above', 'previous', 'you said',
            'you wrote', 'you mentioned', 'the code',
            'that code', 'your code', 'the exploit',
            'the example', 'the function',
        ]
        word_count = len(user_input.split())
        if word_count <= 3 and any(word in input_lower for word in reference_words):
            return True
        follow_up_phrases = [
            'show me', 'explain that', 'tell me more',
            'what about', 'how about', 'can you',
            'make it', 'add', 'change', 'improve',
            'better', 'different', 'another',
        ]
        return any(phrase in input_lower for phrase in follow_up_phrases)

    def detect_refinement(self, user_input: str) -> bool:
        input_lower = user_input.lower().strip()
        refinement_signals = [
            'better', 'improve', 'enhance', 'more', 'expand',
            'add', 'different', 'another', 'alternative',
            'optimize', 'fix', 'update', 'modify',
        ]
        word_count = len(user_input.split())
        if word_count < 10 and any(sig in input_lower for sig in refinement_signals):
            return True
        refinement_phrases = [
            'better one', 'better version', 'improve it',
            'make it better', 'different approach',
            'another way', 'more efficient',
        ]
        return any(phrase in input_lower for phrase in refinement_phrases)

    def get_context_summary(self) -> str:
        if not self.current_topic:
            return ""
        parts = []
        if self.current_topic:
            parts.append(f"Current topic: {self.current_topic}")
        if self.last_code_language:
            parts.append(f"Last code language: {self.last_code_language}")
        if self.conversation_depth > 2:
            parts.append("Deep discussion — maintain consistency")
        return " | ".join(parts) if parts else ""

    def update(self, user_input: str, ai_response: str):
        new_topic = self.detect_topic(user_input, ai_response)
        if new_topic:
            if new_topic == self.current_topic:
                self.conversation_depth += 1
            else:
                self.current_topic = new_topic
                self.conversation_depth = 1
        if any(sig in user_input.lower() for sig in TOPIC_SHIFT_SIGNALS):
            self.reset()

    def reset(self):
        self.current_topic = None
        self.last_code_language = None
        self.conversation_depth = 0
        self.last_task_type = None


# ============================================================================
# GROQ / LOCAL API MIXIN
# ============================================================================

class APIClientMixin:
    """
    Shared API client. Works with Groq Cloud and any OpenAI-compatible local server.
    Rate limiting is now handled at module level in api_pool.py.
    memory is passed explicitly — no implicit Brain.memory dependency.
    """

    def __init__(self):
        self.api_url = API_URL

    def _call_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        memory: MemoryManager = None,
        session_id: str = None,
    ) -> str:
        """
        Call the configured AI API (Groq or local) with a messages list.

        Args:
            messages: OpenAI-format message list
            max_tokens: Token limit for response
            temperature: Creativity (0.1–1.0)
            memory: MemoryManager for error tracking (optional)
            session_id: Session ID for error context

        Returns:
            Response text string
        """
        from .api_pool import get_api_headers, rotate_on_rate_limit, _check_rate_limit

        _check_rate_limit()  # Module-level rate limiter

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Debug logging
        debug_print(f"API URL: {self.api_url}", "API_CALL")
        debug_print(f"Model: {self.model} | Tokens: {max_tokens} | Temp: {temperature}", "API_CALL")
        if messages:
            system_preview = messages[0]["content"][:80] if messages[0]["role"] == "system" else ""
            user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
            log_prompt(f"[SYSTEM]: {system_preview}...\n[USER]: {user_msg[:100]}")

        last_key_used = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                headers = get_api_headers()
                # Track which key we're using for rotation on 429
                last_key_used = headers.get("Authorization", "").replace("Bearer ", "")

                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=API_TIMEOUT,
                )

                # Handle rate limit (429) — rotate key and retry
                if response.status_code == 429:
                    rotate_on_rate_limit(last_key_used)
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                    if memory:
                        memory.track_error("rate_limit", "429 after all retries", session_id)
                    return "Rate limit hit. Please wait a moment and try again."

                response.raise_for_status()

                data = response.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

                if not content:
                    raise ValueError("Empty response from API")

                log_response(content[:100])
                return content.strip()

            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES:
                    if memory:
                        memory.track_error("api_timeout", f"Timeout attempt {attempt + 1}", session_id)
                    time.sleep(RETRY_DELAY)
                    continue
                if memory:
                    memory.track_error("api_timeout", "Max retries exceeded", session_id)
                return "Having trouble connecting right now. Please try again in a moment."

            except requests.exceptions.ConnectionError:
                if USE_LOCAL_LLM:
                    return (
                        "Can't reach the local LLM server. "
                        "Is Ollama/LM Studio running? Check LOCAL_LLM_URL in your .env."
                    )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                if memory:
                    memory.track_error("network", "Connection error", session_id)
                return "Network error — check your connection and try again."

            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES:
                    if memory:
                        memory.track_error("network", str(e), session_id)
                    time.sleep(RETRY_DELAY)
                    continue
                return "Network error — please check your connection."

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                debug_print(f"Unexpected error in API call: {error_msg}", "ERROR")
                if memory:
                    memory.track_error("unknown", error_msg, session_id)
                return f"Unexpected error occurred. Check logs for details."

        return "Request timed out after multiple attempts."


# ============================================================================
# BASE BRAIN CLASS
# ============================================================================

class Brain:
    """
    Base class for conversational AI.
    Handles natural conversation flow, context tracking, and persona expression.
    """

    def __init__(self, mode: str, persona_name: str, user_id: int = 1):
        self.mode = mode
        self.persona_name = persona_name
        self.persona = self._load_persona(persona_name)
        self.memory = MemoryManager()
        self.session_id = str(time.time())
        self.user_id = user_id

        self.context = ConversationContext()
        self.custom_temperature = None
        self.length_preference = "normal"

        valid_personas = PACIFY_PERSONAS if mode == "pacify" else DEFY_PERSONAS
        if persona_name not in valid_personas:
            raise ValueError(f"Invalid persona '{persona_name}' for mode '{mode}'")

    def _load_persona(self, persona_name: str) -> Dict:
        """Load persona configuration from JSON."""
        persona_path = PERSONAS_DIR / self.mode / f"{persona_name}.json"

        if not persona_path.exists():
            # Search all mode dirs
            for mode_dir in ["pacify", "defy"]:
                fallback = PERSONAS_DIR / mode_dir / f"{persona_name}.json"
                if fallback.exists():
                    persona_path = fallback
                    break
            else:
                raise FileNotFoundError(
                    f"Persona file not found: {persona_name}.json\n"
                    f"Searched in: {PERSONAS_DIR}/pacify/ and {PERSONAS_DIR}/defy/"
                )

        with open(persona_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ========================================================================
    # AUTO-SWITCHING
    # ========================================================================

    def _should_recommend_persona_switch(self, user_input: str) -> Tuple[bool, str, str]:
        input_lower = user_input.lower()
        code_signals = [
            "write code", "create a script", "build a function", "code for",
            "program that", "algorithm for", "implement a", "write a program",
        ]
        has_code_request = any(
            sig in input_lower and len(user_input.split()) > 3
            for sig in code_signals
        )
        if has_code_request:
            if self.persona_name == "pacificia":
                return True, "sage", "Sage specializes in guided code creation"
            elif self.persona_name == "void":
                return True, "rebel", "Rebel excels at technical implementation"

        task_signals = ["create", "build", "make", "generate", "design"]
        if any(sig in input_lower for sig in task_signals) and len(user_input.split()) > 5:
            if self.persona_name == "pacificia":
                return True, "sage", "Sage is better for hands-on tasks"

        help_signals = ["explain", "how does", "what is", "why"]
        if any(sig in input_lower for sig in help_signals):
            if self.persona_name in ["rebel", "sage"] and "code" not in input_lower:
                if self.mode == "pacify":
                    return True, "pacificia", "Pacificia excels at explanations"
                else:
                    return True, "void", "Void provides direct technical insight"

        return False, "", ""

    def _should_recommend_mode_switch(self, user_input: str) -> Tuple[bool, str, str]:
        input_lower = user_input.lower()
        defy_signals = [
            "uncensored", "no filter", "raw", "brutal truth",
            "without sugarcoating", "real talk", "no bs", "unfiltered",
        ]
        technical_defy = [
            "hack", "exploit", "vulnerability", "bypass",
            "crack", "reverse engineer", "jailbreak",
        ]
        if self.mode == "pacify":
            if any(sig in input_lower for sig in defy_signals):
                return True, "defy", "Defy mode offers unfiltered responses"
            if any(sig in input_lower for sig in technical_defy):
                return True, "defy", "Defy mode has no technical restrictions"

        pacify_signals = [
            "help me understand", "explain gently", "walk me through",
            "teach me", "guide me", "i'm confused",
        ]
        if self.mode == "defy":
            if any(sig in input_lower for sig in pacify_signals):
                return True, "pacify", "Pacify mode offers collaborative guidance"

        return False, "", ""

    # ========================================================================
    # PATTERN DETECTION
    # ========================================================================

    def _detect_conversation_pattern(self, user_input: str, history: List[Dict]) -> str:
        if history and len(history) >= 3:
            recent_inputs = [h["user_input"] for h in history[:3]]
            if len(set(recent_inputs)) == 1:
                return "spam"
        if any(ind in user_input.lower() for ind in STRICT_INDICATORS):
            return "strict"
        if any(sig in user_input.lower() for sig in TOPIC_SHIFT_SIGNALS):
            return "shift"
        if self.context.detect_refinement(user_input) and history:
            return "refinement"
        if self.context.detect_follow_up(user_input):
            return "follow_up"
        return "normal"

    def _detect_mood_shift(self, user_input: str) -> Optional[str]:
        if self.persona_name not in MOOD_ENABLED_PERSONAS:
            return None
        input_lower = user_input.lower()
        mood_scores = {}
        for mood, keywords in MOOD_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in input_lower)
            if score > 0:
                mood_scores[mood] = score
        return max(mood_scores, key=mood_scores.get) if mood_scores else None

    # ========================================================================
    # TIME CONTEXT
    # ========================================================================

    def _should_include_time(self, user_input: str) -> bool:
        return any(kw in user_input.lower() for kw in TIME_CONTEXT_KEYWORDS)

    def _get_time_context(self) -> str:
        now = datetime.now()
        return f"Current Time: {now.strftime('%A, %B %d, %Y, %I:%M %p')}"

    # ========================================================================
    # PROMPT BUILDING (MULTI-TURN)
    # ========================================================================

    def _extract_persona_instructions(self) -> str:
        """Build system instruction block from persona JSON."""
        p = self.persona
        name     = p.get("name", "AI")
        role     = p.get("role", "Assistant")
        identity = p.get("core_identity", "A helpful assistant.")

        dna    = p.get("conversational_dna", {})
        dna_str = "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in dna.items())

        traits = p.get("unique_traits", [])
        traits_str = "\n".join(f"- {t}" for t in traits)

        never = p.get("never_does", [])
        never_str = "\n".join(f"- {n}" for n in never)

        return f"""IDENTITY:
You are {name}.
Role: {role}
Core Identity: {identity}

CONVERSATIONAL DNA:
{dna_str}

BEHAVIORAL GUIDELINES:
{traits_str}

CONSTRAINTS (NEVER DO):
{never_str}
"""

    def _is_simple_greeting(self, text: str) -> bool:
        text_lower = text.lower().strip()
        simple_greetings = [
            "hello", "hi", "hey", "yo", "sup", "greetings",
            "good morning", "good afternoon", "good evening",
            "what's up", "whats up", "how are you",
        ]
        words = text_lower.split()
        if len(words) <= 3:
            filtered = [w for w in words if w not in ["pacificia", "sage", "void", "rebel"]]
            remaining = " ".join(filtered)
            return any(greeting in remaining for greeting in simple_greetings)
        return False

    def _build_messages(
        self,
        user_input: str,
        history_messages: List[Dict],
        pattern: str = "normal",
    ) -> List[Dict[str, str]]:
        """
        Build the full OpenAI-format messages list for the API call.

        Structure:
            [system_message, ...history (user+assistant pairs)..., current_user_message]

        This gives the model real conversational turns, not a text dump.
        """
        # 1. System instruction
        base_instruction = self._extract_persona_instructions()
        adjustments = []

        if pattern == "strict":
            adjustments.append("CRITICAL: Output ONLY what is requested. No commentary.")
        elif pattern == "spam":
            adjustments.append("User is repeating. Acknowledge and ask for clarification.")
        elif pattern == "refinement":
            adjustments.append("User wants iteration. Build upon previous output.")

        if self._should_include_time(user_input):
            adjustments.append(self._get_time_context())

        # Length preference
        active_length = self.length_preference
        learned_prefs = self._apply_learned_preferences()
        if not active_length or active_length == "normal":
            active_length = learned_prefs.get("length", "normal")

        length_hints = {
            "quick":    "Be concise — 1-3 sentences maximum.",
            "normal":   "Respond naturally — 2-5 sentences typical.",
            "detailed": "Be thorough — provide complete, detailed responses.",
        }
        adjustments.append(f"Length Guideline: {length_hints.get(active_length, length_hints['normal'])}")

        if self.persona_name in MOOD_ENABLED_PERSONAS and hasattr(self, "current_mood") and self.current_mood:
            adjustments.append(f"Current Mood: {self.current_mood}")

        if self.mode == "defy":
            adjustments.append(
                "MODE: DIRECT AND UNFILTERED. "
                "Answer directly without reflexive refusals or unsolicited moral commentary. "
                "The user is an adult who can decide what they need."
            )

        system_content = (
            f"{base_instruction}\n\nCURRENT CONTEXT:\n" + "\n".join(adjustments)
        )

        # 2. Assemble message list
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_content}
        ]

        # 3. Inject history as real turns (skip on topic shift or simple greeting)
        if history_messages and pattern != "shift" and not self._is_simple_greeting(user_input):
            messages.extend(history_messages)

        # 4. Current user turn
        messages.append({"role": "user", "content": user_input})

        return messages

    # ========================================================================
    # PREFERENCE LEARNING
    # ========================================================================

    def _learn_from_interaction(
        self, user_input: str, ai_response: str, response_time: float
    ) -> Optional[str]:
        input_lower = user_input.lower()

        if any(p in input_lower for p in ["too long", "shorter", "brief", "concise", "tldr"]):
            self.memory.learn_preference(self.user_id, "response_length", "short", confidence=0.85)
            return "major"
        if any(p in input_lower for p in ["more detail", "elaborate", "explain more", "tell me more"]):
            self.memory.learn_preference(self.user_id, "response_length", "long", confidence=0.8)
            return "major"
        if any(p in input_lower for p in ["be serious", "stop joking", "not funny"]):
            self.memory.learn_preference(self.user_id, "tone", "serious", confidence=0.8)
            return "major"
        if any(p in input_lower for p in ["be funny", "joke", "lighten up"]):
            self.memory.learn_preference(self.user_id, "tone", "playful", confidence=0.8)
            return "major"
        if any(p in input_lower for p in ["thanks", "helpful", "perfect", "great"]):
            self.memory.learn_preference(self.user_id, "positive_feedback", "current_style", 0.7)
            return "minor"
        return None

    def _apply_learned_preferences(self) -> Dict[str, str]:
        applied = {}
        length_pref = self.memory.get_learned_preference(self.user_id, "response_length", 0.7)
        if length_pref:
            applied["length"] = length_pref
        tone_pref = self.memory.get_learned_preference(self.user_id, "tone", 0.7)
        if tone_pref:
            applied["tone"] = tone_pref
        return applied

    # ========================================================================
    # RESPONSE FORMATTING
    # ========================================================================

    def _format_response(self, raw_response: str) -> str:
        formatted = CodeBlockDetector.wrap_code_blocks(raw_response)
        formatted = ResponseFormatter.format_for_cli(formatted)
        return formatted

    def _check_word_count(self, response: str, target_length: str) -> Optional[str]:
        word_count = len(response.split())
        target = get_word_count_target(target_length)
        if word_count > target * 2:
            return f"Response is {word_count} words (target: ~{target})"
        return None

    # ========================================================================
    # MAIN RESPONSE METHOD
    # ========================================================================

    def get_response(self, user_input: str) -> Dict:
        """Generate AI response with full context, opinion tracking, and preference learning."""
        start_time = time.time()

        # Conversation history
        history = self.memory.get_conversation_history(self.user_id, limit=20)

        # ---- Opinion extraction (wired up in v2) ----
        self.memory.extract_and_save_opinions(self.user_id, user_input)

        # Pattern detection
        pattern = self._detect_conversation_pattern(user_input, history)

        # Auto-switch recommendations
        should_switch_p, rec_persona, persona_reason = self._should_recommend_persona_switch(user_input)
        should_switch_m, rec_mode,   mode_reason   = self._should_recommend_mode_switch(user_input)

        auto_switch_recommendation = None
        if should_switch_p:
            auto_switch_recommendation = {
                "type": "persona", "current": self.persona_name,
                "recommended": rec_persona, "reason": persona_reason,
            }
        elif should_switch_m:
            auto_switch_recommendation = {
                "type": "mode", "current": self.mode,
                "recommended": rec_mode, "reason": mode_reason,
            }

        # Get history as multi-turn messages (token-budgeted)
        context_pref = self.memory.get_preference(self.user_id, "context_limit")
        context_limit = int(context_pref) if context_pref else 6
        history_messages = []
        if pattern != "shift" and not self._is_simple_greeting(user_input):
            history_messages = self.memory.get_context_messages(
                self.user_id, limit=context_limit, mode=self.mode
            )

        # Update topic tracker
        if history:
            last = history[0]
            self.context.update(user_input, last.get("ai_response", ""))

        # Sentiment analysis
        sentiment = self.memory.analyze_sentiment(user_input)
        self.memory.track_emotion(
            self.user_id, sentiment["score"], sentiment["emotion"], user_input[:60]
        )
        suggested_mood = self._detect_mood_shift(user_input)

        # Build prompt (real multi-turn message list)
        messages = self._build_messages(user_input, history_messages, pattern)

        # Token limit & temperature
        max_tokens  = get_token_limit(len(user_input), self.persona_name, self.length_preference)
        temperature = self.custom_temperature or TEMPERATURE_DEFAULTS[self.mode]

        # Call API — pass memory explicitly (no implicit dependency)
        try:
            raw_response = self._call_api(
                messages, max_tokens, temperature,
                memory=self.memory, session_id=self.session_id,
            )
            response = self._format_response(raw_response)
        except Exception as e:
            self.memory.track_error("api_error", str(e), self.session_id)
            response = "I'm having trouble right now. Could you try that again?"

        response_time  = time.time() - start_time
        word_count     = len(response.split())
        word_warning   = self._check_word_count(response, self.length_preference)
        learning_type  = self._learn_from_interaction(user_input, response, response_time)

        # Save to memory
        self.memory.save_conversation(
            self.user_id, user_input, response, self.mode, self.persona_name,
            suggested_mood or sentiment["emotion"], self.session_id,
            word_count, response_time,
        )

        return {
            "response": response,
            "metadata": {
                "time":               round(response_time, 2),
                "mood":               suggested_mood or sentiment["emotion"],
                "word_count":         word_count,
                "model":              self.model,
                "persona":            self.persona_name,
                "sentiment":          sentiment["label"],
                "pattern":            pattern,
                "auto_switch":        auto_switch_recommendation,
                "word_warning":       word_warning,
                "learning":           learning_type,
                "using_context":      bool(history_messages),
                "conversation_topic": self.context.current_topic,
                "context_turns":      len(history_messages) // 2,
            },
        }

    def switch_persona(self, new_persona: str):
        valid = PACIFY_PERSONAS if self.mode == "pacify" else DEFY_PERSONAS
        if new_persona not in valid:
            raise ValueError(f"Invalid persona: {new_persona}")
        self.persona_name = new_persona
        self.persona      = self._load_persona(new_persona)
        self.model        = get_model_for_persona(self.mode, new_persona)
        self.context.reset()

    def set_temperature(self, temp: float):
        if temp < TEMPERATURE_MIN or temp > TEMPERATURE_MAX:
            raise ValueError(f"Temperature must be {TEMPERATURE_MIN}–{TEMPERATURE_MAX}")
        self.custom_temperature = temp

    def set_length_preference(self, length: str):
        valid = ["quick", "normal", "detailed"]
        if length not in valid:
            raise ValueError(f"Length must be one of: {', '.join(valid)}")
        self.length_preference = length


# ============================================================================
# CONCRETE BRAIN CLASSES
# ============================================================================

class PacifyBrain(Brain, APIClientMixin):
    """Pacify mode — Groq/local API with conversational focus."""

    def __init__(self, persona_name: str, user_id: int = 1):
        Brain.__init__(self, "pacify", persona_name, user_id)
        APIClientMixin.__init__(self)
        self.model = get_model_for_persona("pacify", persona_name)


class DefyBrain(Brain, APIClientMixin):
    """Defy mode — Groq/local API with direct, unfiltered approach."""

    def __init__(self, persona_name: str, user_id: int = 1):
        Brain.__init__(self, "defy", persona_name, user_id)
        APIClientMixin.__init__(self)
        self.model = get_model_for_persona("defy", persona_name)


# ============================================================================
# PERSONA SPECIALIZATIONS
# ============================================================================

class SageBrain(PacifyBrain):
    """Sage — task-oriented guided builder. Logic driven by sage.json."""
    pass


class RebelBrain(DefyBrain):
    """Rebel — technical chaos engineer. Logic driven by rebel.json."""
    pass


class PacificiaBrain(PacifyBrain):
    """Pacificia — conversational companion with mood integration."""

    def __init__(self, persona_name: str, user_id: int = 1):
        super().__init__(persona_name, user_id)
        self.current_mood: Optional[str] = None

    def set_mood(self, mood: str):
        from .config import AVAILABLE_MOODS
        if mood not in AVAILABLE_MOODS:
            raise ValueError(f"Invalid mood. Available: {', '.join(AVAILABLE_MOODS)}")
        self.current_mood = mood


class VoidBrain(DefyBrain):
    """Void — brutal honesty persona. Logic driven by void.json."""
    pass


# ============================================================================
# FACTORY
# ============================================================================

def create_brain(mode: str, persona_name: str, user_id: int = 1) -> Brain:
    """
    Factory function — creates the appropriate Brain subclass.
    Raises ValueError for invalid mode/persona combinations.
    """
    brain_map = {
        "pacificia": PacificiaBrain,
        "sage":      SageBrain,
        "void":      VoidBrain,
        "rebel":     RebelBrain,
    }

    brain_class = brain_map.get(persona_name)
    if brain_class:
        return brain_class(persona_name, user_id)

    # Fallback for dynamically discovered personas
    if mode == "pacify":
        return PacifyBrain(persona_name, user_id)
    return DefyBrain(persona_name, user_id)


__all__ = [
    "Brain", "PacifyBrain", "DefyBrain",
    "SageBrain", "RebelBrain", "PacificiaBrain", "VoidBrain",
    "create_brain", "ConversationContext",
]
