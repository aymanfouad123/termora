# Termora

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

**Your agentic AI terminal with perfect memory, intelligent automation, and reliable rollbacks.**

(Currently in progress 🛠️)

Termora is an intelligent AI-powered terminal assistant that remembers how you work, dynamically reasons through tasks, and executes operations with safety and transparency—all through natural language conversation.

## Key Capabilities

- **Agentic Intelligence**: Reasons dynamically about tasks, generating multi-step workflows
- **Contextual Awareness**: Gathers information about directories, files, commands, and git status
- **Perfect Memory**: Maintains history of commands and adapts to your patterns
- **Intelligent Automation**: Creates and manages workflows through natural language
- **Enhanced Safety**: Provides automatic backups and rollback capabilities

## Examples

Just say what you want:

```bash
termora
> find all screenshots from March and move them to a new folder
> run the git command I used yesterday to find large files
> clean up my downloads folder but keep the PDFs from this year
> remind me to backup my project directory every Friday
> every weekday at 9am, open VS Code and do a git pull in my main
project
```

Termora analyzes your request, shows you exactly what it will do, and executes after your confirmation. Unlike other tools, it remembers your past commands and adapts to how you work.

## Example Use Cases

### Intelligent File Management

```
> Keep only the 10 newest versions of each log file and compress the rest
> Find duplicate files across my home directory and help me remove them
> Move all PDFs from my downloads that contain "invoice" into my tax folder
```

### System Operations

```
> Show me the largest files in my home directory
> Clean up disk space by finding unused packages and cached files
> Check which processes are using the most memory right now
```

### Smart Automation

```
> Check my disk space every morning and alert me if it's below 10%
> Archive my log files at the end of each week
> Restart my local server if it stops responding
```

## Features

- **True Natural Language**: Communicate your intent conversationally
- **Dynamic Reasoning**: Generates shell commands or Python code based on your needs
- **Perfect Command Memory**: Recalls your past solutions in similar contexts
- **Task Planning**: Creates and executes multi-step workflows for complex goals
- **Transparent Execution**: Shows you exactly what it will do before doing it
- **Enhanced Safety**: Creates targeted backups with rollback capabilities
- **AI Flexibility**: Works with OpenAI, Groq, Claude, or local Ollama models
- **Cross-platform**: Supports macOS and Linux

## Why Termora?

Most terminal tools require exact command syntax or scripting for complex tasks. Termora lets you describe what you want in natural language and figures out how to make it happen—whether that means running shell commands, generating code, or combining multiple tools.

What makes Termora unique is its memory—it remembers how you've solved similar problems before and adapts to your personal patterns, becoming more personalized the more you use it.

## Installation

```bash
# Not yet available via pip - coming soon!
git clone https://github.com/aymanfouad123/termora.git
cd termora
pip install -e .
```

## Usage

Simply start Termora and tell it what you want in natural language:

```bash
termora
```

That's it. No commands to learn, no flags to remember. Just describe what you want, and Termora figures out the rest.

## Privacy & Security

- All processing can happen locally on your machine with Ollama
- Command history remains private and secure in `~/.termora/`
- Automatic backups protect against unintended changes
- Full transparency in what commands will be executed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Termora: Your AI-powered terminal with perfect memory, intelligent automation, and enhanced safety.
