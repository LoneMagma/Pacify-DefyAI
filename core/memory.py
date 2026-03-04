"""
Pacify & Defy - Memory Management System v-2.0.0

Changes from v1:
- Added `users` table for multi-user support
- Added dedicated `session_state` table (no longer abuses `preferences`)
- VADER sentiment analysis with keyword fallback
- Opinion extraction actually wired and called
- Context returned as token-budgeted list for multi-turn formatting
- Fixed: cleanup_old_data was deleting ALL conversations older than 30d regardless of user
"""

import sqlite3
import datetime
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, List, Tuple

from .config import (
    DB_PATH,
    DEFAULT_CONTEXT_LIMIT,
    MEMORY_RETENTION_DAYS,
    EMOTIONAL_TRACKING_HOURS,
    OPINION_CONFIDENCE_THRESHOLD,
    POSITIVE_KEYWORDS,
    NEGATIVE_KEYWORDS,
    EMOTIONAL_KEYWORDS,
    PLAYFUL_SIGNALS,
    MAX_SESSION_ERRORS,
    SESSION_STATE_FIELDS,
    VADER_AVAILABLE,
    MAX_CONTEXT_TOKENS,
    CHARS_PER_TOKEN,
    OPINION_SIGNAL_PHRASES,
    OPINION_TOPIC_KEYWORDS,
)


