#!/usr/bin/env python3
"""
Quick Termora CLI - A simple interface to test Termora's API communication.
"""

import asyncio
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from termora.core.agent import TermoraAgent

# Rich imports for pretty formatting
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

# Create console instance
console = Console()

def setup_environment():
    """Setup environment variables and check API key."""
    # Load environment variables
    load_dotenv()
    
    # Check if API key is set
    if not os.getenv("GROQ_API_KEY"):
        console.print(Panel.fit(
            "[red]Error: GROQ_API_KEY not found in .env file[/red]\n\n"
            "Please create a .env file with your GROQ_API_KEY\n"
            "Example .env file content:\n"
            "GROQ_API_KEY=your_groq_api_key_here\n"
            "AI_PROVIDER=groq\n"
            "AI_MODEL=llama3-70b-8192",
            title="Configuration Error",
            border_style="red"
        ))
        sys.exit(1)

def verify_path(path: str) -> bool:
    """Verify if a path exists and is accessible."""
    try:
        return os.path.exists(os.path.expanduser(path))
    except Exception:
        return False

def get_desktop_path() -> str:
    """Get the user's desktop path."""
    try:
        # Try to get desktop path from environment
        desktop = os.path.expanduser("~/Desktop")
        if verify_path(desktop):
            return desktop
            
        # Try alternative paths based on OS
        if sys.platform == "darwin":  # macOS
            desktop = os.path.expanduser("~/Desktop")
        elif sys.platform == "linux":
            desktop = os.path.expanduser("~/Desktop")
        elif sys.platform == "win32":
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            
        if verify_path(desktop):
            return desktop
            
        # Try to get from environment variables
        desktop = os.getenv("DESKTOP") or os.getenv("USERPROFILE")
        if desktop and verify_path(desktop):
            return desktop
            
        return None
    except Exception:
        return None

def execute_shell_command(command: str, is_destructive: bool = False) -> tuple[bool, str, str]:
    """Execute a shell command safely."""
    try:
        # Expand desktop path in command if present
        if "~/Desktop" in command:
            desktop_path = get_desktop_path()
            if not desktop_path:
                return False, "", "Could not find desktop directory"
            command = command.replace("~/Desktop", desktop_path)
        
        # For destructive commands, first list what will be affected
        if is_destructive and "delete" in command.lower():
            # Extract the find command without the -delete
            list_cmd = command.replace(" -delete", "")
            # Run the list command first
            list_result = subprocess.run(
                list_cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if list_result.returncode == 0:
                files = [f.strip() for f in list_result.stdout.splitlines() if f.strip()]
                if files:
                    console.print(Panel(
                        f"[yellow]The following {len(files)} files will be deleted:[/yellow]\n" + 
                        "\n".join(f"• {f}" for f in files),
                        title="⚠️  Warning: Destructive Operation",
                        border_style="red"
                    ))
                    
                    if not Confirm.ask("Are you sure you want to delete these files?", console=console):
                        return True, "Operation cancelled by user", ""
                else:
                    return False, "", "No files found to delete"
            else:
                return False, "", f"Error listing files: {list_result.stderr}"
        
        # Execute the actual command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        # For search-type commands with no results, provide clear feedback
        is_search = any(cmd in command for cmd in ['find', 'grep', 'ls'])
        if result.returncode == 0 and not result.stdout.strip() and is_search:
            # Finding files but got no results
            if 'find' in command and '-name' in command:
                pattern = command.split('-name')[1].strip().split()[0].strip("'\"")
                location = command.split('find')[1].strip().split()[0]
                return True, f"No files matching {pattern} found in {location}", ""
        
        # For destructive commands, show what was done
        if is_destructive and result.returncode == 0:
            return True, f"Successfully deleted files from {command.split()[1]}", ""
            
        return (
            result.returncode == 0,
            result.stdout.strip(),
            result.stderr.strip()
        )
    except Exception as e:
        return False, "", str(e)

async def execute_python_code(code: str) -> tuple[bool, str, str]:
    """Execute Python code safely."""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        # Execute the Python file
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()  # Ensure we're in the current directory
        )
        
        # Clean up
        os.unlink(temp_path)
        
        return (
            result.returncode == 0,
            result.stdout.strip(),
            result.stderr.strip()
        )
    except Exception as e:
        return False, "", str(e)

def get_user_confirmation(action: dict) -> bool:
    """Get user confirmation before executing an action."""
    # Create a table for the action details
    table = Table(show_header=False, box=None)
    table.add_row("Action:", action['explanation'])
    table.add_row("Type:", action['type'])
    table.add_row("Command:", Syntax(action['content'], "bash", theme="monokai"))
    
    # Show the action in a panel
    console.print(Panel(table, title="Action Details", border_style="blue"))
    
    # Get confirmation
    return Confirm.ask("Execute this command?", console=console)

def display_results(success: bool, stdout: str, stderr: str):
    """Display command execution results in a pretty format."""
    if success:
        if stdout:
            # Split output into lines and count them
            lines = stdout.splitlines()
            if len(lines) > 0:
                console.print(Panel(
                    Syntax(stdout, "text", theme="monokai"),
                    title=f"Command Output ({len(lines)} items)",
                    border_style="green"
                ))
            else:
                console.print("[yellow]No output generated.[/yellow]")
        else:
            # Handle success but no output (common for searches with no matches)
            console.print(Panel(
                "[yellow]Command executed successfully, but no items were found.[/yellow]",
                title="No Results",
                border_style="yellow"
            ))
    else:
        if stderr:
            console.print(Panel(
                Syntax(stderr, "text", theme="monokai"),
                title="Error",
                border_style="red"
            ))
        else:
            console.print(Panel(
                "[red]Unknown error occurred[/red]",
                title="Error",
                border_style="red"
            ))

