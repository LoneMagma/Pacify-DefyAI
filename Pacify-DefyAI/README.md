# Pacify & Defy

```
    ____             _ ____         ___     ____       ____       
   / __ \____ ______(_) __/_  __   ( _ )   / __ \___  / __/_  __
  / /_/ / __ `/ ___/ / /_/ / / /  / __ \/\/ / / / _ \/ /_/ / / /
 / ____/ /_/ / /__/ / __/ /_/ /  / /_/  \/ /_/ /  __/ __/ /_/ / 
/_/    \__,_/\___/_/_/  \__, /   \___/\_/_____/\___/_/  \__, /  
                       /____/                          /____/    
```

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Groq API](https://img.shields.io/badge/Powered%20by-Groq-orange)](https://groq.com)

A dual-mode conversational AI system with persistent memory, context awareness, and dynamic personality adaptation.

---

## Overview

Pacify & Defy is a sophisticated CLI-based AI assistant that operates in two distinct modes, each with specialized personas designed for different interaction styles. The system maintains conversation history, learns user preferences, and provides contextually aware responses through the Groq API.

### Modes & Personas

<table>
<tr>
<td width="50%" valign="top">

**Pacify Mode**  
*Collaborative, structured assistance*

- **Pacificia** — Conversational companion with mood-based adaptation
- **Sage** — Task-oriented guide for technical implementation

</td>
<td width="50%" valign="top">

**Defy Mode**  
*Unfiltered, direct responses*

- **Void** — Brutally honest conversational partner
- **Rebel** — Technical specialist without content restrictions

</td>
</tr>
</table>

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Pacify_DefyAI

# Run setup script
chmod +x setup.sh
./setup.sh

# Or install manually
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Add your Groq API key
echo "GROQ_API_KEY=your_api_key_here" > .env
```

