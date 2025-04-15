"""
History management module for Termora.

This module handles tracking, storing, and analyzing command history with rich context
to enable Termora's temporal intelligence features.
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from termora.utils.helpers import get_termora_dir, get_timestamp


class HistoryManager:
    """
    Manages command history with rich context metadata.
    
    This class is responsible for:
    1. Recording commands with their execution context
    2. Storing and retrieving history
    3. Analyzing patterns in command usage
    4. Providing context-aware search capabilities
    """
    
    def __init__(self):
        """Initialize the history manager."""
        # Get the termora directory (reusing the utility from the rollback manager)
        self.termora_dir = get_termora_dir()
        
        # Define paths for history storage
        self.history_dir = self.termora_dir / "history"
        self.history_file = self.history_dir / "command_history.json"
        
        # Create directories if they don't exist
        self._ensure_directories()
        
        # Load existing history or initialize empty history
        self.history = self._load_history()
    
    def _ensure_directories(self):
        """Ensure that required directories exist."""
        if not self.history_dir.exists():
            self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """
        Load command history from file or initialize if it doesn't exist.
        
        Returns:
            List of command history entries
        """
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # If file is corrupted or doesn't exist, return empty history
            return []
    
    def _save_history(self):
        """Save command history to file."""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)
    
    def add_command(self, command: str, directory: str, output: str = "", exit_code: int = 0, duration: float = 0.0) -> Dict[str, Any]:
        """
        Add a command to the history with context metadata.
        
        Args:
            command: The command string that was executed
            directory: The working directory where the command was run
            output: The command's output (optional)
            exit_code: The command's exit code (optional)
            duration: How long the command took to execute in seconds (optional)
            
        Returns:
            The newly created history entry
        """
        
        # Create entry with rich metadata
        entry = {
            "command": command,
            "directory": directory,
            "timestamp": get_timestamp(),
            "unix_timestamp": time.time(),
            "output": output[:1000] if output else "",  # Limit output size
            "exit_code": exit_code,
            "duration": duration
        }
        
        # Add additional context if available
        entry["context"] = self._gather_command_context(command, directory)
        
        # Add to history and save
        self.history.append(entry)
        self._save_history()
        
        return entry
    
    def _gather_command_context(self, command: str, directory: str) -> Dict[str, Any]:
        """
        Gather additional context about the command and environment.
        
        Args:
            command: The command being executed
            directory: The working directory
            
        Returns:
            Dict with context information
        """
        # This will be expanded later with more sophisticated context gathering
        context = {
            "project": self._detect_project(directory),
            "files_affected": [],  # Will be populated later
            "command_type": self._categorize_command(command)
        }
        
        return context
    
    def _detect_project(self, directory: str) -> Optional[str]:
        """
        Attempt to detect which project the directory belongs to.
        
        Args:
            directory: Directory path
            
        Returns:
            Project name if detected, None otherwise
        """
        
        # Simple project detection based on common project files
        dir_path = Path(directory)
        
        # Look for git repository
        git_dir = dir_path / ".git"
        if git_dir.exists():
            # Try to get repository name from config
            git_config = dir_path / ".git" / "config"
            if git_config.exists():
                try:
                    with open(git_config, "r") as f:
                        for line in f:
                            if "url = " in line:
                                # Extract repo name from URL
                                url = line.split("url = ")[1].strip()
                                repo_name = url.split("/")[-1].replace(".git", "")
                                return repo_name
                except:
                    pass
            
            # Fallback to directory name
            return dir_path.name
        
        # Check for other project indicators
        if (dir_path / "package.json").exists():
            return f"{dir_path.name} (Node.js)"
        
        if (dir_path / "requirements.txt").exists() or (dir_path / "setup.py").exists():
            return f"{dir_path.name} (Python)"
            
        # No project detected
        return None