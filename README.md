# Termora

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

Termora is a privacy-first, local-first AI agent that lives in your terminal. It understands natural language and translates your requests into safe, explainable shell commands.

Termora is:

- 🧠 **Context-aware** (files, OS, shell history)
- 🛡️ **Safe** (dry-run previews, rollback support, backups)
- 🔁 **Agentic** (can reason over multi-step workflows)
- 💬 **Conversational** (you don't have to write in "command speak")

## Examples

Say things like:

```bash
termora chat
> organize my downloads folder and group files by type
> create a daily backup routine to Dropbox
> mute my Mac when I join Zoom
> summarize today's git changes
```

Termora figures out what to do, explains it, and asks you for confirmation. It logs everything locally.

## Features

- **Natural Language Interface**: Just describe what you want done
- **Context-Aware Reasoning**: Understands your files, OS, and recent commands
- **Safe Execution**: Preview commands before they run
- **Automatic Backups**: Creates backups before destructive operations
- **Rollback Support**: `termora rollback last` to undo operations
- **Multi-model Support**: Works with OpenAI, Groq, Claude, or local Ollama models
- **Cross-platform**: Supports macOS and Linux

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

# Rollback the last operation
termora rollback last
```

It's not just a shell tool — it's your agentic terminal copilot.

## 🛡️ Privacy & Security

- Commands are processed securely with backups for destructive operations
- All logs stored locally in `~/.termora/`
- Optional: Use local AI models via Ollama for complete privacy

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
