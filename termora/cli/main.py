"""
Termora CLI - Main user interface for the Termora terminal assistant.
"""

import os
import sys
import argparse
from typing import Optional, List, Dict, Any
import json
import readline  # For command history in terminal
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from rich.prompt import Confirm
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from termora.core.context import TerminalContext
from termora.core.agent import TermoraAgent
from termora.core.executor import CommandExecutor
from termora.core.rollback import RollbackManager

# Create custom theme
termora_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "command": "bold blue",
    "step": "bold magenta",
})

class TermoraCLI:
    """Main CLI interface for Termora."""
    
    def __init__(self, model: str = "openai", verbose: bool = False):
        """
        Initialize the Termora CLI.
        
        Args:
            model: AI model to use ("openai", "groq", or "ollama")
            verbose: Whether to show verbose output
        """
        
        self.verbose = verbose
        self.console = Console(theme=termora_theme)
        self.context = TerminalContext()
        self.agent = TermoraAgent(model_name=model)
        self.executor = CommandExecutor()
        self.rollback = RollbackManager()
        
        # Create and load command history
        self.history_file = self._get_history_file_path()
        self.command_history = self._load_command_history()
        
        self._display_welcome()
        
    def _get_history_file_path(self) -> Path:
        """Get the path to the command history file."""
        # Create ~/.termora directory if it doesn't exist
        termora_dir = Path.home() / ".termora"
        termora_dir.mkdir(exist_ok=True)
        
        # Return path to history file
        return termora_dir / "command_history.json"
    
    def _load_command_history(self) -> List[str]:
        """Load command history from file."""
        if not self.history_file.exists():
            return []
            
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If there's an error reading the file, start with empty history
            return []
    
    def _save_command_history(self) -> None:
        """Save command history to file."""
        try:
            # Keep only the latest 1000 commands
            history_to_save = self.command_history[-1000:] if len(self.command_history) > 1000 else self.command_history
            
            with open(self.history_file, 'w') as f:
                json.dump(history_to_save, f)
        except IOError as e:
            if self.verbose:
                self.console.print(f"[warning]Could not save command history: {str(e)}[/warning]")
    
    def _display_welcome(self) -> None:
        """Display the welcome message."""
        welcome_text = """
        # TERMORA
        
        Your AI-powered terminal assistant
        
        Type your requests in natural language.
        Type 'exit' or 'quit' to exit.
        """
        welcome_panel = Panel(
            Markdown(welcome_text.strip()),
            border_style="cyan",
            expand=False,
            padding=(1, 2)
        )
        self.console.print(welcome_panel)
    