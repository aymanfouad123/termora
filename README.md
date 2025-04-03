# Termora

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

An AI-powered, natural language terminal assistant that helps you get things done by just talking in the terminal.

## 🧠 Features

- **Natural Language First**: Tell Termora what you want in plain English
- **Secure Execution**: Preview commands before they run with backup and rollback
- **Agentic Planning**: Complex multi-step tasks executed as a sequence
- **OS Awareness**: Built with macOS and Linux support in mind
- **Local Logging**: All activities are logged locally for your review
- **Extensible**: Custom routines and workflows for common tasks

## 🚀 Installation

```bash
# Not yet available via pip - coming soon!
git clone https://github.com/yourusername/termora.git
cd termora
pip install -e .
```

## 🔨 Usage

```bash
# Start a conversation with Termora
termora chat

# Run commands automatically without confirmation
termora chat --auto

# Rollback the last operation
termora rollback last

# Execute common workflows
termora start dev
```

## 🛡️ Privacy & Security

- Commands are processed securely with backups for destructive operations
- All logs stored locally in `~/.termora/`
- Optional: Use local AI models via Ollama for complete privacy

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
