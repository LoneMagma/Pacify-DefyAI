"""
Personalized Farewell System v-1.0.0
Context-aware, time-based, and occasionally witty exit messages
"""

import random
from datetime import datetime
from typing import Optional


class FarewellGenerator:
    """Generate contextual farewell messages."""
    
    # Time-based farewells
    TIME_BASED = {
        "late_night": [  # 12am-4am
            "Go get some sleep. I'll be here when you need me.",
            "It's late. Rest up—conversations can wait.",
            "Burning the midnight oil? Get some rest.",
            "Late night session, huh? Sleep well.",
        ],
        "early_morning": [  # 4am-7am
            "Early start? Have a good one.",
            "Morning. Go get 'em.",
            "Rise and shine. Catch you later.",
        ],
        "morning": [  # 7am-12pm
            "Have a productive morning.",
            "Enjoy your day ahead.",
            "See you around.",
        ],
        "afternoon": [  # 12pm-5pm
            "Later. Take care.",
            "Catch you later.",
            "See you soon.",
        ],
        "evening": [  # 5pm-9pm
            "Have a good evening.",
            "Enjoy the rest of your night.",
            "Later.",
        ],
        "night": [  # 9pm-12am
            "Good night. See you tomorrow.",
            "Rest up. Catch you later.",
            "Night. Sleep well.",
        ]
    }
    
    # Session-length based (subtle experience references)
    SESSION_BASED = {
        "very_short": [  # < 2 exchanges
            "That was quick. See you next time.",
            "Brief visit. Later.",
            "Catch you later.",
        ],
        "short": [  # 2-5 exchanges
            "Good chat. See you around.",
            "Later. Take care.",
            "See you next time.",
        ],
        "medium": [  # 6-15 exchanges
            "Thanks for the conversation. Later.",
            "Good talking with you. See you soon.",
            "That was a solid chat. Catch you later.",
        ],
        "long": [  # 16-30 exchanges
            "We covered some ground today. See you next time.",
            "That was a good session. Later.",
            "Productive chat. Catch you later.",
        ],
        "marathon": [  # 30+ exchanges
            "Quite the session we had. Go stretch your legs.",
            "Long conversation. Hope it helped. See you soon.",
            "Marathon chat completed. Rest up.",
        ]
    }
    
    # Persona-specific (rare, 10% chance)
    PERSONA_SPECIFIC = {
        "pacificia": [
            "Until next time, friend. 💙",
            "Take care of yourself. I'll be here when you need me.",
            "Later, space cowboy. ✨",
        ],
        "sage": [
            "Keep learning. See you next time.",
            "Remember: progress over perfection. Later.",
            "Good work today. Catch you later.",
        ],
        "void": [
            "Reality calls. Later.",
            "Back to the noise. See you in the void.",
            "Stay sharp out there.",
        ],
        "rebel": [
            "Go cause some trouble. Responsibly.",
            "Until the next hack. Stay safe.",
            "Peace out. Don't get caught. 😈",
        ]
    }
    
    # Occasional witty/comical (5% chance)
    WITTY = [
        "Don't do anything I wouldn't do. Actually, never mind.",
        "Remember to hydrate. Seriously.",
        "Off you go. The world awaits. Or whatever.",
        "Later. Try not to break anything important.",
        "Goodbye. Please rate this conversation 5 stars. (Kidding.)",
        "See you later, alligator. (Sorry, had to.)",
        "Peace out. Touch grass if you haven't already today.",
        "Farewell, human. May your code compile on the first try.",
    ]
    
    # Mode-switch acknowledgment (if they switched modes during session)
    MODE_SWITCH = [
        "Pacify to Defy and back again. Quite the journey. Later.",
        "You switched modes {count} times. Indecisive or thorough? Either way, see you.",
        "Mode-hopping session complete. Catch you next time.",
    ]
    
    # Error recovery (if session had errors)
    ERROR_RECOVERY = [
        "Sorry about the hiccups earlier. Hopefully next session is smoother.",
        "Despite the technical difficulties, glad we got through it. Later.",
        "Rough start, but we made it work. See you next time.",
    ]
    
    @staticmethod
    def get_time_period() -> str:
        """Determine current time period."""
        hour = datetime.now().hour
        
        if 0 <= hour < 4:
            return "late_night"
        elif 4 <= hour < 7:
            return "early_morning"
        elif 7 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    @staticmethod
    def get_session_length_category(exchange_count: int) -> str:
        """Categorize session length."""
        if exchange_count < 2:
            return "very_short"
        elif exchange_count < 6:
            return "short"
        elif exchange_count < 16:
            return "medium"
        elif exchange_count < 31:
            return "long"
        else:
            return "marathon"
    
    @classmethod
    def generate(
        cls,
        persona: str,
        exchange_count: int = 0,
        mode_switches: int = 0,
        had_errors: bool = False
    ) -> str:
        """
        Generate contextual farewell message.
        
        Args:
            persona: Current persona name
            exchange_count: Number of exchanges in session
            mode_switches: Number of mode switches
            had_errors: Whether session had errors
        
        Returns:
            Farewell message
        """
        # Error recovery message (if applicable, 30% chance)
        if had_errors and random.random() < 0.3:
            return random.choice(cls.ERROR_RECOVERY)
        
        # Mode switch acknowledgment (if 3+ switches)
        if mode_switches >= 3 and random.random() < 0.4:
            message = random.choice(cls.MODE_SWITCH)
            return message.replace("{count}", str(mode_switches))
        
        # Witty message (5% chance)
        if random.random() < 0.05:
            return random.choice(cls.WITTY)
        
        # Persona-specific (10% chance)
        if persona in cls.PERSONA_SPECIFIC and random.random() < 0.10:
            return random.choice(cls.PERSONA_SPECIFIC[persona])
        
        # Session-length based (30% chance if applicable)
        if exchange_count > 0 and random.random() < 0.30:
            category = cls.get_session_length_category(exchange_count)
            return random.choice(cls.SESSION_BASED[category])
        
        # Default: Time-based
        time_period = cls.get_time_period()
        return random.choice(cls.TIME_BASED[time_period])


class GreetingGenerator:
    """Generate contextual greeting messages (already partially in config.py)."""
    
    # Additional context-aware greetings
    RETURN_GREETINGS = {
        "same_day": [
            "Back already? What's up?",
            "Hey again. Need something else?",
            "Round two, huh?",
        ],
        "next_day": [
            "Welcome back. How'd yesterday go?",
            "Hey. New day, new questions?",
            "Morning. What brings you back?",
        ],
        "long_absence": [  # 7+ days
            "Long time no see. What's new?",
            "Been a while. Everything alright?",
            "Welcome back, stranger.",
        ]
    }
    
    @classmethod
    def generate(cls, last_session_date: Optional[str] = None) -> Optional[str]:
        """
        Generate contextual greeting (returns None to use default).
        
        Args:
            last_session_date: ISO timestamp of last session
        
        Returns:
            Greeting message or None
        """
        if not last_session_date:
            return None
        
        try:
            last_date = datetime.fromisoformat(last_session_date)
            now = datetime.now()
            delta = now - last_date
            
            # Same day (within 12 hours)
            if delta.total_seconds() < 43200 and random.random() < 0.3:
                return random.choice(cls.RETURN_GREETINGS["same_day"])
            
            # Next day
            elif delta.days == 1 and random.random() < 0.2:
                return random.choice(cls.RETURN_GREETINGS["next_day"])
            
            # Long absence
            elif delta.days >= 7 and random.random() < 0.4:
                return random.choice(cls.RETURN_GREETINGS["long_absence"])
        
        except:
            pass
        
        return None
