"""
Termora CLI - Main user interface for the Termora terminal assistant.
"""

import os
import sys
import argparse
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
import traceback

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
    
    def __init__(self, model: str = "groq", verbose: bool = False, debug: bool = False):
        """
        Initialize the Termora CLI.
        
        Args:
            model: AI model to use ("openai", "groq", or "ollama")
            verbose: Whether to show verbose output
            debug: Whether to enable pipeline debug mode
        """
        self.verbose = verbose
        self.console = Console(theme=termora_theme)
        
        # Initialize pipeline with model configuration
        agent_config = {
            "ai_provider": model,
            "ai_model": "llama3-70b-8192" if model == "groq" else "gpt-4" if model == "openai" else "llama3",
            "temperature": 0.7,
            "max_tokens": 2000
        }
        self.pipeline = TermoraPipeline.from_config(agent_config, debug=debug)

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
        Only handles user interaction and display; all business logic is in the pipeline.
        """
        if user_input.lower() in ['exit', 'quit']:
            self.console.print("[success]Goodbye![/success]")
            sys.exit(0)
            
        try:
            self.console.print("\n[info]I'll help you with that.[/info]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[info]Processing your request...[/info]"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("", total=None)
                result = self.pipeline.process(user_input)
                
            if result.get("executed", False):
                self.console.print("\n[success]All operations completed successfully![/success]")
            else:
                reason = result.get("reason", "Unknown reason")
                self.console.print(f"\n[warning]Plan execution was cancelled or failed: {reason}[/warning]")
                if self.verbose and "error_details" in result:
                    self.console.print(Panel(result["error_details"], title="Error Details", border_style="red"))
        except Exception as e:
            self.console.print(f"[error]Critical error: {str(e)}[/error]")
            if self.verbose:
                self.console.print(Panel(traceback.format_exc(), title="Critical Error", border_style="red"))

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
                    self.console.print("\n[success]Goodbye![/success]")
                    break
        finally:
            # Let pipeline handle any cleanup
            self.pipeline.cleanup()

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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode to inspect pipeline steps"
    )
    
    return vars(parser.parse_args(args))

def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args(sys.argv[1:])
    cli = TermoraCLI(model=args["model"], verbose=args["verbose"], debug=args["debug"])
    cli.start_repl()

if __name__ == "__main__":
    main()
        