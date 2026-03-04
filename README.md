---
title: Pacify & Defy
---

# Pacify & Defy

<div align="center">

<!-- ────────────────────────────────
     HERO (animated, no ASCII)
     Swap to your own GIF later (guide below)
     ──────────────────────────────── -->

<!-- Option A (now): animated typing SVG (no assets required) -->
<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=46&pause=900&color=F59E0B&center=true&vCenter=true&width=980&lines=Pacify+%26+Defy;Two+modes.+Four+personas.;Persistent+memory.+Context+aware.;CLI+assistant+with+teeth." alt="Pacify & Defy Typing" />

<br/>

<strong>collaborate gently • or get the truth raw</strong>

<br/><br/>

<!-- Option B (later): replace with your own animated title -->
<!-- <img src="assets/pacify-defy-title.gif" alt="Pacify & Defy Animated Title" width="70%" /> -->

<img src="assets/banner.gif" alt="Pacify & Defy Banner" width="100%" />

<br/><br/>

<a href="https://github.com/LoneMagma/Pacify-DefyAI">
  <img src="https://img.shields.io/badge/repo-LoneMagma%2FPacify--DefyAI-111827?style=for-the-badge&labelColor=000000" />
</a>
<a href="https://github.com/LoneMagma/Pacify-DefyAI">
  <img src="https://img.shields.io/badge/status-active%20development-f59e0b?style=for-the-badge&labelColor=000000" />
</a>
<a href="https://www.python.org/downloads/">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776ab?style=for-the-badge&logo=python&logoColor=white&labelColor=000000" />
</a>
<a href="https://groq.com">
  <img src="https://img.shields.io/badge/Powered%20by-Groq-f97316?style=for-the-badge&labelColor=000000" />
</a>
<a href="LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge&labelColor=000000" />
</a>

<br/><br/>

> *A dual‑mode CLI AI with persistent memory, context awareness, and personality adaptation.*

<p>
  <a href="#what-is-this">What is this</a> •
  <a href="#modes--personas">Modes</a> •
  <a href="#quick-start">Quick start</a> •
  <a href="#commands">Commands</a> •
  <a href="#features">Features</a> •
  <a href="#project-structure">Structure</a> •
  <a href="#troubleshooting">Troubleshooting</a>
</p>

</div>

---

## What is this

**Pacify & Defy** is a CLI-based conversational system with **two modes** and **four personas**.
It remembers what matters (SQLite persistence), adapts your preferences, and responds with the kind of tone you picked:
soft guidance… or blunt truth.

It runs on the **Groq API** (free tier works), stays lightweight, and is designed to feel like a *tool*, not a toy.

---

## Modes & personas

<div align="center">

| Mode | Vibe | Personas |
|---|---|---|
| **Pacify** | collaborative, structured | **Pacificia** (mood-adaptive) · **Sage** (implementation guide) |
| **Defy** | direct, unfiltered | **Void** (brutally honest) · **Rebel** (technical specialist) |

</div>

<details>
<summary><b>Persona cheat-sheet (click)</b></summary>

- **Pacificia**: emotionally adaptive, supportive, remembers preferences, can be witty/poetic.
- **Sage**: step-by-step implementation, less fluff, more structure.
- **Void**: no sugar coating, short brutal clarity (still helpful).
- **Rebel**: technical answers with minimal guardrails (you asked for it).

</details>

---

## Quick start

### Get the repo
```bash
git clone https://github.com/LoneMagma/Pacify-DefyAI.git
cd Pacify-DefyAI
```

### Install (Linux / macOS / WSL)
```bash
chmod +x setup.sh
./setup.sh
```

### Install (Windows PowerShell)
```powershell
.\setup.ps1
```

### Set your Groq key
Get a free key from Groq console:
- https://console.groq.com/keys

```bash
cp .env.example .env
```

Edit `.env`:
```env
GROQ_API_KEY=your_api_key_here
```

### Launch
```bash
python cli.py
```

---

## Commands

### Essentials
```bash
/help              # Command reference
/status            # Current configuration
/stats             # Conversation statistics
/history [N]       # Recent conversations
/export [file]     # Export conversation history
```

### Mode & persona control
```bash
/setmode pacify    # Switch to Pacify
/setmode defy      # Switch to Defy
/persona sage      # Switch persona
/mood witty        # Pacificia mood (only)
```

### Settings
```bash
/set length quick|normal|detailed    # Response length
/set context 1-10                    # Context window size
/set temperature 0.1-1.0            # Creativity level
/set metadata on|off                # Toggle metadata display
/set autosave on|off                # Auto-save on exit
```

