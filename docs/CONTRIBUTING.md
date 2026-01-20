# Contributing to Pacify & Defy

Thank you for considering contributing to Pacify & Defy. This document outlines the process and guidelines for contributions.

## How to Contribute

### Reporting Bugs

Before creating a bug report:
- Check existing issues to avoid duplicates
- Verify the bug with the latest version
- Collect relevant information (logs, error messages, steps to reproduce)

When filing a bug report, include:
- Clear, descriptive title
- Detailed steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, dependencies)
- Relevant logs from `logs/pacify_defy.log`

### Suggesting Features

Feature requests should include:
- Clear use case and motivation
- Detailed description of proposed functionality
- How it fits within existing architecture
- Any implementation considerations

### Pull Requests

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines

3. **Test thoroughly**
   - Verify core functionality works
   - Test both Pacify and Defy modes
   - Check all personas (Pacificia, Sage, Void, Rebel)
   - Ensure database operations maintain user isolation

4. **Commit with clear messages**
   ```bash
   git commit -m "Add: Feature description"
   git commit -m "Fix: Bug description"
   git commit -m "Docs: Documentation update"
   ```

5. **Push to your fork** and submit a pull request
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

### Python Code

- Follow PEP 8 conventions
- Use type hints where applicable
- Maximum line length: 100 characters
- Use descriptive variable names (balance clarity with brevity)

**Example:**
```python
def get_response(self, user_input: str) -> Dict:
    """
    Generate AI response with context awareness.
    
    Args:
        user_input: User's message
    
    Returns:
        Dictionary with response and metadata
    """
    # Implementation
```

### Persona JSON Files

When modifying persona configurations:

- Maintain consistent structure across all personas
- Test changes with actual conversations
- Update documentation if persona behavior changes significantly

**Structure:**
```json
{
  "name": "PersonaName",
  "role": "Brief role description",
  "core_identity": "Core personality",
  "conversational_dna": {
    "tone": "...",
    "style": "...",
    "response_pattern": "..."
  },
  "unique_traits": [],
  "never_does": []
}
```

### Database Changes

If modifying the database schema:

- Ensure backward compatibility or provide migration script
- Maintain user data isolation (all tables must filter by `user_id`)
- Update `memory.py` and relevant documentation
- Test with existing data

## Project Architecture

### Core Components

- **`cli.py`** — Terminal interface and command handling
- **`core/brain.py`** — AI logic, API integration, context tracking
- **`core/memory.py`** — Database operations, preference learning
- **`core/config.py`** — Configuration management
- **`core/formatters.py`** — Response formatting, code detection
- **`personas/*.json`** — Persona definitions (source of truth)

### Design Principles

1. **User Data Isolation** — Every database query must filter by `user_id`
2. **Dynamic JSON Loading** — Personas load from JSON, not hardcoded strings
3. **Context Awareness** — Maintain conversation flow and topic tracking
4. **Minimal Dependencies** — Only essential packages
5. **Clean UX** — Clear, scannable terminal output

## Testing Checklist

Before submitting:

- [ ] Code runs without errors
- [ ] All four personas function correctly
- [ ] Mode switching works (Pacify ↔ Defy)
- [ ] Database operations complete successfully
- [ ] Export functionality produces valid files
- [ ] Preference learning persists across sessions
- [ ] No API key leaks in code or logs
- [ ] Documentation updated if needed

## Documentation

When adding features:

- Update `README.md` if user-facing
- Add inline comments for complex logic
- Update `CHANGELOG.md` with changes
- Document new commands in help system

## Questions?

If you're unsure about anything:

- Open an issue with the `question` label
- Check existing documentation in `docs/`
- Review similar implementations in the codebase

---

Thank you for helping improve Pacify & Defy!