Get your API key at [console.groq.com](https://console.groq.com)

### Launch

```bash
python cli.py
```

---

## Core Features

- **Persistent Memory** — SQLite-backed conversation history with user isolation
- **Context Awareness** — Tracks topics, detects follow-ups, maintains conversation flow
- **Preference Learning** — Automatically adapts to user communication styles
- **Mood System** — Dynamic emotional tone adjustment (Pacificia persona)
- **Code Intelligence** — Automatic code block detection and formatting
- **Session Management** — Saves state across sessions with contextual greetings
- **Export Capabilities** — Conversation export in TXT, JSON, and Markdown formats

---

## Usage

### Essential Commands

```bash
/help              # Display command reference
/status            # Show current configuration
/stats             # View conversation statistics
/history [N]       # Show recent conversations
/export [file]     # Save conversation history
```

### Mode & Persona Control

```bash
/setmode pacify    # Switch to Pacify mode
/setmode defy      # Switch to Defy mode
/persona sage      # Change persona
/mood witty        # Set mood (Pacificia only)
```

### Configuration

```bash
/set length quick|normal|detailed    # Response length
/set context 1-10                    # Context window size
/set temperature 0.1-1.0            # Creativity level
/set metadata on|off                # Toggle metadata display
/set autosave on|off                # Auto-save on exit
```

### Data Management

```bash
/search <keyword>  # Search conversation history
/opinions          # View tracked opinions
/copy [N]          # Copy response to clipboard
/clear             # Clear session memory
```

---

## Project Structure

```
Pacify_DefyAI/
├── cli.py                 # Terminal interface
├── core/
│   ├── brain.py          # AI logic and API integration
│   ├── memory.py         # Database and persistence
│   ├── config.py         # Configuration management
│   ├── formatters.py     # Response formatting
│   ├── farewell.py       # Context-aware exit messages
│   └── api_pool.py       # API key management
├── personas/
│   ├── pacify/
│   │   ├── pacificia.json
│   │   └── sage.json
│   └── defy/
│       ├── void.json
│       └── rebel.json
├── data/                 # SQLite database (auto-generated)
├── exports/              # Conversation exports
├── logs/                 # System logs
├── docs/                 # Extended documentation
├── setup.sh              # Linux/macOS setup
└── setup.ps1             # Windows setup
```

---

## Advanced Features

### Mood System

Available for Pacificia persona:

`witty` · `sarcastic` · `philosophical` · `empathetic` · `cheeky` · `poetic` · `inspired` · `melancholic`

```bash
/mood philosophical
```

### Auto-Switching Recommendations

The system intelligently suggests persona/mode switches:

- Code implementation needed → Sage/Rebel
- Deep explanations requested → Pacificia/Void
- Unfiltered content implied → Defy mode
- Collaborative guidance needed → Pacify mode

### Export Formats

<details>
<summary><b>Text Format (.txt)</b></summary>

```
Pacify & Defy - Conversation Export
Mode: pacify | Persona: sage
============================================================

[1] 2024-01-20T10:30:00
Mode: pacify | Persona: sage
You: How do I implement a binary search tree?
sage: [response content]
------------------------------------------------------------
```
</details>

<details>
<summary><b>JSON Format (.json)</b></summary>

```json
{
  "mode": "pacify",
  "persona": "sage",
  "export_date": "2024-01-20T10:30:00",
  "conversations": [
    {
      "timestamp": "2024-01-20T10:30:00",
      "user": "How do I implement a binary search tree?",
      "ai": "[response content]",
      "mood": "focused",
      "word_count": 150
    }
  ]
}
```
</details>

<details>
<summary><b>Markdown Format (.md)</b></summary>

```markdown
# Pacify & Defy - Conversation Export

**Mode:** pacify | **Persona:** sage

---

## [1] 2024-01-20T10:30:00

**Mode:** pacify | **Persona:** sage

**You:** How do I implement a binary search tree?

**sage:** [response content]

---
```
</details>

---

## Technical Details

### Memory System

SQLite-backed persistence with complete user data isolation:

| Table | Purpose |
|-------|---------|
| `conversations` | Full exchange history with metadata |
| `opinions` | Tracked user viewpoints with confidence scoring |
| `preferences` | Manual and learned user preferences |
| `emotional_tracking` | Sentiment analysis over time |
| `session_state` | Persistent configuration across restarts |

### Context Awareness

The conversation tracker maintains:

- Current topic identification
- Follow-up detection
- Refinement request recognition
- Topic shift signals
- Code language persistence

### Token Allocation

| Context | Tokens | Use Case |
|---------|--------|----------|
| Quick | 80 | Short answers (1-2 sentences) |
| Normal | 150 | Standard conversation (2-4 sentences) |
| Detailed | 250 | In-depth responses (4-6 sentences) |
| Technical | 600 | Code examples and explanations |

### API Configuration

- **Model:** `llama-3.3-70b-versatile`
- **Rate Limit:** 30 requests/minute
- **Timeout:** 30 seconds
- **Retry Attempts:** 2

---

## Troubleshooting

<details>
<summary><b>API Key Issues</b></summary>

**Error:** `GROQ_API_KEY not found`

- Ensure `.env` file exists in project root
- Verify API key is properly set without quotes
- Check for extra spaces or newlines

```bash
# Correct format
GROQ_API_KEY=gsk_your_actual_key_here
```
</details>

<details>
<summary><b>Rate Limit Errors</b></summary>

**Error:** `Rate limit exceeded`

- Wait 60 seconds between large request batches
- Consider adding additional API keys in `core/api_pool.py`
- Check your Groq console for quota status

</details>

<details>
<summary><b>Empty or Invalid Responses</b></summary>

- Check internet connection
- Verify API key validity at [console.groq.com](https://console.groq.com)
- Review logs in `logs/pacify_defy.log`
- Enable debug mode: `DEBUG_MODE=true python cli.py`

</details>

<details>
<summary><b>Persona File Not Found</b></summary>

- Ensure `personas/` directory structure is intact
- Verify JSON files exist for all personas
- Re-run setup script: `./setup.sh`

</details>

---

## Environment Variables

```bash
# Required
GROQ_API_KEY=your_api_key_here

# Optional
DEBUG_MODE=false          # Enable verbose logging
```

---

## Performance Considerations

- **Context Window:** Higher limits (8-10) increase token usage
- **Response Length:** "Detailed" setting uses ~2x tokens of "normal"
- **History Size:** Default 20 exchanges (~2-4k tokens for context)
- **Rate Limiting:** Built-in throttling prevents API quota exhaustion

---

## Documentation

- [CHANGELOG.md](CHANGELOG.md) — Version history and updates
- [docs/](docs/) — Extended guides and API documentation
- [LICENSE](LICENSE) — MIT License

---

## Contributing

Contributions are welcome. Please ensure:

- Code follows existing architecture patterns
- Persona modifications update corresponding JSON files
- New features include appropriate error handling
- Changes maintain user data isolation in memory system

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Built with [Groq's LLaMA 3.3 70B](https://groq.com) · Terminal UI by [Rich](https://rich.readthedocs.io/) · ASCII art via [pyfiglet](https://github.com/pwaller/pyfiglet)

---

<div align="center">

**Version 1.0.0** · *Last Updated: January 2026*

[Report Bug](../../issues) · [Request Feature](../../issues) · [Documentation](docs/)

</div>
