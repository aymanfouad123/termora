"""
Utility helper functions for Termora.

This module provides common utility functions used throughout the application
for tasks like path resolution, timestamp formatting, and system information.
"""

import os
import platform
import datetime
from pathlib import Path
from typing import Union, Optional

def get_termora_dir() -> Path:
    """
    Get the Termora configuration directory path.
    
    Creates ~/.termora directory if it doesn't exist.
    
    Returns:
        Path: The path to the Termora configuration directory
    """
    
    home_dir = Path.home()
    termora_dir = home_dir / ".termora"
    
    # Create directory if it doesn't exist
    if not termora_dir.exists():
        termora_dir.mkdir(parents=True, exist_ok=True)
    return termora_dir

def resolve_path(path_str: str) -> Path:
    """
    Resolve a path string to an absolute Path object.
    
    Handles tilde expansion for home directory and converts
    relative paths to absolute paths.
    
    Args:
        path_str: A string representing a file path
        
    Returns:
        Path: An absolute Path object
    """
    # Expanding ~ to home directory
    if path_str.startswith("~"):
        path_str = os.path.expanduser(path_str)
    
    # Converting to absolute path 
    return Path(path_str).absolute()

def get_timestamp(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Get a formatted timestamp string.
    
    Args:
        format_str: The datetime format string (default: "%Y-%m-%d %H:%M:%S")
        
    Returns:
        str: A formatted timestamp string
    """
    return datetime.datetime.now().strftime(format_str)
        
def get_system_info() -> dict:
    """
    Get basic system information.
    
    Returns:
        dict: A dictionary containing system information
    """
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "hostname": platform.node()
    }
    
def is_destructive_command(command: str) -> bool:
    """
    Check if a command is potentially destructive.
    
    Args:
        command: The command string to check
        
    Returns:
        bool: True if the command contains potentially destructive operations
    """
    # List of potentially destructive commands
    destructive_cmds = [
        "rm", "rmdir", "mv", "dd", "mkfs", "fdisk", "format",
        "shutdown", "reboot", "del", "truncate", ">", "tee", "sed" 
    ]
    
    # Check if any destructive command is present
    for cmd in destructive_cmds:
        # Match whole words to avoid false positives
        if f" {cmd} " in f" {command} " or command.startswith(f"{cmd} "):
            return True
            
    return False