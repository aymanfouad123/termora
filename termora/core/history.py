"""
History management module for Termora.

This module handles tracking, storing, and analyzing command history with rich context 
to enable Termora's temporal intelligence features.

Key functionality:
- HistoryManager: Main class for tracking and analyzing command history
- Command history management (REPL history)
- Action history tracking
- History search and analysis
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
    3. Analyzing patterns in usage
    4. Providing context-aware search capabilities
    5. Managing REPL command history
    """
    
    def __init__(self):
        """Initialize the history manager."""
        # Get the termora directory
        self.termora_dir = get_termora_dir()
        
        # Define paths for history storage
        self.history_dir = self.termora_dir / "history"
        self.history_file = self.history_dir / "command_history.json"
        self.repl_history_file = self.termora_dir / "repl_history.json"
        
        # Create directories if they don't exist
        self._ensure_directories()
        
        # Load existing history or initialize empty history
        self.history = self._load_history()
        self.repl_history = self._load_repl_history()
    
    def _ensure_directories(self):
        """Ensure that required directories exist."""
        if not self.termora_dir.exists():
            self.termora_dir.mkdir(parents=True, exist_ok=True)
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
    
    def _load_repl_history(self) -> List[str]:
        """Load REPL command history from file."""
        if not self.repl_history_file.exists():
            return []
            
        try:
            with open(self.repl_history_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_repl_history(self) -> None:
        """Save REPL command history to file."""
        try:
            # Keep only the latest 1000 commands
            history_to_save = self.repl_history[-1000:] if len(self.repl_history) > 1000 else self.repl_history
            
            with open(self.repl_history_file, 'w') as f:
                json.dump(history_to_save, f)
        except IOError as e:
            print(f"Warning: Could not save REPL history: {str(e)}")
    
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
        
        # Create entry with rich metadata context
        entry = {
            "action_type": "shell_command",  # Specifing this is a shell command for compatibility
            "command": command,
            "directory": directory,
            "timestamp": get_timestamp(),
            "unix_timestamp": time.time(),
            "output": output[:1000] if output else "",  # Limiting output size
            "exit_code": exit_code,
            "duration": duration
        }
        
        # Add additional context if available
        entry["context"] = self._gather_command_context(command, directory)
        
        # Add to history and save
        self.history.append(entry)
        self._save_history()
        
        return entry
    
    def add_python_execution(self, code: str, directory: str, output: str = "", exit_code: int = 0, duration: float = 0.0) -> Dict[str, Any]:
        """
        Add a Python code execution to the history with context metadata.
        
        Args:
            code: The Python code that was executed
            directory: The working directory where the code was run
            output: The code's output (optional)
            exit_code: The code's exit code (optional)
            duration: How long the execution took in seconds (optional)
            
        Returns:
            The newly created history entry
        """

        entry = {
            "action_type": "python_code",  # Specifing this is Python code
            "code": code[:2000],  # Limiting the code size
            "directory": directory,
            "timestamp": get_timestamp(),
            "unix_timestamp": time.time(),
            "output": output[:1000] if output else "",  # Limiting output size
            "exit_code": exit_code,
            "duration": duration
        }
        
        entry["context"] = self._gather_python_context(code, directory)
        
        self.history.append(entry)
        self._save_history()
        
        return entry
    
    def add_action_plan(self, plan, results: Dict[str, Any], directory: str) -> Dict[str, Any]:
        """
        Add a complete ActionPlan execution to history.
        
        Args:
            plan: The ActionPlan that was executed
            results: The execution results
            directory: The working directory
            
        Returns:
            The newly created history entry
        """
        
        # Creating an entry for the overall action plan
        entry = {
            "action_type": "action_plan",
            "explanation": plan.explanation,
            "directory": directory,
            "timestamp": get_timestamp(),
            "unix_timestamp": time.time(),
            "actions": plan.actions,
            "success": results.get("executed", False) and all(
                output.get("success", False) for output in results.get("outputs", [])
            ),
            "backup_path": results.get("backup_path")
        }
        
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
    
    def _gather_python_context(self, code: str, directory: str) -> Dict[str, Any]:
        """
        Gather additional context about Python code execution.
        
        Args:
            code: The Python code being executed
            directory: The working directory
            
        Returns:
            Dict with context information
        """
        # Basic context for Python code
        context = {
            "project": self._detect_project(directory),
            "files_affected": [],  # Will be populated later
            "imports": self._extract_python_imports(code),
            "code_type": self._categorize_python_code(code)
        }
        
        return context
    
    def _extract_python_imports(self, code: str) -> List[str]:
        """Extract import statements from Python code."""
        imports = []
        
        # Very simple approach - will need improvement for complex imports
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
                
        return imports
    
    def _categorize_python_code(self, code: str) -> str:
        """Categorize Python code by type/purpose."""
        code_lower = code.lower()
        
        if 'import os' in code_lower and ('open(' in code_lower or 'os.path' in code_lower):
            return "file_operation"
        elif 'import requests' in code_lower or 'urllib' in code_lower:
            return "networking"
        elif 'import pandas' in code_lower or 'numpy' in code_lower or 'matplotlib' in code_lower:
            return "data_analysis"
        elif 'subprocess' in code_lower:
            return "system_command"
        else:
            return "general"
    
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
    
    def _categorize_command(self, command: str) -> str:
        """
        Categorize a command by type.
        
        Args:
            command: The command string
            
        Returns:
            Command category as string
        """
        
        # This is a simple categorization that will be expanded later
        command = command.strip().split()[0] if command.strip() else ""
        
        # Common command categories
        if command in ["git", "svn", "hg"]:
            return "version_control"
        elif command in ["cd", "ls", "dir", "pwd", "mv", "cp", "rm"]:
            return "filesystem"
        elif command in ["python", "python3", "pip", "pipenv", "venv"]:
            return "python_dev"
        elif command in ["npm", "yarn", "node"]:
            return "node_dev"
        elif command in ["docker", "docker-compose", "kubectl"]:
            return "container"
        else:
            return "other"
        
    def search_history(self, query: str = "", 
                      directory: Optional[str] = None,
                      limit: int = 10,
                      action_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search command history with filtering.
        
        Args:
            query: Search term to find in commands or code
            directory: Filter by directory
            limit: Maximum number of results
            action_type: Filter by action type (shell_command, python_code, action_plan)
            
        Returns:
            List of matching history entries
        """
        results = []
        
        for entry in reversed(self.history):  # Most recent first
            # Check action type filter
            if action_type and entry.get("action_type") != action_type:
                continue
                
            # Apply content filters based on action type
            entry_type = entry.get("action_type", "shell_command")
            
            if query:
                if entry_type == "shell_command" and query.lower() not in entry.get("command", "").lower():
                    continue
                elif entry_type == "python_code" and query.lower() not in entry.get("code", "").lower():
                    continue
                elif entry_type == "action_plan" and query.lower() not in entry.get("explanation", "").lower():
                    continue
                
            if directory and entry.get("directory") != directory:
                continue
            
            results.append(entry)
            
            if len(results) >= limit:
                break
                
        return results
    
    def get_command_patterns(self, directory: Optional[str] = None, action_type: str = "shell_command") -> List[Dict[str, Any]]:
        """
        Identify common command patterns in history.
        
        Args:
            directory: Optional directory to limit pattern analysis to
            action_type: Filter by action type
            
        Returns:
            List of command patterns with frequency information
        """
        # This is a placeholder for more sophisticated pattern analysis
        content_counts = {}
        
        for entry in self.history:
            # Skip if we're filtering by directory and this doesn't match
            if directory and entry.get("directory") != directory:
                continue
                
            # Skip if entry type doesn't match
            if entry.get("action_type") != action_type:
                continue
                
            if action_type == "shell_command":
                content = entry.get("command", "")
            elif action_type == "python_code":
                content = entry.get("code", "")[:50]  # First 50 chars as identifier
            else:
                continue
                
            # Count content occurrences
            if content in content_counts:
                content_counts[content] += 1
            else:
                content_counts[content] = 1
        
        # Convert to sorted list
        patterns = []
        for content, count in content_counts.items():
            item = {"count": count}
            if action_type == "shell_command":
                item["command"] = content
            elif action_type == "python_code":
                item["code"] = content
            patterns.append(item)
        
        # Sort by frequency (most frequent first)
        patterns.sort(key=lambda x: x["count"], reverse=True)
        
        return patterns[:10]  # Return top 10 patterns
    
    def add_repl_command(self, command: str) -> None:
        """
        Add a command to the REPL history.
        
        Args:
            command: The command string to add
        """
        self.repl_history.append(command)
        self._save_repl_history()
    
    def get_repl_history(self, limit: int = 1000) -> List[str]:
        """
        Get the REPL command history.
        
        Args:
            limit: Maximum number of commands to return
            
        Returns:
            List of recent commands
        """
        return self.repl_history[-limit:]
    
    def cleanup(self) -> None:
        """Perform cleanup operations when shutting down."""
        self._save_history()
        self._save_repl_history()