"""
Pacify & Defy - Memory Management System v-1.0.0
"""

import sqlite3
import datetime
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, List, Tuple

from .config import (
    DB_PATH,
    SESSION_STATE_PATH,
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
)


class MemoryManager:
    """
    Manages database operations with COMPLETE user data isolation.
    UPDATED: All queries now filter by user_id.
    FIXED: Removed context truncation for full conversation memory.
    """
    
    def __init__(self, db_path: Path = DB_PATH):
        """
        Initialize memory manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_database()
        
        # Session-only error tracking (not persisted)
        self.session_errors = []
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Create all required tables with user_id columns."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            # Main conversation storage (WITH USER_ID)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    persona TEXT NOT NULL,
                    mood TEXT,
                    session_id TEXT,
                    word_count INTEGER,
                    response_time REAL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Opinion tracking (WITH USER_ID)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS opinions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    stance TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    formed_date TEXT NOT NULL,
                    last_mentioned TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, topic)
                )
            """)
            
            # Emotional tracking (WITH USER_ID)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS emotional_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    sentiment_score REAL NOT NULL,
                    detected_emotion TEXT,
                    context TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Manual preferences (WITH USER_ID)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    user_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    set_date TEXT NOT NULL,
                    PRIMARY KEY (user_id, key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Learned preferences (WITH USER_ID)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS learned_preferences (
                    user_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    learned_date TEXT NOT NULL,
                    reinforcement_count INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # User profile (WITH USER_ID)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    user_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (user_id, key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for performance
            cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_timestamp ON conversations(user_id, timestamp)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_opinions_user ON opinions(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_emotional_user ON emotional_tracking(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_preferences_user ON preferences(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_learned_pref_user ON learned_preferences(user_id)")
            
            conn.commit()
            
            # Cleanup old data
            self._cleanup_old_data()
    
    def _cleanup_old_data(self):
        """Remove data older than retention period (respects user_id)."""
        cutoff_date = (
            datetime.datetime.now() - datetime.timedelta(days=MEMORY_RETENTION_DAYS)
        ).isoformat()
        
        emotional_cutoff = (
            datetime.datetime.now() - datetime.timedelta(days=30)
        ).isoformat()
        
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM conversations WHERE timestamp < ?", (cutoff_date,))
            cur.execute("DELETE FROM emotional_tracking WHERE timestamp < ?", (emotional_cutoff,))
            conn.commit()
    
    # ========================================================================
    # CONVERSATION MANAGEMENT (WITH USER_ID)
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
        response_time: float = None
    ):
        """
        Save a conversation exchange to database.
        
        Args:
            user_id: User ID (REQUIRED)
            user_input: User's message
            ai_response: AI's response
            mode: 'pacify' or 'defy'
            persona: Active persona name
            mood: Detected/set mood
            session_id: Current session ID
            word_count: Words in response
            response_time: API response time
        """
        timestamp = datetime.datetime.now().isoformat()
        
        if word_count is None:
            word_count = len(ai_response.split())
        
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO conversations 
                (user_id, timestamp, user_input, ai_response, mode, persona, mood, 
                 session_id, word_count, response_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, timestamp, user_input, ai_response, mode, persona, mood,
                  session_id, word_count, response_time))
            conn.commit()
    
    def get_recent_context(
        self,
        user_id: int,
        limit: int = DEFAULT_CONTEXT_LIMIT,
        mode: str = None
    ) -> str:
        """
        Get recent conversation history formatted for context.
        FIXED: Returns FULL text without truncation!
        
        Args:
            user_id: User ID (REQUIRED)
            limit: Number of recent exchanges
            mode: Filter by mode (optional)
        
        Returns:
            Formatted conversation history
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            if mode:
                cur.execute("""
                    SELECT user_input, ai_response, persona, mood
                    FROM conversations
                    WHERE user_id = ? AND mode = ?
                    ORDER BY id DESC
                    LIMIT ?
                """, (user_id, mode, limit))
            else:
                cur.execute("""
                    SELECT user_input, ai_response, persona, mood
                    FROM conversations
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                """, (user_id, limit))
            
            rows = cur.fetchall()
        
        if not rows:
            return ""
        
        # Format in chronological order (oldest first) with FULL text
        context_lines = []
        for user_input, ai_response, persona, mood in reversed(rows):
            context_lines.append(f"User: {user_input}")  # ✅ NO TRUNCATION
            context_lines.append(f"{persona}: {ai_response}")  # ✅ NO TRUNCATION
            if mood:
                context_lines.append(f"[Mood: {mood}]")
            context_lines.append("")  # Blank line separator
        
        return "\n".join(context_lines)
    
    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get recent conversations with metadata.
        
        Args:
            user_id: User ID (REQUIRED)
            limit: Number of exchanges
        
        Returns:
            List of conversation dictionaries
        """
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
        
        conversations = []
        for row in rows:
            conversations.append({
                'timestamp': row[0],
                'user_input': row[1],
                'ai_response': row[2],
                'mode': row[3],
                'persona': row[4],
                'mood': row[5],
                'word_count': row[6],
                'response_time': row[7],
            })
        
        return conversations
    
    def clear_session(self, user_id: int, session_id: str = None):
        """
        Clear conversations for user's session.
        
        Args:
            user_id: User ID (REQUIRED)
            session_id: Session to clear (all if None)
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            if session_id:
                cur.execute(
                    "DELETE FROM conversations WHERE user_id = ? AND session_id = ?",
                    (user_id, session_id)
                )
            else:
                cur.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            conn.commit()
    
    # ========================================================================
    # STATISTICS (WITH USER_ID)
    # ========================================================================
    
    def get_stats(self, user_id: int) -> Dict:
        """
        Get comprehensive conversation statistics for user.
        
        Args:
            user_id: User ID (REQUIRED)
        
        Returns:
            Statistics dictionary
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            # Total conversations
            cur.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
            total = cur.fetchone()[0]
            
            # Mode breakdown
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
            
            # Persona usage
            cur.execute("""
                SELECT persona, COUNT(*) 
                FROM conversations
                WHERE user_id = ?
                GROUP BY persona 
                ORDER BY COUNT(*) DESC
            """, (user_id,))
            persona_usage = dict(cur.fetchall())
            
            # Average response time
            cur.execute("""
                SELECT AVG(response_time) 
                FROM conversations 
                WHERE user_id = ? AND response_time IS NOT NULL
            """, (user_id,))
            avg_time = cur.fetchone()[0] or 0
            
            # Average word count
            cur.execute("""
                SELECT AVG(word_count) 
                FROM conversations 
                WHERE user_id = ? AND word_count IS NOT NULL
            """, (user_id,))
            avg_words = cur.fetchone()[0] or 0
            
            # Current preferences
            cur.execute(
                "SELECT value FROM preferences WHERE user_id = ? AND key = 'active_mode'",
                (user_id,)
            )
            mode_result = cur.fetchone()
            current_mode = mode_result[0] if mode_result else "pacify"
            
            cur.execute(
                "SELECT value FROM preferences WHERE user_id = ? AND key = 'active_persona'",
                (user_id,)
            )
            persona_result = cur.fetchone()
            current_persona = persona_result[0] if persona_result else "pacificia"
        
        return {
            'total': total,
            'pacify_count': pacify_count,
            'defy_count': defy_count,
            'persona_usage': persona_usage,
            'avg_response_time': round(avg_time, 2),
            'avg_word_count': round(avg_words, 1),
            'current_mode': current_mode,
            'current_persona': current_persona,
        }
    
    # ========================================================================
    # USER PROFILE (WITH USER_ID)
    # ========================================================================
    
    def get_user_name(self, user_id: int) -> Optional[str]:
        """Get stored user name."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM user_profile WHERE user_id = ? AND key = 'user_name'",
                (user_id,)
            )
            result = cur.fetchone()
            return result[0] if result else None
    
    def set_user_name(self, user_id: int, name: str):
        """Save user name."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO user_profile VALUES (?, ?, ?)",
                (user_id, 'user_name', name)
            )
            conn.commit()
    
    # ========================================================================
    # PREFERENCES (WITH USER_ID)
    # ========================================================================
    
    def get_preference(self, user_id: int, key: str) -> Optional[str]:
        """Get a manual preference value."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM preferences WHERE user_id = ? AND key = ?",
                (user_id, key)
            )
            result = cur.fetchone()
            return result[0] if result else None
    
    def set_preference(self, user_id: int, key: str, value: str):
        """Set a manual preference value."""
        timestamp = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO preferences VALUES (?, ?, ?, ?)",
                (user_id, key, value, timestamp)
            )
            conn.commit()
    
    def get_all_preferences(self, user_id: int) -> Dict[str, str]:
        """Get all manual preferences."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT key, value FROM preferences WHERE user_id = ?",
                (user_id,)
            )
            return dict(cur.fetchall())
    
    # ========================================================================
    # LEARNED PREFERENCES (WITH USER_ID)
    # ========================================================================
    
    def learn_preference(
        self,
        user_id: int,
        key: str,
        value: str,
        confidence: float = 0.7
    ):
        """
        Learn a user preference automatically.
        
        Args:
            user_id: User ID (REQUIRED)
            key: Preference key (e.g., 'response_length', 'tone')
            value: Preference value
            confidence: Confidence level (0-1)
        """
        timestamp = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            # Check if preference exists
            cur.execute("""
                SELECT confidence, reinforcement_count 
                FROM learned_preferences 
                WHERE user_id = ? AND key = ?
            """, (user_id, key))
            existing = cur.fetchone()
            
            if existing:
                # Reinforce existing preference
                old_confidence, count = existing
                new_confidence = min((old_confidence + confidence) / 2, 1.0)
                new_count = count + 1
                
                cur.execute("""
                    UPDATE learned_preferences 
                    SET value = ?, confidence = ?, reinforcement_count = ?
                    WHERE user_id = ? AND key = ?
                """, (value, new_confidence, new_count, user_id, key))
            else:
                # Insert new learned preference
                cur.execute("""
                    INSERT INTO learned_preferences VALUES (?, ?, ?, ?, ?, 1)
                """, (user_id, key, value, confidence, timestamp))
            
            conn.commit()
    
    def get_learned_preference(
        self,
        user_id: int,
        key: str,
        min_confidence: float = 0.6
    ) -> Optional[str]:
        """
        Get a learned preference if confidence is high enough.
        
        Args:
            user_id: User ID (REQUIRED)
            key: Preference key
            min_confidence: Minimum confidence threshold
        
        Returns:
            Preference value or None
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT value, confidence 
                FROM learned_preferences 
                WHERE user_id = ? AND key = ? AND confidence >= ?
            """, (user_id, key, min_confidence))
            result = cur.fetchone()
            return result[0] if result else None
    
    def get_all_learned_preferences(self, user_id: int) -> List[Dict]:
        """Get all learned preferences with metadata."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT key, value, confidence, reinforcement_count
                FROM learned_preferences
                WHERE user_id = ?
                ORDER BY confidence DESC
            """, (user_id,))
            
            preferences = []
            for row in cur.fetchall():
                preferences.append({
                    'key': row[0],
                    'value': row[1],
                    'confidence': row[2],
                    'reinforcement_count': row[3],
                })
            return preferences
    
    # ========================================================================
    # OPINION TRACKING (WITH USER_ID)
    # ========================================================================
    
    def save_opinion(
        self,
        user_id: int,
        topic: str,
        stance: str,
        confidence: float = 0.7
    ):
        """
        Form or update an opinion.
        
        Args:
            user_id: User ID (REQUIRED)
            topic: Opinion topic
            stance: Opinion stance
            confidence: Confidence level
        """
        timestamp = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            # Check if opinion exists
            cur.execute(
                "SELECT confidence FROM opinions WHERE user_id = ? AND topic = ?",
                (user_id, topic)
            )
            existing = cur.fetchone()
            
            if existing:
                # Update: average confidence
                new_confidence = (existing[0] + confidence) / 2
                cur.execute("""
                    UPDATE opinions 
                    SET stance = ?, confidence = ?, last_mentioned = ?
                    WHERE user_id = ? AND topic = ?
                """, (stance, new_confidence, timestamp, user_id, topic))
            else:
                # Insert new opinion
                cur.execute("""
                    INSERT INTO opinions (user_id, topic, stance, confidence, formed_date, last_mentioned)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, topic, stance, confidence, timestamp, timestamp))
            
            conn.commit()
    
    def get_opinion(self, user_id: int, topic: str) -> Optional[Tuple[str, float]]:
        """
        Get opinion on topic.
        
        Args:
            user_id: User ID (REQUIRED)
            topic: Topic to search
        
        Returns:
            (stance, confidence) or None
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT stance, confidence 
                FROM opinions 
                WHERE user_id = ? AND topic LIKE ?
            """, (user_id, f"%{topic}%"))
            result = cur.fetchone()
            return result if result else None
    
    def get_all_opinions(
        self,
        user_id: int,
        min_confidence: float = OPINION_CONFIDENCE_THRESHOLD
    ) -> List[Dict]:
        """
        Get all opinions above confidence threshold.
        
        Args:
            user_id: User ID (REQUIRED)
            min_confidence: Minimum confidence
        
        Returns:
            List of opinion dictionaries
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT topic, stance, confidence, last_mentioned
                FROM opinions
                WHERE user_id = ? AND confidence >= ?
                ORDER BY confidence DESC
                LIMIT 20
            """, (user_id, min_confidence))
            
            opinions = []
            for row in cur.fetchall():
                opinions.append({
                    'topic': row[0],
                    'stance': row[1],
                    'confidence': row[2],
                    'last_mentioned': row[3],
                })
            return opinions
    
    # ========================================================================
    # EMOTIONAL TRACKING (WITH USER_ID)
    # ========================================================================
    
    def track_emotion(
        self,
        user_id: int,
        sentiment_score: float,
        emotion: str = None,
        context: str = None
    ):
        """
        Track user's emotional state.
        
        Args:
            user_id: User ID (REQUIRED)
            sentiment_score: Sentiment (-1 to 1)
            emotion: Emotion label
            context: Brief context
        """
        timestamp = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO emotional_tracking (user_id, timestamp, sentiment_score, detected_emotion, context)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, timestamp, sentiment_score, emotion, context))
            conn.commit()
    
    def get_emotional_pattern(self, user_id: int) -> Optional[Dict]:
        """
        Analyze recent emotional patterns.
        
        Args:
            user_id: User ID (REQUIRED)
        
        Returns:
            Emotional analysis or None
        """
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
                LIMIT 20
            """, (user_id, cutoff))
            
            rows = cur.fetchall()
        
        if not rows:
            return None
        
        # Calculate statistics
        scores = [r[0] for r in rows]
        emotions = [r[1] for r in rows if r[1]]
        
        avg_sentiment = sum(scores) / len(scores)
        
        # Determine trend
        if avg_sentiment > 0.2:
            trend = "positive"
        elif avg_sentiment < -0.2:
            trend = "negative"
        else:
            trend = "neutral"
        
        # Most common emotion
        if emotions:
            emotion_counts = {}
            for e in emotions:
                emotion_counts[e] = emotion_counts.get(e, 0) + 1
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)
        else:
            dominant_emotion = "neutral"
        
        return {
            'avg_sentiment': round(avg_sentiment, 2),
            'trend': trend,
            'dominant_emotion': dominant_emotion,
            'sample_size': len(rows)
        }
    
    # ========================================================================
    # SESSION STATE PERSISTENCE (PER-USER)
    # ========================================================================
    
    def save_session_state(self, user_id: int, state: Dict):
        """
        Save session state to user preferences.
        
        Args:
            user_id: User ID (REQUIRED)
            state: Session state dictionary
        """
        # Store session state in preferences table
        for key in SESSION_STATE_FIELDS:
            if key in state:
                self.set_preference(user_id, f"session_{key}", str(state[key]))
        
        # Update timestamp
        self.set_preference(
            user_id,
            "session_last_session_timestamp",
            datetime.datetime.now().isoformat()
        )
    
    def load_session_state(self, user_id: int) -> Optional[Dict]:
        """
        Load session state from user preferences.
        
        Args:
            user_id: User ID (REQUIRED)
        
        Returns:
            Session state dictionary or None
        """
        state = {}
        
        for field in SESSION_STATE_FIELDS:
            value = self.get_preference(user_id, f"session_{field}")
            if value:
                # Convert back to appropriate type
                if field == "mode_switches":
                    state[field] = int(value)
                else:
                    state[field] = value
        
        return state if state else None
    
    # ========================================================================
    # ERROR TRACKING (SESSION-ONLY - NO USER_ID NEEDED)
    # ========================================================================
    
    def track_error(self, error_type: str, message: str):
        """
        Track error in session memory (not persisted to DB).
        
        Args:
            error_type: Type of error
            message: Error message
        """
        error_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": error_type,
            "message": message
        }
        
        self.session_errors.append(error_entry)
        
        # Keep only last N errors
        if len(self.session_errors) > MAX_SESSION_ERRORS:
            self.session_errors = self.session_errors[-MAX_SESSION_ERRORS:]
    
    def get_recent_errors(self, limit: int = 5) -> List[Dict]:
        """Get recent session errors."""
        return self.session_errors[-limit:]
    
    def clear_session_errors(self):
        """Clear all session errors."""
        self.session_errors = []
    
    # ========================================================================
    # SENTIMENT ANALYSIS (LOCAL - NO USER_ID NEEDED)
    # ========================================================================
    
    @staticmethod
    def analyze_sentiment(text: str) -> Dict:
        """
        Fast local sentiment analysis.
        
        Args:
            text: Text to analyze
        
        Returns:
            Sentiment analysis dictionary
        """
        text_lower = text.lower()
        score = 0
        emotions = []
        
        # Count keyword matches
        pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
        neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
        emo_count = sum(1 for kw in EMOTIONAL_KEYWORDS if kw in text_lower)
        
        # Calculate score
        score = (pos_count * 0.3) - (neg_count * 0.3)
        
        # Punctuation signals
        if "!" in text:
            score += 0.2
            emotions.append("enthusiastic")
        if "?" in text and len(text) > 30:
            emotions.append("curious")
        if "..." in text:
            score -= 0.1
            emotions.append("contemplative")
        
        # Emotional engagement
        if emo_count > 0:
            score += 0.1
            emotions.append("engaged")
        
        # Length signals
        if len(text) > 200:
            emotions.append("thoughtful")
        
        # Clamp score
        score = max(min(score, 1), -1)
        
        # Determine label
        if score > 0.3:
            label = "positive"
        elif score < -0.3:
            label = "negative"
        else:
            label = "neutral"
        
        primary_emotion = emotions[0] if emotions else "neutral"
        
        # Playfulness detection
        is_playful = any(signal in text_lower for signal in PLAYFUL_SIGNALS)
        
        return {
            'score': score,
            'label': label,
            'emotion': primary_emotion,
            'intensity': abs(score),
            'is_playful': is_playful,
        }