### Data management
```bash
/search <keyword>  # Search conversation history
/opinions          # View tracked opinions
/copy [N]          # Copy response to clipboard
/clear             # Clear session memory
```

---

## Features

- **Persistent memory** — SQLite conversation history with user isolation
- **Context awareness** — topic tracking, follow-up detection, conversation flow
- **Preference learning** — adapts to your style automatically
- **Mood system** — Pacificia adjusts tone dynamically
- **Code intelligence** — detects/format code blocks automatically
- **Session management** — state saved across sessions with contextual greetings
- **Exports** — TXT / JSON / Markdown

<details>
<summary><b>Export formats (examples)</b></summary>

**TXT**
```text
Pacify & Defy - Conversation Export
Mode: pacify | Persona: sage
============================================================
[1] 2026-01-20T10:30:00
You: How do I implement a binary search tree?
sage: [response...]
```

**JSON**
```json
{
  "mode": "pacify",
  "persona": "sage",
  "export_date": "2026-01-20T10:30:00",
  "conversations": [
    {
      "timestamp": "2026-01-20T10:30:00",
      "user": "How do I implement a binary search tree?",
      "ai": "[response content]"
    }
  ]
}
```

</details>

---

## Project structure
```text
Pacify-DefyAI/
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

## Technical details

### Memory system

SQLite-backed persistence with complete user data isolation:

| Table | Purpose |
|---|---|
| `conversations` | Exchange history + metadata |
| `opinions` | Tracked viewpoints + confidence |
| `preferences` | Learned + manual preferences |
| `emotional_tracking` | Sentiment signals over time |
| `session_state` | Persistent config across restarts |

### Context awareness tracks

- Current topic identification
- Follow-up detection
- Refinement request recognition
- Topic shift signals
- Code language persistence

### Token allocation

| Context | Tokens | Use case |
|---|---:|---|
| Quick | 80 | 1–2 sentences |
| Normal | 150 | 2–4 sentences |
| Detailed | 250 | 4–6 sentences |
| Technical | 600 | Code examples + breakdowns |

### API configuration

- **Model:** `llama-3.3-70b-versatile`
- **Rate limit:** ~30 req/min (provider-side; varies)
- **Timeout:** 30s
- **Retry attempts:** 2

---

## Troubleshooting

<details>
<summary><b>GROQ_API_KEY not found</b></summary>

- Ensure `.env` exists in the project root
- Verify key format (no quotes, no trailing spaces)

```bash
GROQ_API_KEY=gsk_your_actual_key_here
```
</details>

<details>
<summary><b>Rate limit exceeded</b></summary>

- Wait ~60 seconds between big batches
- Add additional keys in `core/api_pool.py`
- Check quota on Groq console

</details>

<details>
<summary><b>Empty / invalid responses</b></summary>

- Check internet connection
- Validate key at Groq console
- Review logs in `logs/pacify_defy.log`
- Enable debug: `DEBUG_MODE=true python cli.py`

</details>

<details>
<summary><b>Persona file not found</b></summary>

- Ensure `personas/` directory structure exists
- Verify all JSON files are present
- Re-run setup: `./setup.sh` or `.\setup.ps1`

</details>

---

## Documentation

- `CHANGELOG.md` — Version history
- `docs/` — Extended guides
- `LICENSE` — MIT License

---

## Contributing

PRs welcome. Please keep:

- Existing architecture patterns
- Persona JSON files in sync with behavior
- Error handling (especially around API calls)
- User data isolation intact

---

## Acknowledgments

Built with Groq’s LLaMA 3.3 70B · Terminal UI by Rich · vibecoded (credits in `credits.md`)

---

<div align="center">

**Version 1.0.0** · *Last Updated: January 2026*

<a href="https://github.com/LoneMagma/Pacify-DefyAI/issues">Report Bug</a> ·
<a href="https://github.com/LoneMagma/Pacify-DefyAI/issues">Request Feature</a> ·
<a href="docs/">Documentation</a>

<br/><br/>

built by <a href="https://github.com/LoneMagma">LoneMagma</a> • choose peace or chaos.

</div>

---

## How to add your own animated hero later (GIF)

1) Create an `assets/` folder in the repo root (if it doesn’t exist):
```bash
mkdir assets
```

2) Drop your files:
- `assets/pacify-defy-title.gif` (logo/title animation)
- `assets/banner.gif` (wide banner vibe strip)

3) At the top of this README:
- Uncomment the “Option B” `<img src="assets/pacify-defy-title.gif" .../>`
- Optionally remove the typing SVG line

4) Keep files GitHub-friendly:
- Aim for **< 5–8 MB** per GIF
- Title width ~**900–1200px**
- Banner width ~**1200–1600px**

That’s it — commit + push, and GitHub will render them automatically.
