"""
Pacify & Defy - CLI Interface v-1.0.0
Clean, user-friendly terminal interface with enhanced UX
"""

import sys
import os
import random
from typing import Optional, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from pyfiglet import Figlet

# Clipboard support
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

# Core imports
try:
    from core.memory import MemoryManager
    from core.farewell import FarewellGenerator, GreetingGenerator
    from core.config import (
        PACIFY_PERSONAS,
        DEFY_PERSONAS,
        DEFY_WARNING,
        DEFAULT_MODE,
        DEFAULT_PACIFY_PERSONA,
        DEFAULT_DEFY_PERSONA,
        AVAILABLE_MOODS,
        DEFAULT_MOOD,
        MOOD_ENABLED_PERSONAS,
        PACIFY_MODEL,
        DEFY_MODEL,
        FONTS,
        GREETINGS,
        MODE_SWITCH_THRESHOLD_LOW,
        MODE_SWITCH_THRESHOLD_HIGH,
        GREETING_RANDOMNESS,
        COMMAND_HISTORY_SIZE,
        )
    
    # Brain import with factory
    try:
        from core.brain import create_brain
        BRAIN_AVAILABLE = True
    except ImportError:
        BRAIN_AVAILABLE = False
        print("Warning: brain.py not found - running in demo mode")
        
except ImportError as e:
    print(f"Error: Core modules not found: {e}")
    sys.exit(1)


console = Console()


class CLI:
    """
    Terminal interface for Pacify & Defy.
    Clean, user-friendly with enhanced error handling and auto-recommendations.
    """
    
    def __init__(self):
        """Initialize CLI with session persistence."""
        self.memory = MemoryManager()
        self.running = True
        self.session_id = self._generate_session_id()
        self.user_id = 1
        
        # Display settings
        self.show_metadata = True
        self.show_timestamps = False
        
        # Response tracking for copy command
        self.response_history = []
        
        # Auto-switch tracking (avoid nagging)
        self.declined_switches = set()
        
        # Load last session state or use defaults
        session_state = self.memory.load_session_state(self.user_id)
        
        if session_state:
            self.mode = session_state.get("last_mode", DEFAULT_MODE)
            self.persona = session_state.get("last_persona", self._get_default_persona(self.mode))
            self.current_mood = session_state.get("last_mood", DEFAULT_MOOD)
            self.mode_switches = session_state.get("mode_switches", 0)
        else:
            self.mode = DEFAULT_MODE
            self.persona = DEFAULT_PACIFY_PERSONA
            self.current_mood = DEFAULT_MOOD
            self.mode_switches = 0
        
        # Command history for terminal shortcuts
        self.command_history = []
        self.history_index = -1
        
        # Defy mode confirmation tracking
        self.defy_confirmed = False
        
        # Session tracking for farewell
        self.exchange_count = 0
        