async def quick_termora_request(question: str) -> None:
    """Send a request to Groq and get a response, then execute the commands."""
    try:
        # Check for desktop operations
        if "desktop" in question.lower():
            desktop_path = get_desktop_path()
            if not desktop_path:
                console.print(Panel(
                    "[red]Error: Could not find your desktop directory.[/red]\n"
                    "Please verify that your desktop exists and is accessible.",
                    title="Path Error",
                    border_style="red"
                ))
                return
                
            # Let the user know which path will be used
            console.print(f"[dim]Using desktop path: {desktop_path}[/dim]")
        
        # Create agent with minimal configuration
        agent = TermoraAgent({
            "send_to_api": True,
            "ai_provider": "groq",
            "ai_model": "llama3-70b-8192"
        })
        
        # Show progress while getting response
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            progress.add_task(description="Thinking...", total=None)
            plan = await agent.process_request(question)
        
        # Print the response in a pretty format
        console.print(Panel(
            Markdown(f"**Explanation:** {plan.explanation}"),
            title="Termora Response",
            border_style="green"
        ))
        
        if not plan.actions:
            console.print("[yellow]No actions generated.[/yellow]")
            return
            
        # Process each action
        for i, action in enumerate(plan.actions, 1):
            console.print(f"\n[bold blue]Action {i}[/bold blue]")
            
            # Check if this is a destructive operation
            is_destructive = any(word in action['content'].lower() 
                               for word in ['delete', 'remove', 'rm', 'unlink'])
            
            # Get user confirmation
            if not get_user_confirmation(action):
                console.print("[yellow]Skipping this action.[/yellow]")
                continue
            
            # Execute the action
            if action['type'] == 'shell_command':
                success, stdout, stderr = execute_shell_command(
                    action['content'],
                    is_destructive=is_destructive
                )
            elif action['type'] == 'python_code':
                success, stdout, stderr = await execute_python_code(action['content'])
            else:
                console.print(f"[red]Unknown action type: {action['type']}[/red]")
                continue
            
            # Display results
            display_results(success, stdout, stderr)
            
    except Exception as e:
        error_msg = str(e)
        if "Event loop is closed" in error_msg:
            error_msg = "Connection to AI service was interrupted. Please try again."
        console.print(Panel(
            f"[red]Error: {error_msg}[/red]\n\n"
            "This might be due to:\n"
            "1. Invalid API key\n"
            "2. Network connection issues\n"
            "3. API rate limiting\n"
            "4. Invalid request format",
            title="Error",
            border_style="red"
        ))

def print_welcome():
    """Print a pretty welcome message."""
    console.print(Panel.fit(
        "[bold green]Welcome to Quick Termora![/bold green]\n\n"
        "Type your questions and press Enter.\n"
        "Type 'quit' or 'exit' to end the session.\n"
        "Type 'help' for example questions.",
        title="Termora CLI",
        border_style="green"
    ))
    
    # Create a table for example questions
    table = Table(title="Example Questions", show_header=False, box=None)
    table.add_row("• List all images in current directory")
    table.add_row("• Find all PDF files in Downloads")
    table.add_row("• Create a backup of current directory")
    table.add_row("• Find all files containing 'TODO' comments")
    
    console.print(table)

def print_help():
    """Print help information in a pretty format."""
    table = Table(title="Example Questions", show_header=False, box=None)
    table.add_row("• List all images in current directory")
    table.add_row("• Find all PDF files in Downloads")
    table.add_row("• Create a backup of current directory")
    table.add_row("• Find all files containing 'TODO' comments")
    table.add_row("• Show disk usage of current directory")
    table.add_row("• Count lines in all Python files")
    
    console.print(Panel(table, title="Help", border_style="blue"))

async def main_async():
    """Async main function to handle the event loop properly."""
    # Setup environment
    setup_environment()
    
    # Print welcome message
    print_welcome()
    
    while True:
        try:
            # Get user input with a custom prompt
            question = console.input("\n[bold green]termora>[/bold green] ").strip()
            
            # Check for exit commands
            if question.lower() in ('quit', 'exit'):
                console.print("\n[bold green]Goodbye![/bold green]")
                break
                
            # Check for help command
            if question.lower() == 'help':
                print_help()
                continue
            
            if question:
                # Process the request
                await quick_termora_request(question)
                
        except KeyboardInterrupt:
            console.print("\n\n[bold green]Goodbye![/bold green]")
            break
        except Exception as e:
            console.print(Panel(
                f"[red]Unexpected error: {str(e)}[/red]\n"
                "Please try again or type 'quit' to exit.",
                title="Error",
                border_style="red"
            ))

def main():
    """Main entry point for the quick Termora CLI."""
    try:
        # Run the async main function
        asyncio.run(main_async())
    except KeyboardInterrupt:
        console.print("\n\n[bold green]Goodbye![/bold green]")
    except Exception as e:
        console.print(Panel(
            f"[red]Fatal error: {str(e)}[/red]\n"
            "The application encountered an unexpected error.",
            title="Fatal Error",
            border_style="red"
        ))
        sys.exit(1)

if __name__ == "__main__":
    main() 