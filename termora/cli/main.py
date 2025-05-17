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
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import traceback

from termora.core.context import TerminalContext
from termora.core.agent import TermoraAgent
from termora.core.executor import CommandExecutor
from termora.core.rollback import RollbackManager
from termora.core.history import HistoryManager
from termora.core.pipeline import TermoraPipeline

# Create custom theme
termora_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "command": "bold blue",
    "python": "bold purple",
    "step": "bold magenta",
})

class TermoraCLI:
    """Main CLI interface for Termora."""
    
    def __init__(self, model: str = "groq", verbose: bool = False):
        """
        Initialize the Termora CLI.
        
        Args:
            model: AI model to use ("openai", "groq", or "ollama")
            verbose: Whether to show verbose output
        """
        
        self.verbose = verbose
        self.console = Console(theme=termora_theme)
        self.context = TerminalContext()
        
        # Create agent config with the selected model
        agent_config = {
            "ai_provider": model,
            "ai_model": "llama3-70b-8192" if model == "groq" else "gpt-4" if model == "openai" else "llama3",
            "temperature": 0.7,
            "max_tokens": 2000
        }
        self.agent = TermoraAgent(config=agent_config)
        
        self.executor = CommandExecutor()
        self.rollback = RollbackManager()
        self.history_manager = HistoryManager()
        
        # Create pipeline
        self.pipeline = TermoraPipeline(
            agent=self.agent,
            executor=self.executor,
            context_provider=self.context,
            history_manager=self.history_manager,
            rollback_manager=self.rollback
        )
    
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
    
    def process_input(self, user_input: str) -> None:
        """
        Process a single user input using the pipeline.
        
        Args:
            user_input: Natural language input from user
        """
        if user_input.lower() in ['exit', 'quit']:
            # Save history before exiting
            self._save_command_history()
            self.console.print("[success]Goodbye![/success]")
            sys.exit(0)
            
        try:
            # Add to command history and save
            self.command_history.append(user_input)
            self._save_command_history()
            
            # Process through pipeline
            self.console.print("\n[info]I'll help you with that.[/info]")
            
            # Use pipeline to process the request
            with Progress(
                SpinnerColumn(),
                TextColumn("[info]Processing your request...[/info]"),
                console=self.console,
                transient=True
            ) as progress:
                progress.add_task("", total=None)
                result = self.pipeline.process(user_input)
            
            # Check result and provide feedback
            if result.get("executed", False):
                self.console.print("\n[success]Plan completed successfully![/success]")
            else:
                self.console.print("\n[warning]Plan execution was cancelled or failed.[/warning]")
                
        except Exception as e:
            self.console.print(f"[error]Error: {str(e)}[/error]")
            if self.verbose:
                self.console.print(Panel(traceback.format_exc(), title="Detailed Error", border_style="red"))
    
    def start_repl(self) -> None:
        """Start the Read-Eval-Print Loop."""
        try:
            while True:
                try:
                    # Get current directory for the prompt
                    current_dir = os.getcwd()
                    # Create a more informative prompt showing the current directory
                    prompt = f"\n[blue]Current Directory: {current_dir}[/blue]\n[cyan]>[/cyan] "
                    user_input = self.console.input(prompt)
                    if user_input.strip():
                        self.process_input(user_input)
                except KeyboardInterrupt:
                    self.console.print("\n[warning]Interrupted. Type 'exit' to quit.[/warning]")
                except EOFError:
                    # Save history before exiting
                    self._save_command_history()
                    self.console.print("\n[success]Goodbye![/success]")
                    break
        finally:
            # Final history save on exit
            self._save_command_history()


def parse_args(args: List[str]) -> Dict[str, Any]:
    """
    Parse command line arguments.
    
    Args:
        args: Command line arguments
        
    Returns:
        Dictionary of parsed arguments
    """
    parser = argparse.ArgumentParser(description="Termora - AI-powered terminal assistant")
    parser.add_argument(
        "--model", 
        choices=["openai", "groq", "ollama"],
        default="groq",
        help="AI model to use"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show verbose output"
    )
    
    return vars(parser.parse_args(args))


def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args(sys.argv[1:])
    cli = TermoraCLI(model=args["model"], verbose=args["verbose"])
    cli.start_repl()


if __name__ == "__main__":
    main()
        