# Initialize brain if available
        if BRAIN_AVAILABLE:
            self.brain = create_brain(self.mode, self.persona, self.user_id)
    # Set mood for Pacificia
            if self.persona == "pacificia" and hasattr(self.brain, 'set_mood'):
                try:
                    self.brain.set_mood(self.current_mood)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not set mood: {e}[/yellow]")
        else:
            self.brain = None
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _get_default_persona(self, mode: str) -> str:
        """Get default persona for mode."""
        return DEFAULT_PACIFY_PERSONA if mode == "pacify" else DEFAULT_DEFY_PERSONA
    
    # ========================================================================
    # ASCII ART & GREETINGS
    # ========================================================================
    
    def _get_ascii_art(self, text: str, font: str) -> str:
        """Generate ASCII art using pyfiglet."""
        try:
            fig = Figlet(font=font)
            return fig.renderText(text)
        except:
            return text
    
    def _get_contextual_greeting(self) -> str:
        """Get contextual greeting based on session state."""
        use_switch_greeting = False
        
        if self.mode_switches >= MODE_SWITCH_THRESHOLD_HIGH:
            use_switch_greeting = random.random() < 0.6
        elif self.mode_switches >= MODE_SWITCH_THRESHOLD_LOW:
            use_switch_greeting = random.random() < 0.4
        else:
            use_switch_greeting = random.random() < GREETING_RANDOMNESS
        
        greeting_type = "mode_switch" if use_switch_greeting else "standard"
        greeting_list = GREETINGS.get(self.mode, {}).get(greeting_type, ["Welcome back."])
        
        return random.choice(greeting_list)
    
    def _show_mode_banner(self):
        """Display mode-level ASCII art banner."""
        mode_name = self.mode.upper()
        font = FONTS.get(f"{self.mode}_mode", "slant")
        
        ascii_art = self._get_ascii_art(mode_name, font)
        color = "cyan" if self.mode == "pacify" else "red"
        
        console.print(ascii_art, style=f"bold {color}")
    
    def _show_persona_banner(self):
        """Display persona-level ASCII art."""
        persona_name = self.persona.capitalize()
        font = FONTS.get(self.persona, "small")
        
        ascii_art = self._get_ascii_art(persona_name, font)
        color = "cyan" if self.mode == "pacify" else "red"
        
        console.print(ascii_art, style=color)
    
    def show_banner(self):
        """Display complete startup banner with contextual greeting."""
        console.clear()
        
        # Mode banner
        self._show_mode_banner()
        
        # Persona name
        self._show_persona_banner()
        
        # Contextual greeting with return visitor detection
        last_session = self.memory.get_preference(self.user_id, "session_last_session_timestamp")
        custom_greeting = GreetingGenerator.generate(last_session)
        
        if custom_greeting:
            greeting = custom_greeting
        else:
            greeting = self._get_contextual_greeting()
        console.print(f"\n{greeting}\n", style="dim italic")
        
        # Status line
        mode_color = "cyan" if self.mode == "pacify" else "red"
        status = (
            f"Mode: [{mode_color}]{self.mode.upper()}[/{mode_color}] | "
            f"Persona: [{mode_color}]{self.persona}[/{mode_color}]"
        )
        
        if self.persona in MOOD_ENABLED_PERSONAS:
            status += f" | Mood: [yellow]{self.current_mood}[/yellow]"
        
        console.print(status, style="dim")
        
        # Check for recent errors
        recent_errors = self.memory.get_recent_errors(limit=1)
        if recent_errors and random.random() < 0.3:
            console.print("[dim]I see we had some technical difficulties last time...[/dim]")
        
        if not BRAIN_AVAILABLE:
            console.print("[yellow]Warning: brain.py not loaded - demo mode[/yellow]", style="dim")
        
        if not CLIPBOARD_AVAILABLE:
            console.print("[dim]Note: pyperclip not installed - /copy command unavailable[/dim]")
        
        console.print("Type [yellow]/help[/yellow] for commands or start chatting\n", style="dim")
    
    # ========================================================================
    # TERMINAL SHORTCUTS
    # ========================================================================
    
    def _add_to_history(self, command: str):
        """Add command to history."""
        if command and command != self.command_history[-1:]:
            self.command_history.append(command)
            if len(self.command_history) > COMMAND_HISTORY_SIZE:
                self.command_history.pop(0)
        self.history_index = len(self.command_history)
    
    def _handle_shortcut(self, key: str) -> Optional[str]:
        """Handle terminal shortcuts."""
        if key == "ctrl_l":
            console.clear()
            self.show_banner()
            return None
        
        if key == "!!":
            if self.command_history:
                last_cmd = self.command_history[-1]
                console.print(f"[dim]Repeating: {last_cmd}[/dim]")
                return last_cmd
            return None
        
        if key == "arrow_up":
            if self.history_index > 0:
                self.history_index -= 1
                return self.command_history[self.history_index]
            return None
        
        if key == "arrow_down":
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                return self.command_history[self.history_index]
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                return ""
            return None
        
        return None
    
    # ========================================================================
    # RESPONSE DISPLAY WITH CONTEXT INDICATORS
    # ========================================================================
    
    def display_response(self, response: str, metadata: dict):
        """
        Display AI response with metadata and context indicators.
        
        Args:
            response: AI response text
            metadata: Response metadata
        """
        border_color = "cyan" if self.mode == "pacify" else "red"
        
        # Track response for copy command
        self.response_history.append(response)
        if len(self.response_history) > 10:
            self.response_history.pop(0)
        
        panel = Panel(
            response,
            title=f"[bold]{self.persona}[/bold]",
            border_style=border_color,
            padding=(1, 2)
        )
        console.print(panel)
        
        # Metadata footer (if enabled)
        if self.show_metadata:
            time_str = f"{metadata.get('time', 0):.2f}s"
            word_count = metadata.get('word_count', 0)
            mood = metadata.get('mood', self.current_mood)
            pattern = metadata.get('pattern', 'normal')
            
            # Build metadata line
            meta_parts = [f"Time: {time_str}", f"Words: {word_count}"]
            
            # Context indicator
            if metadata.get('using_context'):
                meta_parts.append("Using context")
            
            # Topic tracking
            if metadata.get('conversation_topic'):
                topic = metadata['conversation_topic']
                meta_parts.append(f"Topic: {topic}")
            
            # Pattern indicator (if not normal)
            if pattern not in ["normal", "follow_up"]:
                meta_parts.append(f"Pattern: {pattern}")
            
            if self.persona in MOOD_ENABLED_PERSONAS:
                meta_parts.append(f"Mood: {mood}")
            
            if self.show_timestamps:
                timestamp = datetime.now().strftime("%H:%M:%S")
                meta_parts.append(f"Time: {timestamp}")
            
            # Word count warning
            if metadata.get('word_warning'):
                meta_parts.append(f"Note: {metadata['word_warning']}")
            
            console.print(f"[dim]{' | '.join(meta_parts)}[/dim]\n")
        else:
            console.print()
        
        # Auto-switch recommendation
        auto_switch = metadata.get('auto_switch')
        if auto_switch:
            switch_key = f"{auto_switch['type']}:{auto_switch['recommended']}"
            
            # Don't nag if user declined before
            if switch_key not in self.declined_switches:
                self._show_auto_switch_recommendation(auto_switch)
        
        # Preference learning notification
        if metadata.get('learning') == 'major':
            learned = self.memory.get_learned_preference(self.user_id, "response_length")
            if learned:
                console.print(f"[dim]Noticed you prefer {learned} responses. Adjusting...[/dim]\n")
    
    def _show_auto_switch_recommendation(self, auto_switch: dict):
        """
        Show auto-switch recommendation with prompt.
        
        Args:
            auto_switch: Auto-switch metadata
        """
        switch_type = auto_switch['type']
        current = auto_switch['current']
        recommended = auto_switch['recommended']
        reason = auto_switch['reason']
        
        message = f"\n[yellow]Suggestion: {reason}. Switch to {recommended}? (y/N)[/yellow]"
        console.print(message)
        
        try:
            choice = Prompt.ask("", default="n").strip().lower()
            
            if choice in ["y", "yes"]:
                if switch_type == "persona":
                    self.switch_persona(recommended)
                elif switch_type == "mode":
                    self.switch_mode(recommended)
            else:
                # Track decline to avoid nagging
                switch_key = f"{switch_type}:{recommended}"
                self.declined_switches.add(switch_key)
                console.print("[dim]Okay, staying with current setup.[/dim]\n")
        except KeyboardInterrupt:
            console.print("\n")
    
    # ========================================================================
    # ERROR HANDLING
    # ========================================================================
    
    def _handle_error(self, error_type: str, error: Exception, context: str = ""):
        """
        Handle errors with user-friendly messages.
        
        Args:
            error_type: Type of error
            error: Exception object
            context: Additional context
        """
        error_messages = {
            "api_error": "I'm having trouble connecting to the AI service right now.",
            "network": "Network connection issue detected.",
            "auth_failed": "Authentication problem - check your API key in .env file.",
            "rate_limit": "Rate limit reached - please wait a moment.",
            "unknown": "Something unexpected happened.",
        }
        
        base_message = error_messages.get(error_type, "An error occurred.")
        
        console.print(f"\n[red]Error: {base_message}[/red]")
        
        if context:
            console.print(f"[dim]{context}[/dim]")
        
        # Offer contextual help
        if error_type == "auth_failed":
            console.print("[dim]Hint: Make sure GROQ_API_KEY is set in your .env file[/dim]\n")
        elif error_type == "network":
            console.print("[dim]Hint: Check your internet connection and try again[/dim]\n")
        elif error_type == "rate_limit":
            console.print("[dim]Hint: Wait 60 seconds or check your API quota[/dim]\n")
        else:
            console.print(f"[dim]Technical details: {str(error)}[/dim]\n")
        
        # Track error
        self.memory.track_error(error_type, str(error))
    
    # ========================================================================
    # STATISTICS & HISTORY
    # ========================================================================
    
    def show_stats(self):
        """Display comprehensive conversation statistics."""
        stats = self.memory.get_stats(self.user_id)
        
        # Main stats table
        table = Table(title="Statistics", show_header=True, header_style="bold yellow")
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="green", width=20)
        
        table.add_row("Total Conversations", str(stats['total']))
        table.add_row("Pacify Mode", str(stats['pacify_count']))
        table.add_row("Defy Mode", str(stats['defy_count']))
        table.add_row("Current Mode", self.mode)
        table.add_row("Current Persona", self.persona)
        
        if self.persona in MOOD_ENABLED_PERSONAS:
            table.add_row("Current Mood", self.current_mood)
        
        table.add_row("Mode Switches (Session)", str(self.mode_switches))
        
        if stats['avg_response_time'] > 0:
            table.add_row("Avg Response Time", f"{stats['avg_response_time']}s")
        if stats['avg_word_count'] > 0:
            table.add_row("Avg Word Count", f"{stats['avg_word_count']:.0f}")
        
        console.print(table)
        
        # Persona usage breakdown
        if stats['persona_usage']:
            persona_table = Table(title="Persona Usage", show_header=True, header_style="bold yellow")
            persona_table.add_column("Persona", style="cyan")
            persona_table.add_column("Count", style="green", justify="right")
            
            for persona, count in sorted(stats['persona_usage'].items(), key=lambda x: x[1], reverse=True):
                persona_table.add_row(persona, str(count))
            
            console.print(persona_table)
        
        console.print()
    
    def show_history(self, limit: int = 5):
        """Display recent conversation history."""
        history = self.memory.get_conversation_history(self.user_id, limit)
        
        if not history:
            console.print("[yellow]No conversation history yet.[/yellow]\n")
            return
        
        console.print(f"[bold cyan]Recent Conversations (Last {min(limit, len(history))})[/bold cyan]\n")
        
        for i, conv in enumerate(reversed(history), 1):
            mode_color = "cyan" if conv['mode'] == "pacify" else "red"
            timestamp = conv['timestamp'].split('T')[1][:5] if 'T' in conv['timestamp'] else conv['timestamp']
            
            console.print(f"[dim]{i}. [{mode_color}]{conv['mode']}[/{mode_color}] - {conv['persona']} - {timestamp}[/dim]")
            console.print(f"   [yellow]You:[/yellow] {conv['user_input'][:70]}{'...' if len(conv['user_input']) > 70 else ''}")
            console.print(f"   [green]{conv['persona']}:[/green] {conv['ai_response'][:70]}{'...' if len(conv['ai_response']) > 70 else ''}")
            console.print()
    
    def show_opinions(self):
        """Display tracked opinions."""
        opinions = self.memory.get_all_opinions(self.user_id)
        
        if not opinions:
            console.print("[yellow]No opinions tracked yet.[/yellow]\n")
            return
        
        table = Table(title="Tracked Opinions", show_header=True, header_style="bold yellow")
        table.add_column("Topic", style="cyan", width=25)
        table.add_column("Stance", style="green", width=35)
        table.add_column("Confidence", style="yellow", justify="right")
        
        for op in opinions:
            confidence_pct = f"{op['confidence']*100:.0f}%"
            table.add_row(op['topic'], op['stance'][:35], confidence_pct)
        
        console.print(table)
        console.print()
    
    # ========================================================================
    # COPY COMMAND
    # ========================================================================
    
    def copy_to_clipboard(self, index: Optional[int] = None):
        """
        Copy AI response to clipboard.
        
        Args:
            index: Response index (None = last response)
        """
        if not CLIPBOARD_AVAILABLE:
            console.print("[yellow]Copy command unavailable - install pyperclip:[/yellow]")
            console.print("[dim]pip install pyperclip[/dim]\n")
            return
        
        if not self.response_history:
            console.print("[yellow]No responses to copy yet.[/yellow]\n")
            return
        
        try:
            if index is None:
                # Copy last response
                text_to_copy = self.response_history[-1]
                console.print("[green]Copied last response to clipboard.[/green]\n")
            else:
                # Copy specific response
                if 1 <= index <= len(self.response_history):
                    text_to_copy = self.response_history[-index]
                    console.print(f"[green]Copied response #{index} to clipboard.[/green]\n")
                else:
                    console.print(f"[yellow]Invalid index. Available: 1-{len(self.response_history)}[/yellow]\n")
                    return
            
            pyperclip.copy(text_to_copy)
        
        except Exception as e:
            console.print(f"[red]Clipboard error: {str(e)}[/red]\n")
    
    # ========================================================================
    # MODE & PERSONA SWITCHING
    # ========================================================================
    
    def switch_mode(self, new_mode: str):
        """Switch between Pacify and Defy modes."""
        new_mode = new_mode.lower()
        
        if new_mode not in ["pacify", "defy"]:
            console.print("[red]Invalid mode. Use 'pacify' or 'defy'[/red]\n")
            return
        
        if new_mode == self.mode:
            console.print(f"[yellow]Already in {new_mode} mode[/yellow]\n")
            return
        
        # Warn for Defy mode
        if new_mode == "defy" and not self.defy_confirmed:
            console.print(Panel(DEFY_WARNING, border_style="red", title="WARNING"))
            if not Confirm.ask("Continue?", default=False):
                console.print("[yellow]Mode switch cancelled[/yellow]\n")
                return
            self.defy_confirmed = True
        
        # Track mode switch
        self.mode_switches += 1
        
        # Switch mode and persona
        old_mode = self.mode
        self.mode = new_mode
        self.persona = self._get_default_persona(new_mode)
        
        # Clear declined switches on mode change
        self.declined_switches.clear()
        
        # Reload brain
        if BRAIN_AVAILABLE:
            self.brain = create_brain(self.mode, self.persona, self.user_id)
            if self.persona == "pacificia" and hasattr(self.brain, 'set_mood'):
                self.brain.set_mood(self.current_mood)
        
        # Update preferences
        self.memory.set_preference(self.user_id, "active_mode", self.mode)
        self.memory.set_preference(self.user_id, "active_persona", self.persona)
        
        # Save session state
        self._save_session_state()
        
        # Show new banner
        console.clear()
        self.show_banner()
        
        mode_color = "cyan" if new_mode == "pacify" else "red"
        console.print(
            f"[{mode_color}]Switched from {old_mode} to {new_mode.upper()} mode with persona '{self.persona}'[/{mode_color}]\n"
        )
    
    def switch_persona(self, persona_name: str):
        """Switch to different persona within current mode."""
        persona_name = persona_name.lower()
        
        valid_personas = PACIFY_PERSONAS if self.mode == "pacify" else DEFY_PERSONAS
        
        if persona_name not in valid_personas:
            console.print(
                f"[red]Invalid persona. Available for {self.mode}: {', '.join(valid_personas)}[/red]\n"
            )
            return
        
        if persona_name == self.persona:
            console.print(f"[yellow]Already using {persona_name} persona[/yellow]\n")
            return
        
        self.persona = persona_name
        
        # Clear declined switches on persona change
        self.declined_switches.clear()
        
        # Reload brain
        if BRAIN_AVAILABLE:
            self.brain = create_brain(self.mode, self.persona, self.user_id)
            if self.persona == "pacificia" and hasattr(self.brain, 'set_mood'):
                self.brain.set_mood(self.current_mood)
        
        self.memory.set_preference(self.user_id, "active_persona", self.persona)
        self._save_session_state()
        
        # Show new persona banner
        console.print()
        self._show_persona_banner()
        console.print(f"[green]Switched to persona '{self.persona}'[/green]\n")
    
    def set_mood(self, mood: str):
        """Set conversation mood (Pacificia only)."""
        mood = mood.lower()
        
        if self.persona not in MOOD_ENABLED_PERSONAS:
            console.print(f"[yellow]Moods only work with Pacificia. Current persona: {self.persona}[/yellow]\n")
            return
        
        if mood not in AVAILABLE_MOODS:
            console.print(f"[red]Invalid mood. Available: {', '.join(AVAILABLE_MOODS)}[/red]\n")
            return
        
        self.current_mood = mood
        
        if BRAIN_AVAILABLE and hasattr(self.brain, 'set_mood'):
            self.brain.set_mood(mood)
        
        self._save_session_state()
        console.print(f"[green]Mood set to '{mood}'[/green]\n")
    
    # ========================================================================
    # SESSION STATE
    # ========================================================================
    
    def _save_session_state(self):
        """Save current session state."""
        state = {
            "last_mode": self.mode,
            "last_persona": self.persona,
            "last_mood": self.current_mood,
            "mode_switches": self.mode_switches,
        }
        self.memory.save_session_state(self.user_id, state)
    
    def show_status(self):
        """Display current configuration."""
        mode_color = "cyan" if self.mode == "pacify" else "red"
        
        status = f"""
[bold cyan]Current Configuration:[/bold cyan]

Mode:           [{mode_color}]{self.mode.upper()}[/{mode_color}]
Persona:        [{mode_color}]{self.persona}[/{mode_color}]"""
        
        if self.persona in MOOD_ENABLED_PERSONAS:
            status += f"\nMood:           [yellow]{self.current_mood}[/yellow]"
        
        status += f"""
Session ID:     [dim]{self.session_id}[/dim]
Mode Switches:  [dim]{self.mode_switches}[/dim]
Metadata:       [green]{'ON' if self.show_metadata else 'OFF'}[/green]
Timestamps:     [green]{'ON' if self.show_timestamps else 'OFF'}[/green]
Brain Status:   [{'green' if BRAIN_AVAILABLE else 'yellow'}]{'Loaded' if BRAIN_AVAILABLE else 'Not Available'}[/{'green' if BRAIN_AVAILABLE else 'yellow'}]
Clipboard:      [{'green' if CLIPBOARD_AVAILABLE else 'yellow'}]{'Available' if CLIPBOARD_AVAILABLE else 'Not Available'}[/{'green' if CLIPBOARD_AVAILABLE else 'yellow'}]

[bold cyan]Models:[/bold cyan]
Pacify Model:   [cyan]{PACIFY_MODEL}[/cyan]
Defy Model:     [red]{DEFY_MODEL}[/red]
        """
        
        console.print(Panel(status, border_style=mode_color, padding=(1, 2)))
        console.print()
    
    def clear_session(self):
        """Clear current session memory."""
        if not Confirm.ask("Clear all conversation history?", default=False):
            console.print("[yellow]Cancelled[/yellow]\n")
            return
        
        self.memory.clear_session(self.user_id, self.session_id)
        self.response_history.clear()
        console.print("[green]Session memory cleared[/green]\n")
    
    # ========================================================================
    # HELP MENU (CLEAN & SCANNABLE)
    # ========================================================================
    
    def show_help(self):
        """Display clean, scannable help menu."""
        help_text = """
[bold cyan]PACIFY & DEFY - COMMAND REFERENCE[/bold cyan]

[bold yellow]CORE COMMANDS[/bold yellow]
  /help                    Show this help menu
  /status                  Show current configuration
  /stats                   Conversation statistics
  /clear                   Clear session memory
  
[bold yellow]MODE & PERSONALITY[/bold yellow]
  /setmode <pacify|defy>   Switch AI mode
  /persona <name>          Change persona (pacificia, sage, void, rebel)
  /mood <mood>             Set mood (Pacificia only)

[bold yellow]HISTORY & DATA[/bold yellow]
  /history [N]             Show last N conversations (default: 5)
  /search <keyword>        Search conversation history
  /copy [N]                Copy last (or Nth) response to clipboard
  /export [file.ext]       Save conversation (txt, json, md)
  /opinions                View tracked opinions

[bold yellow]CONFIGURATION[/bold yellow]
  /settings                Show all current settings
  /set <option> <value>    Adjust settings (see /settings for options)

[bold yellow]TERMINAL SHORTCUTS[/bold yellow]
  Ctrl+L                   Clear screen, redisplay banner
  !!                       Repeat last command
  exit, quit               End session

[dim]Tip: Type /settings to see all configurable options[/dim]
[dim]Tip: The AI suggests better persona/mode for your task[/dim]
"""
        console.print(help_text)
        console.print()
    
    # ========================================================================
    # SETTINGS SYSTEM
    # ========================================================================
    
    def show_settings(self):
        """Display all current settings."""
        mode_color = "cyan" if self.mode == "pacify" else "red"
        
        # Get current brain settings
        length_pref = self.brain.length_preference if BRAIN_AVAILABLE else "normal"
        custom_temp = self.brain.custom_temperature if BRAIN_AVAILABLE else None
        context_pref = self.memory.get_preference(self.user_id, "context_limit") or "3"
        autosave = self.memory.get_preference(self.user_id, "autosave") or "off"
        
        settings_text = f"""
[bold cyan]Current Settings:[/bold cyan]

[bold yellow]Response Control:[/bold yellow]
  Length:       [{mode_color}]{length_pref}[/{mode_color}]
  Temperature:  [{mode_color}]{custom_temp if custom_temp else 'default'}[/{mode_color}]
  Context:      [{mode_color}]{context_pref} exchanges[/{mode_color}]

[bold yellow]Display:[/bold yellow]
  Metadata:     [{'green' if self.show_metadata else 'red'}]{'ON' if self.show_metadata else 'OFF'}[/{'green' if self.show_metadata else 'red'}]
  Timestamps:   [{'green' if self.show_timestamps else 'red'}]{'ON' if self.show_timestamps else 'OFF'}[/{'green' if self.show_timestamps else 'red'}]

[bold yellow]Features:[/bold yellow]
  Auto-save:    [{'green' if autosave == 'on' else 'red'}]{autosave.upper()}[/{'green' if autosave == 'on' else 'red'}]

[bold yellow]Available Options:[/bold yellow]
  /set length <quick|normal|detailed>
  /set temperature <0.1-1.0>
  /set context <1-10>
  /set metadata <on|off>
  /set timestamps <on|off>
  /set autosave <on|off>

[dim]Example: /set length detailed[/dim]
"""
        console.print(Panel(settings_text, border_style=mode_color, padding=(1, 2)))
        console.print()
    
    def handle_set_command(self, args: List[str]):
        """
        Handle /set commands for adjusting settings.
        
        Args:
            args: Command arguments [option, value]
        """
        if not args:
            self.show_settings()
            return
        
        if args[0] == "show":
            self.show_settings()
            return
        
        if len(args) < 2:
            console.print("[red]Usage: /set <option> <value>[/red]")
            console.print("[dim]Type /settings to see all options[/dim]\n")
            return
        
        option = args[0].lower()
        value = args[1].lower()
        
        # Length setting
        if option == "length":
            if value not in ["quick", "normal", "detailed"]:
                console.print("[red]Invalid length. Use: quick, normal, or detailed[/red]\n")
                return
            
            if BRAIN_AVAILABLE:
                self.brain.set_length_preference(value)
                console.print(f"[green]Response length set to '{value}'[/green]\n")
            else:
                console.print("[yellow]Brain not available[/yellow]\n")
        
        # Temperature setting
        elif option == "temperature":
            try:
                temp = float(value)
                if temp < 0.1 or temp > 1.0:
                    console.print("[red]Temperature must be between 0.1 and 1.0[/red]\n")
                    return
                
                if BRAIN_AVAILABLE:
                    self.brain.set_temperature(temp)
                    console.print(f"[green]Temperature set to {temp}[/green]\n")
                else:
                    console.print("[yellow]Brain not available[/yellow]\n")
            except ValueError:
                console.print("[red]Temperature must be a number (e.g., 0.7)[/red]\n")
        
        # Context setting
        elif option == "context":
            try:
                ctx = int(value)
                if ctx < 1 or ctx > 10:
                    console.print("[red]Context must be between 1 and 10[/red]\n")
                    return
                
                self.memory.set_preference(self.user_id, "context_limit", str(ctx))
                console.print(f"[green]Context window set to {ctx} exchanges[/green]\n")
            except ValueError:
                console.print("[red]Context must be a number (1-10)[/red]\n")
        
        # Metadata toggle
        elif option == "metadata":
            if value in ["on", "off"]:
                self.show_metadata = (value == "on")
                console.print(f"[green]Metadata display {value.upper()}[/green]\n")
            else:
                console.print("[red]Use 'on' or 'off'[/red]\n")
        
        # Timestamps toggle
        elif option == "timestamps":
            if value in ["on", "off"]:
                self.show_timestamps = (value == "on")
                console.print(f"[green]Timestamps {value.upper()}[/green]\n")
            else:
                console.print("[red]Use 'on' or 'off'[/red]\n")
        
        # Auto-save toggle
        elif option == "autosave":
            if value in ["on", "off"]:
                self.memory.set_preference(self.user_id, "autosave", value)
                console.print(f"[green]Auto-save {value.upper()}[/green]\n")
            else:
                console.print("[red]Use 'on' or 'off'[/red]\n")
        
        else:
            console.print(f"[red]Unknown setting: {option}[/red]")
            console.print("[dim]Type /settings to see available options[/dim]\n")
    
    # ========================================================================
    # EXPORT SYSTEM
    # ========================================================================
    
    def export_conversation(self, filename: str = None):
        """
        Export conversation history to file.
        
        Args:
            filename: Custom filename (with extension) or None for auto-generated
        """
        from pathlib import Path
        from core.config import EXPORTS_DIR
        
        history = self.memory.get_conversation_history(self.user_id, limit=100)
        
        if not history:
            console.print("[yellow]No conversations to export[/yellow]\n")
            return
        
        # Determine filename and format
        if filename:
            export_path = EXPORTS_DIR / filename
            
            if filename.endswith('.json'):
                format_type = "json"
            elif filename.endswith('.md'):
                format_type = "md"
            else:
                format_type = "txt"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_{self.mode}_{timestamp}.txt"
            export_path = EXPORTS_DIR / filename
            format_type = "txt"
        
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                if format_type == "json":
                    import json
                    export_data = {
                        "mode": self.mode,
                        "persona": self.persona,
                        "export_date": datetime.now().isoformat(),
                        "conversations": [
                            {
                                "timestamp": conv['timestamp'],
                                "user": conv['user_input'],
                                "ai": conv['ai_response'],
                                "mode": conv['mode'],
                                "persona": conv['persona'],
                                "mood": conv.get('mood'),
                                "word_count": conv.get('word_count'),
                            }
                            for conv in reversed(history)
                        ]
                    }
                    json.dump(export_data, f, indent=2)
                
                elif format_type == "md":
                    f.write(f"# Pacify & Defy - Conversation Export\n\n")
                    f.write(f"**Mode:** {self.mode} | **Persona:** {self.persona}\n\n")
                    f.write("---\n\n")
                    
                    for i, conv in enumerate(reversed(history), 1):
                        f.write(f"## [{i}] {conv['timestamp']}\n\n")
                        f.write(f"**Mode:** {conv['mode']} | **Persona:** {conv['persona']}\n\n")
                        f.write(f"**You:** {conv['user_input']}\n\n")
                        f.write(f"**{conv['persona']}:** {conv['ai_response']}\n\n")
                        f.write("---\n\n")
                
                else:
                    f.write(f"Pacify & Defy - Conversation Export\n")
                    f.write(f"Mode: {self.mode} | Persona: {self.persona}\n")
                    f.write("=" * 60 + "\n\n")
                    
                    for i, conv in enumerate(reversed(history), 1):
                        f.write(f"[{i}] {conv['timestamp']}\n")
                        f.write(f"Mode: {conv['mode']} | Persona: {conv['persona']}\n")
                        f.write(f"You: {conv['user_input']}\n")
                        f.write(f"{conv['persona']}: {conv['ai_response']}\n")
                        f.write("-" * 60 + "\n\n")
            
            console.print(f"[green]Exported {len(history)} conversations to {export_path.name}[/green]\n")
        
        except Exception as e:
            console.print(f"[red]Export failed: {e}[/red]\n")
    
    # ========================================================================
    # SEARCH SYSTEM
    # ========================================================================
    
    def search_history(self, keyword: str):
        """
        Search conversation history for keyword.
        
        Args:
            keyword: Search term
        """
        history = self.memory.get_conversation_history(self.user_id, limit=100)
        
        if not history:
            console.print("[yellow]No conversation history to search.[/yellow]\n")
            return
        
        keyword_lower = keyword.lower()
        matches = [
            conv for conv in history
            if keyword_lower in conv['user_input'].lower() 
            or keyword_lower in conv['ai_response'].lower()
        ]
        
        if not matches:
            console.print(f"[yellow]No conversations found containing '{keyword}'[/yellow]\n")
            return
        
        console.print(f"[bold cyan]Found {len(matches)} conversations matching '{keyword}'[/bold cyan]\n")
        
        for i, conv in enumerate(matches[:10], 1):
            mode_color = "cyan" if conv['mode'] == "pacify" else "red"
            console.print(f"[dim]{i}. [{mode_color}]{conv['mode']}[/{mode_color}] - {conv['persona']}[/dim]")
            console.print(f"   [yellow]You:[/yellow] {conv['user_input'][:70]}...")
            console.print(f"   [green]{conv['persona']}:[/green] {conv['ai_response'][:70]}...")
            console.print()
        
        if len(matches) > 10:
            console.print(f"[dim]... and {len(matches) - 10} more results[/dim]\n")
    
    # ========================================================================
    # COMMAND HANDLER
    # ========================================================================
    
    def handle_command(self, user_input: str) -> bool:
        """
        Process user commands.
        
        Args:
            user_input: User input string
        
        Returns:
            True if command was handled, False if regular message
        """
        if not user_input.startswith("/"):
            return False
        
        # Parse command and arguments
        parts = user_input[1:].split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else None
        
        # Core commands
        if command == "help":
            self.show_help()
        
        elif command == "settings":
            if arg:
                self.handle_set_command(arg.split())
            else:
                self.show_settings()
        
        elif command == "set":
            if arg:
                self.handle_set_command(arg.split())
            else:
                console.print("[red]Usage: /set <option> <value>[/red]\n")
        
        elif command == "status":
            self.show_status()
        
        elif command == "stats":
            self.show_stats()
        
        elif command == "clear":
            self.clear_session()
        
        # Mode & Persona
        elif command == "setmode":
            if not arg:
                console.print("[red]Usage: /setmode <pacify|defy>[/red]\n")
            else:
                self.switch_mode(arg)
        
        elif command == "persona":
            if not arg:
                console.print("[red]Usage: /persona <name>[/red]\n")
            else:
                self.switch_persona(arg)
        
        elif command == "mood":
            if not arg:
                console.print(f"[cyan]Available moods: {', '.join(AVAILABLE_MOODS)}[/cyan]\n")
            else:
                self.set_mood(arg)
        
        # History & Data
        elif command == "history":
            limit = int(arg) if arg and arg.isdigit() else 5
            self.show_history(limit)
        
        elif command == "search":
            if not arg:
                console.print("[red]Usage: /search <keyword>[/red]\n")
            else:
                self.search_history(arg)
        
        elif command == "copy":
            index = int(arg) if arg and arg.isdigit() else None
            self.copy_to_clipboard(index)
        
        elif command == "export":
            self.export_conversation(arg)
        
        elif command == "opinions":
            self.show_opinions()
        
        else:
            console.print(f"[red]Unknown command: /{command}[/red]")
            console.print("[dim]Type /help for available commands[/dim]\n")
        
        return True
    
    # ========================================================================
    # MAIN LOOP
    # ========================================================================
    
    def main_loop(self):
        """Main conversation loop with enhanced error handling."""
        self.show_banner()
        
        # Check for autosave on startup
        autosave = self.memory.get_preference(self.user_id, "autosave")
        
        while self.running:
            try:
                # Get user input
                user_input = Prompt.ask("[bold yellow]You[/bold yellow]").strip()
                
                if not user_input:
                    continue
                
                # Add to history
                self._add_to_history(user_input)
                
                # Check for exit commands
                if user_input.lower() in ["exit", "quit"]:
                    # Auto-save if enabled
                    if autosave == "on":
                        console.print("[dim]Auto-saving conversation...[/dim]")
                        self.export_conversation()
                    
                    self._save_session_state()
                    
                    # Generate personalized farewell
                    farewell = FarewellGenerator.generate(
                        persona=self.persona,
                        exchange_count=self.exchange_count,
                        mode_switches=self.mode_switches,
                        had_errors=len(self.memory.get_recent_errors()) > 0
                    )
                    
                    mode_color = "cyan" if self.mode == "pacify" else "red"
                    console.print(f"\n[{mode_color}]{farewell}[/{mode_color}]")
                    break
                
                # Handle !! shortcut
                if user_input == "!!":
                    repeat_cmd = self._handle_shortcut("!!")
                    if repeat_cmd:
                        user_input = repeat_cmd
                    else:
                        continue
                
                # Handle commands
                if self.handle_command(user_input):
                    continue
                
                # Check if brain is available
                if not BRAIN_AVAILABLE:
                    console.print("[yellow]Brain module not loaded. Only commands are available.[/yellow]\n")
                    continue
                
                # Get AI response with enhanced status
                with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                    try:
                        result = self.brain.get_response(user_input)
                        response = result["response"]
                        metadata = result["metadata"]
                        
                        # Display response with context indicators
                        self.display_response(response, metadata)
                        self.exchange_count += 1
                        
                    except Exception as e:
                        # Enhanced error handling
                        error_type = "unknown"
                        
                        if "timeout" in str(e).lower():
                            error_type = "api_error"
                        elif "network" in str(e).lower() or "connection" in str(e).lower():
                            error_type = "network"
                        elif "auth" in str(e).lower() or "key" in str(e).lower():
                            error_type = "auth_failed"
                        elif "rate" in str(e).lower() or "limit" in str(e).lower():
                            error_type = "rate_limit"
                        
                        self._handle_error(error_type, e)
                        continue
            
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Use 'exit' or 'quit' to leave[/yellow]\n")
                continue
            
            except Exception as e:
                console.print(f"\n[red]Unexpected error: {str(e)}[/red]\n")
                self.memory.track_error("unexpected", str(e))
                continue


def main():
    """Entry point for CLI."""
    try:
        cli = CLI()
        cli.main_loop()
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
