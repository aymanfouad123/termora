"""
Terminal context gathering module.

This module collects information about the user's terminal environment,
including current directory, recent commands, files, and git status.
This context helps the AI agent make more informed decisions.

Key functionality:
- TerminalContext: Main class for gathering context information
- get_context: Collects all context data into a dictionary
- to_string: Formats context information for inclusion in AI prompts
- get_directory_contents: Lists files in the current directory
- get_command_history: Retrieves recent command history
- get_git_status: Gets information about git repositories
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import shutil
import json

class TerminalContext:
    """
    Gathers and manages context information about the terminal environment.
    
    This class is responsible for collecting information that provides context to the AI, such as:
    - Current working directory
    - Files in the current directory
    - Recent command history
    - Git status (if in a git repository)
    - Operating system information
    """
    
    def __init__(self, max_history: int = 5, max_files: int = 20):
        """
        Initialize the terminal context gatherer.
        
        Args:
            max_history: Maximum number of recent commands to include in the context 
            max_files: Maximum number of files to list from current directory
        """
        
        self.max_history = max_history
        self.max_files = max_files
        self.os_name = platform.system()  # 'Linux', 'Darwin' (macOS), 'Windows'
    
    def get_context(self) -> Dict[str, Any]:
        """
        Gather all context information from the terminal environment.
        
        Returns:
            A dictionary containing context information
        """
        return {
            "os": self.os_name,
            "cwd": self.get_current_directory(),
            "files": self.get_directory_contents(),
            "history": self.get_command_history(),
            "git_status": self.get_git_status(),
            "environment": self.get_environment_info()
        }
    
    def get_current_directory(self) -> str:
        """
        Get the current working directory.
        
        Returns:
            The current working directory path as a string
        """
        return os.getcwd()
    
    def get_directory_contents(self) -> List[Dict[str,str]]:
        """
        Get information about files in the current directory.
        
        Returns:
            A list of dictionaries with file information
        """
        contents = []
        cwd =  Path(self.get_current_directory())
        
        try:
            # Get directory entries 
            entries = list(cwd.iterdir())
            
            # Sort by modified time, most recent first
            entries.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Limit to max_files
            entries = entries[:self.max_files]
            
            for entry in entries: 
                # Skip hidden files starting with .
                if entry.name.startswith('.') and entry.name != '.gitignore':
                    continue
                
                try:
                    # Get file information
                    stats = entry.stat()
                    file_info = {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stats.st_size,
                        "modified": stats.st_mtime
                    }
                    contents.append(file_info)
                except (PermissionError, FileNotFoundError):
                    # Skip files we can't access
                    pass
        except Exception as e:
            # Handle any unexpected errors
            contents.append({"error": f"Error listing directory: {str(e)}"})
            
        return contents
    
    def get_command_history(self) -> List[str]:
        """
        Get recent command history from the shell.
        
        Returns:
            A list of recent command strings
        """
        history = []
        
        # Different approaches based on OS
        if self.os_name in ('Linux', 'Darwin'):  # Currently supporting Linux or macOS
            # Try to get history from bash or zsh
            for shell_history in [
                os.path.expanduser('~/.bash_history'),
                os.path.expanduser('~/.zsh_history')
            ]:
                if os.path.exists(shell_history):
                    try:
                        # Read history file
                        with open(shell_history, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            
                        # Process the lines based on shell format
                        if shell_history.endswith('zsh_history'):
                            # zsh history has timestamps and other metadata
                            commands = []
                            for line in lines:
                                if ';' in line:
                                    # Extract just the command part
                                    cmd = line.split(';', 1)[1].strip()
                                    commands.append(cmd)
                        else:
                            # bash history is simpler
                            commands = [line.strip() for line in lines]
                            
                        # Get the most recent commands
                        history = commands[-self.max_history:]
                        break
                    except Exception:
                        # If we can't read the history file, continue to the next method
                        pass
                        
            # If we couldn't get history from files, try using the history command
            if not history and shutil.which('history'):
                try:
                    result = subprocess.run(
                        ['history', str(self.max_history)],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                    if result.returncode == 0:
                        # Parse the history output (format is usually "123 command")
                        for line in result.stdout.splitlines():
                            parts = line.strip().split(' ', 1)
                            if len(parts) > 1:
                                history.append(parts[1])
                except Exception:
                    # If history command fails, we'll return an empty list
                    pass
                
        return history[-self.max_history:] if history else []
    
    def get_git_status(self) -> Optional[Dict[str, Any]]:
        """
        Get git status information if in a git repository.
        
        Returns:
            A dictionary with git status info, or None if not in a git repo
        """
        # Check if git is installed
        if not shutil.which('git'):
            return None
        
        # Check if current directory is a git repository
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0 or result.stdout.strip() != 'true':
                return None
        except Exception:
            return None

        # Getting git status information
        git_info = {}
        
        # Get current branch
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                git_info['branch'] = result.stdout.strip()
        except Exception:
            git_info['branch'] = 'unknown'
        
        # Get status summary
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                status_lines = result.stdout.splitlines()
                git_info['changed_files'] = len(status_lines)
                
                # Count by status type
                status_counts = {
                    'modified': 0,
                    'added': 0,
                    'deleted': 0,
                    'untracked': 0,
                }
                
                for line in status_lines:
                    if line.startswith(' M') or line.startswith('M '):
                        status_counts['modified'] += 1
                    elif line.startswith('A '):
                        status_counts['added'] += 1
                    elif line.startswith(' D') or line.startswith('D '):
                        status_counts['deleted'] += 1
                    elif line.startswith('??'):
                        status_counts['untracked'] += 1
                    
                git_info['status_counts'] = status_counts
        
        except Exception:
            git_info['changed_files'] = 0
            
        return git_info

    def get_environment_info(self) -> Dict[str, str]:
        """
        Get relevant environment variables.
        
        Returns:
            A dictionary with environment information
        """
        # Collect environment variables that might be relevant
        # but exclude potentially sensitive ones
        safe_vars = [
            'PATH', 'SHELL', 'TERM', 'LANG', 'LC_ALL', 
            'HOME', 'USER', 'HOSTNAME', 'PWD'
        ]
        
        env_info = {}
        for var in safe_vars:
            value = os.environ.get(var)
            if value:
                env_info[var] = value
                
        return env_info
    
    def to_string(self) -> str:
        """
        Convert the context to a formatted string for inclusion in prompts.
        
        Returns:
            A formatted string representation of the context
        """
        
        context = self.get_context()
        
        # Build a human-readable representation
        lines = [
            "SYSTEM CONTEXT:",
            f"OS: {context['os']}",
            f"Current Directory: {context['cwd']}",
            "",
            "Recent Files:",
        ]
        
        # Add file information
        for file in context['files'][:5]:  # Limit to 5 files to keep context concise
            if 'name' in file:
                file_type = file['type'][0].upper()  # 'D' for directory, 'F' for file
                lines.append(f"  [{file_type}] {file['name']}")
        
        if len(context['files']) > 5:
            lines.append(f"  ... and {len(context['files']) - 5} more files")
            
        lines.append("")
        
        # Add command history
        lines.append("Recent Commands:")
        for cmd in context['history']:
            lines.append(f"  $ {cmd}")
            
        # Add git information if available
        if context['git_status']:
            lines.append("")
            lines.append("Git Status:")
            lines.append(f"  Branch: {context['git_status'].get('branch', 'unknown')}")
            
            if 'changed_files' in context['git_status']:
                lines.append(f"  Changed Files: {context['git_status']['changed_files']}")
                
            if 'status_counts' in context['git_status']:
                counts = context['git_status']['status_counts']
                status_str = ", ".join([
                    f"{count} {status}"
                    for status, count in counts.items()
                    if count > 0
                ])
                if status_str:
                    lines.append(f"  Changes: {status_str}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the context to a dictionary for JSON serialization.
        
        Returns:
            A dictionary representation of the context
        """
        return self.get_context()