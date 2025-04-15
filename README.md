# Termora

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

**Your terminal with a memory.**

Termora is a context-aware terminal assistant that remembers how you work, learns your patterns, and automates your recurring workflows—all while handling complex one-off tasks with precision and safety.

## Key Capabilities

- **Temporal Intelligence**: Remembers your command history and automates time-based workflows
- **Context Awareness**: Understands your files, OS, and project environments
- **Pattern Recognition**: Learns how you work with different projects and adapts to your style
- **Safety First**: Provides previews, backups, and rollback support for all operations

## Examples

Say things like:

```bash
termora chat
> find all screenshots from March and move them to a new folder
> run the git command I used yesterday to find large files
> every weekday at 9am, open VS Code and do a git pull in my main project
> set up my development environment like I usually do for this project
```

Termora figures out what to do, explains it, and asks you for confirmation before execution. Unlike other tools, it remembers your past commands and patterns.

## Features

- **Natural Language Interface**: Communicate your intent conversationally
- **Command History Memory**: Recall and reuse past commands with context
- **Time-Based Automation**: Schedule recurring tasks and routines
- **Project Context Recognition**: Adapt behavior based on project environments
- **Safe Execution**: Preview commands before they run
- **Automatic Backups**: Create backups before destructive operations
- **Rollback Support**: `termora rollback last` to undo operations
- **Multi-model Support**: Works with OpenAI, Groq, Claude, or local Ollama models
- **Cross-platform**: Supports macOS and Linux

## Why Termora?

Most terminal tools execute in isolation—they have no memory of your past work and no awareness of your patterns. Termora maintains a persistent understanding of how you use your system, enabling it to work the way you do.

The more you use Termora, the more it learns about your preferences, routines, and projects. It doesn't just execute commands; it becomes your intelligent partner in the terminal.

## Installation

```bash
# Not yet available via pip - coming soon!
git clone https://github.com/aymanfouad123/termora.git
cd termora
pip install -e .
```

## Usage

```bash
# Start a conversation with Termora
termora chat

# Run commands automatically without confirmation
termora chat --auto

# View your command history with context
termora history

# Set up a recurring workflow
termora schedule "daily at 5pm" "check git repos for uncommitted changes"

# Rollback the last operation
termora rollback last
```

## Privacy & Security

- Commands are processed securely with backups for destructive operations
- All interaction history stored locally in `~/.termora/`
- Optional: Use local AI models via Ollama for complete privacy

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Termora: Terminal commands with perfect memory.