class MemoryManager:
    """
    Manages all database operations with complete user data isolation.
    v2: Users table, dedicated session_state table, VADER sentiment.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._vader = None
        self._init_vader()
        self._init_database()
        self.session_errors: List[Dict] = []

    def _init_vader(self):
        """Load VADER if available."""
        if VADER_AVAILABLE:
            try:
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                self._vader = SentimentIntensityAnalyzer()
            except Exception:
                self._vader = None

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrent reads
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Create all tables. Idempotent — safe to call on every startup."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            # ---- Users (new in v2) ----
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    username     TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    created_at   TEXT NOT NULL,
                    last_seen    TEXT
                )
            """)

            # Ensure default user 1 exists
            cur.execute("""
                INSERT OR IGNORE INTO users (id, username, display_name, created_at)
                VALUES (1, 'default', 'You', ?)
            """, (datetime.datetime.now().isoformat(),))

            # ---- Conversations ----
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL,
                    timestamp     TEXT NOT NULL,
                    user_input    TEXT NOT NULL,
                    ai_response   TEXT NOT NULL,
                    mode          TEXT NOT NULL,
                    persona       TEXT NOT NULL,
                    mood          TEXT,
                    session_id    TEXT,
                    word_count    INTEGER,
                    response_time REAL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # ---- Opinions (tracked per-user) ----
            cur.execute("""
                CREATE TABLE IF NOT EXISTS opinions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL,
                    topic         TEXT NOT NULL,
                    stance        TEXT NOT NULL,
                    confidence    REAL NOT NULL,
                    formed_date   TEXT NOT NULL,
                    last_mentioned TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, topic)
                )
            """)

            # ---- Emotional tracking ----
            cur.execute("""
                CREATE TABLE IF NOT EXISTS emotional_tracking (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         INTEGER NOT NULL,
                    timestamp       TEXT NOT NULL,
                    sentiment_score REAL NOT NULL,
                    detected_emotion TEXT,
                    context         TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # ---- Manual preferences ----
            cur.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    user_id  INTEGER NOT NULL,
                    key      TEXT NOT NULL,
                    value    TEXT NOT NULL,
                    set_date TEXT NOT NULL,
                    PRIMARY KEY (user_id, key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # ---- Learned preferences ----
            cur.execute("""
                CREATE TABLE IF NOT EXISTS learned_preferences (
                    user_id             INTEGER NOT NULL,
                    key                 TEXT NOT NULL,
                    value               TEXT NOT NULL,
                    confidence          REAL NOT NULL,
                    learned_date        TEXT NOT NULL,
                    reinforcement_count INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # ---- User profile ----
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    user_id INTEGER NOT NULL,
                    key     TEXT NOT NULL,
                    value   TEXT NOT NULL,
                    PRIMARY KEY (user_id, key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # ---- Session state (v2: dedicated table, not abusing preferences) ----
            cur.execute("""
                CREATE TABLE IF NOT EXISTS session_state (
                    user_id     INTEGER PRIMARY KEY,
                    last_mode   TEXT DEFAULT 'pacify',
                    last_persona TEXT DEFAULT 'pacificia',
                    last_mood   TEXT DEFAULT 'witty',
                    mode_switches INTEGER DEFAULT 0,
                    updated_at  TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # ---- Error log ----
            cur.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp  TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    message    TEXT,
                    session_id TEXT
                )
            """)

            # Indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_user_ts ON conversations(user_id, timestamp)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_opinions_user ON opinions(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_emotional_user ON emotional_tracking(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pref_user ON preferences(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lpref_user ON learned_preferences(user_id)")

            conn.commit()
            self._cleanup_old_data()

    def _cleanup_old_data(self):
        """Remove data older than retention period."""
        cutoff = (
            datetime.datetime.now() - datetime.timedelta(days=MEMORY_RETENTION_DAYS)
        ).isoformat()
        emotional_cutoff = (
            datetime.datetime.now() - datetime.timedelta(hours=EMOTIONAL_TRACKING_HOURS * 7)
        ).isoformat()

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM conversations WHERE timestamp < ?", (cutoff,))
            cur.execute("DELETE FROM emotional_tracking WHERE timestamp < ?", (emotional_cutoff,))
            cur.execute(
                "DELETE FROM error_log WHERE timestamp < ?",
                ((datetime.datetime.now() - datetime.timedelta(days=7)).isoformat(),)
            )
            conn.commit()

    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================

    def get_or_create_user(self, username: str, display_name: str = None) -> int:
        """Get user ID by username, creating the user if they don't exist."""
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            if row:
                # Update last_seen
                cur.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now, row[0]))
                conn.commit()
                return row[0]

            # Create new user
            cur.execute(
                "INSERT INTO users (username, display_name, created_at, last_seen) VALUES (?, ?, ?, ?)",
                (username, display_name or username.capitalize(), now, now)
            )
            conn.commit()
            return cur.lastrowid

    def list_users(self) -> List[Dict]:
        """List all users with basic stats."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.id, u.username, u.display_name, u.last_seen,
                       COUNT(c.id) as conv_count
                FROM users u
                LEFT JOIN conversations c ON c.user_id = u.id
                GROUP BY u.id
                ORDER BY u.last_seen DESC
            """)
            rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "username": r[1],
                "display_name": r[2],
                "last_seen": r[3],
                "conversation_count": r[4],
            }
            for r in rows
        ]

    def get_user_display_name(self, user_id: int) -> str:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT display_name FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            return row[0] if row else "User"

    # ========================================================================
    # CONVERSATIONS
    # ========================================================================

    def save_conversation(
        self,
        user_id: int,
        user_input: str,
        ai_response: str,
        mode: str,
        persona: str,
        mood: str = None,
        session_id: str = None,
        word_count: int = None,
        response_time: float = None,
    ):
        timestamp = datetime.datetime.now().isoformat()
        if word_count is None:
            word_count = len(ai_response.split())

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO conversations
                (user_id, timestamp, user_input, ai_response, mode, persona,
                 mood, session_id, word_count, response_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, timestamp, user_input, ai_response, mode, persona,
                  mood, session_id, word_count, response_time))
            conn.commit()

    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT timestamp, user_input, ai_response, mode, persona,
                       mood, word_count, response_time
                FROM conversations
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (user_id, limit))
            rows = cur.fetchall()

        return [
            {
                "timestamp":     r[0],
                "user_input":    r[1],
                "ai_response":   r[2],
                "mode":          r[3],
                "persona":       r[4],
                "mood":          r[5],
                "word_count":    r[6],
                "response_time": r[7],
            }
            for r in rows
        ]

    def get_context_messages(
        self,
        user_id: int,
        limit: int = DEFAULT_CONTEXT_LIMIT,
        mode: str = None,
        max_tokens: int = MAX_CONTEXT_TOKENS,
    ) -> List[Dict]:
        """
        Return conversation history as a token-budgeted list of
        {"role": "user"|"assistant", "content": "..."} dicts
        for proper multi-turn API calls.

        Starts from most recent and works backward until token budget is exhausted.
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            if mode:
                cur.execute("""
                    SELECT user_input, ai_response
                    FROM conversations
                    WHERE user_id = ? AND mode = ?
                    ORDER BY id DESC
                    LIMIT ?
                """, (user_id, mode, limit))
            else:
                cur.execute("""
                    SELECT user_input, ai_response
                    FROM conversations
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                """, (user_id, limit))
            rows = cur.fetchall()

        if not rows:
            return []

        # Build pairs from oldest→newest, respecting token budget
        pairs = list(reversed(rows))  # oldest first
        messages = []
        token_count = 0

        for user_input, ai_response in pairs:
            pair_tokens = (len(user_input) + len(ai_response)) // CHARS_PER_TOKEN
            if token_count + pair_tokens > max_tokens:
                break
            messages.append({"role": "user",      "content": user_input})
            messages.append({"role": "assistant",  "content": ai_response})
            token_count += pair_tokens

        return messages

    # Legacy: plain-text context (kept for fallback)
    def get_recent_context(
        self,
        user_id: int,
        limit: int = DEFAULT_CONTEXT_LIMIT,
        mode: str = None,
    ) -> str:
        messages = self.get_context_messages(user_id, limit, mode)
        if not messages:
            return ""
        lines = []
        for msg in messages:
            prefix = "User" if msg["role"] == "user" else "AI"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)

    def clear_session(self, user_id: int, session_id: str = None):
        with self._get_connection() as conn:
            cur = conn.cursor()
            if session_id:
                cur.execute(
                    "DELETE FROM conversations WHERE user_id = ? AND session_id = ?",
                    (user_id, session_id),
                )
            else:
                cur.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            conn.commit()

    # ========================================================================
    # SESSION STATE (dedicated table, not preferences anymore)
    # ========================================================================

    def save_session_state(self, user_id: int, state: Dict):
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO session_state
                    (user_id, last_mode, last_persona, last_mood, mode_switches, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    last_mode    = excluded.last_mode,
                    last_persona = excluded.last_persona,
                    last_mood    = excluded.last_mood,
                    mode_switches = excluded.mode_switches,
                    updated_at   = excluded.updated_at
            """, (
                user_id,
                state.get("last_mode", "pacify"),
                state.get("last_persona", "pacificia"),
                state.get("last_mood", "witty"),
                state.get("mode_switches", 0),
                now,
            ))
            conn.commit()

    def load_session_state(self, user_id: int) -> Optional[Dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT last_mode, last_persona, last_mood, mode_switches, updated_at
                FROM session_state WHERE user_id = ?
            """, (user_id,))
            row = cur.fetchone()
        if not row:
            return None
        return {
            "last_mode":              row[0],
            "last_persona":           row[1],
            "last_mood":              row[2],
            "mode_switches":          row[3],
            "last_session_timestamp": row[4],
        }

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_stats(self, user_id: int) -> Dict:
        with self._get_connection() as conn:
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
            total = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM conversations WHERE user_id = ? AND mode = 'pacify'",
                (user_id,)
            )
            pacify_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM conversations WHERE user_id = ? AND mode = 'defy'",
                (user_id,)
            )
            defy_count = cur.fetchone()[0]

            cur.execute("""
                SELECT persona, COUNT(*)
                FROM conversations WHERE user_id = ?
                GROUP BY persona ORDER BY COUNT(*) DESC
            """, (user_id,))
            persona_usage = dict(cur.fetchall())

            cur.execute(
                "SELECT AVG(response_time) FROM conversations WHERE user_id = ? AND response_time IS NOT NULL",
                (user_id,)
            )
            avg_time = cur.fetchone()[0] or 0

            cur.execute(
                "SELECT AVG(word_count) FROM conversations WHERE user_id = ? AND word_count IS NOT NULL",
                (user_id,)
            )
            avg_words = cur.fetchone()[0] or 0

            # Opinion count
            cur.execute("SELECT COUNT(*) FROM opinions WHERE user_id = ?", (user_id,))
            opinion_count = cur.fetchone()[0]

        # Get session state for current mode/persona
        session = self.load_session_state(user_id)
        return {
            "total":            total,
            "pacify_count":     pacify_count,
            "defy_count":       defy_count,
            "persona_usage":    persona_usage,
            "avg_response_time": round(avg_time, 2),
            "avg_word_count":   round(avg_words, 1),
            "current_mode":     session.get("last_mode", "pacify") if session else "pacify",
            "current_persona":  session.get("last_persona", "pacificia") if session else "pacificia",
            "opinion_count":    opinion_count,
        }

    # ========================================================================
    # USER PROFILE
    # ========================================================================

    def get_user_name(self, user_id: int) -> Optional[str]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM user_profile WHERE user_id = ? AND key = 'user_name'",
                (user_id,)
            )
            result = cur.fetchone()
            return result[0] if result else None

    def set_user_name(self, user_id: int, name: str):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO user_profile VALUES (?, ?, ?)",
                (user_id, "user_name", name)
            )
            conn.commit()

    # ========================================================================
    # PREFERENCES
    # ========================================================================

    def get_preference(self, user_id: int, key: str) -> Optional[str]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM preferences WHERE user_id = ? AND key = ?",
                (user_id, key)
            )
            result = cur.fetchone()
            return result[0] if result else None

    def set_preference(self, user_id: int, key: str, value: str):
        timestamp = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO preferences VALUES (?, ?, ?, ?)",
                (user_id, key, value, timestamp)
            )
            conn.commit()

    def get_all_preferences(self, user_id: int) -> Dict[str, str]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT key, value FROM preferences WHERE user_id = ?",
                (user_id,)
            )
            return dict(cur.fetchall())

    # ========================================================================
    # LEARNED PREFERENCES
    # ========================================================================

    def learn_preference(self, user_id: int, key: str, value: str, confidence: float = 0.7):
        """
        Learn a preference. On repeat signals, confidence increases exponentially
        (reinforcement) rather than just averaging.
        """
        timestamp = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT confidence, reinforcement_count
                FROM learned_preferences WHERE user_id = ? AND key = ?
            """, (user_id, key))
            existing = cur.fetchone()

            if existing:
                old_conf, count = existing
                # Reinforcement: each repeat pushes confidence closer to 1.0
                new_conf = min(old_conf + (1.0 - old_conf) * 0.3, 1.0)
                new_count = count + 1
                cur.execute("""
                    UPDATE learned_preferences
                    SET value = ?, confidence = ?, reinforcement_count = ?
                    WHERE user_id = ? AND key = ?
                """, (value, new_conf, new_count, user_id, key))
            else:
                cur.execute("""
                    INSERT INTO learned_preferences VALUES (?, ?, ?, ?, ?, 1)
                """, (user_id, key, value, confidence, timestamp))
            conn.commit()

    def get_learned_preference(
        self, user_id: int, key: str, min_confidence: float = 0.6
    ) -> Optional[str]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT value FROM learned_preferences
                WHERE user_id = ? AND key = ? AND confidence >= ?
            """, (user_id, key, min_confidence))
            result = cur.fetchone()
            return result[0] if result else None

    def get_all_learned_preferences(self, user_id: int) -> List[Dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT key, value, confidence, reinforcement_count
                FROM learned_preferences WHERE user_id = ?
                ORDER BY confidence DESC
            """, (user_id,))
            return [
                {"key": r[0], "value": r[1], "confidence": r[2], "reinforcement_count": r[3]}
                for r in cur.fetchall()
            ]

    # ========================================================================
    # OPINION TRACKING (now actually wired up via extract_opinions())
    # ========================================================================

    def extract_and_save_opinions(self, user_id: int, user_input: str) -> List[str]:
        """
        Extract opinions from user input and persist them.
        Returns list of topics where opinions were detected.
        """
        input_lower = user_input.lower()
        detected = []

        # Only process if the message contains opinion signal phrases
        has_signal = any(phrase in input_lower for phrase in OPINION_SIGNAL_PHRASES)
        if not has_signal:
            return []

        # Match against known opinion topics
        for topic, keywords in OPINION_TOPIC_KEYWORDS.items():
            matching_keywords = [kw for kw in keywords if kw in input_lower]
            if not matching_keywords:
                continue

            # Build a stance string from the sentence context
            stance = self._extract_stance(user_input, matching_keywords[0])
            if stance:
                confidence = min(0.5 + 0.1 * len(matching_keywords), 0.9)
                self.save_opinion(user_id, topic, stance, confidence)
                detected.append(topic)

        return detected

    def _extract_stance(self, text: str, keyword: str) -> Optional[str]:
        """Extract the stance from text around the keyword."""
        text_lower = text.lower()
        idx = text_lower.find(keyword)
        if idx == -1:
            return None
        # Extract a window of context around the keyword
        start = max(0, idx - 60)
        end = min(len(text), idx + 80)
        snippet = text[start:end].strip()
        # Truncate to sentence
        for punct in ['.', '!', '?', ',']:
            if punct in snippet:
                snippet = snippet.split(punct)[0].strip()
        return snippet[:200] if snippet else None

    def save_opinion(self, user_id: int, topic: str, stance: str, confidence: float = 0.7):
        timestamp = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT confidence FROM opinions WHERE user_id = ? AND topic = ?",
                (user_id, topic)
            )
            existing = cur.fetchone()
            if existing:
                # Reinforce (same logic as preferences)
                new_conf = min(existing[0] + (1.0 - existing[0]) * 0.3, 1.0)
                cur.execute("""
                    UPDATE opinions
                    SET stance = ?, confidence = ?, last_mentioned = ?
                    WHERE user_id = ? AND topic = ?
                """, (stance, new_conf, timestamp, user_id, topic))
            else:
                cur.execute("""
                    INSERT INTO opinions
                    (user_id, topic, stance, confidence, formed_date, last_mentioned)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, topic, stance, confidence, timestamp, timestamp))
            conn.commit()

    def get_opinion(self, user_id: int, topic: str) -> Optional[Tuple[str, float]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT stance, confidence FROM opinions
                WHERE user_id = ? AND topic LIKE ?
            """, (user_id, f"%{topic}%"))
            result = cur.fetchone()
            return result if result else None

    def get_all_opinions(
        self, user_id: int, min_confidence: float = OPINION_CONFIDENCE_THRESHOLD
    ) -> List[Dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT topic, stance, confidence, last_mentioned
                FROM opinions
                WHERE user_id = ? AND confidence >= ?
                ORDER BY confidence DESC
                LIMIT 30
            """, (user_id, min_confidence))
            return [
                {
                    "topic": r[0],
                    "stance": r[1],
                    "confidence": r[2],
                    "last_mentioned": r[3],
                }
                for r in cur.fetchall()
            ]

    # ========================================================================
    # SENTIMENT ANALYSIS (VADER with keyword fallback)
    # ========================================================================

    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment using VADER if available, else keyword fallback.
        Returns: {score: float, emotion: str, label: str}
        """
        if self._vader:
            return self._analyze_with_vader(text)
        return self._analyze_with_keywords(text)

    # Make it callable as a static-style method too (legacy compat)
    @staticmethod
    def analyze_sentiment_static(text: str) -> Dict:
        """Static fallback for legacy callers."""
        text_lower = text.lower()
        score = 0.0
        pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
        neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
        if pos + neg > 0:
            score = (pos - neg) / (pos + neg)
        emotion = "neutral"
        if score > 0.3:
            emotion = "positive"
        elif score < -0.3:
            emotion = "negative"
        return {
            "score": score,
            "emotion": emotion,
            "label": "POSITIVE" if score > 0 else "NEGATIVE" if score < 0 else "NEUTRAL",
        }

    def _analyze_with_vader(self, text: str) -> Dict:
        scores = self._vader.polarity_scores(text)
        compound = scores["compound"]  # -1 to 1, handles negation correctly
        if compound >= 0.05:
            emotion = "positive"
            label = "POSITIVE"
        elif compound <= -0.05:
            emotion = "negative"
            label = "NEGATIVE"
        else:
            emotion = "neutral"
            label = "NEUTRAL"

        # Map to richer emotions
        if compound > 0.5:
            emotion = "excited"
        elif 0.05 <= compound <= 0.5:
            emotion = "positive"
        elif compound < -0.5:
            emotion = "distressed"
        elif -0.05 > compound >= -0.5:
            emotion = "negative"
        else:
            emotion = "neutral"

        return {"score": round(compound, 3), "emotion": emotion, "label": label}

    def _analyze_with_keywords(self, text: str) -> Dict:
        """Keyword fallback — no negation handling but better than nothing."""
        text_lower = text.lower()
        pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
        neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
        score = (pos - neg) / max(pos + neg, 1) if (pos + neg) > 0 else 0.0
        emotion = "neutral"
        if score > 0.3:
            emotion = "positive"
        elif score < -0.3:
            emotion = "negative"
        return {
            "score": round(score, 3),
            "emotion": emotion,
            "label": "POSITIVE" if score > 0 else "NEGATIVE" if score < 0 else "NEUTRAL",
        }

    # ========================================================================
    # EMOTIONAL TRACKING
    # ========================================================================

    def track_emotion(
        self, user_id: int, sentiment_score: float,
        emotion: str = None, context: str = None
    ):
        timestamp = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO emotional_tracking
                (user_id, timestamp, sentiment_score, detected_emotion, context)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, timestamp, sentiment_score, emotion, context))
            conn.commit()

    def get_emotional_pattern(self, user_id: int) -> Optional[Dict]:
        cutoff = (
            datetime.datetime.now() - datetime.timedelta(hours=EMOTIONAL_TRACKING_HOURS)
        ).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT sentiment_score, detected_emotion
                FROM emotional_tracking
                WHERE user_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 30
            """, (user_id, cutoff))
            rows = cur.fetchall()

        if not rows:
            return None

        scores = [r[0] for r in rows]
        emotions = [r[1] for r in rows if r[1]]
        avg_sentiment = sum(scores) / len(scores)

        trend = (
            "positive" if avg_sentiment > 0.2
            else "negative" if avg_sentiment < -0.2
            else "neutral"
        )

        emotion_counts: Dict[str, int] = {}
        for e in emotions:
            emotion_counts[e] = emotion_counts.get(e, 0) + 1
        dominant = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"

        return {
            "avg_sentiment":    round(avg_sentiment, 2),
            "trend":            trend,
            "dominant_emotion": dominant,
            "sample_size":      len(rows),
        }

    # ========================================================================
    # ERROR TRACKING
    # ========================================================================

    def track_error(self, error_type: str, message: str, session_id: str = None):
        """Persist error to DB and keep in-session list."""
        timestamp = datetime.datetime.now().isoformat()
        self.session_errors.append({
            "type": error_type,
            "message": message,
            "timestamp": timestamp,
        })
        # Keep only last N in memory
        if len(self.session_errors) > MAX_SESSION_ERRORS:
            self.session_errors = self.session_errors[-MAX_SESSION_ERRORS:]

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO error_log (timestamp, error_type, message, session_id)
                    VALUES (?, ?, ?, ?)
                """, (timestamp, error_type, message[:500], session_id))
                conn.commit()
        except Exception:
            pass  # Error tracking must never crash the app

    def get_recent_errors(self, limit: int = 5) -> List[Dict]:
        """Get recent errors from DB."""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT timestamp, error_type, message
                    FROM error_log
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
                return [
                    {"timestamp": r[0], "type": r[1], "message": r[2]}
                    for r in cur.fetchall()
                ]
        except Exception:
            return self.session_errors[-limit:]
