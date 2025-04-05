"""
AI Agent module for Termora.

This module handles the core intelligence of Termora, managing the 
interaction with AI models to process natural language requests and 
generate executable command plans.
"""

import os
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import re
from dotenv import load_dotenv

# For AI model integration
import litellm
import requests

# Internal imports
from termora.core.context import TerminalContext

class CommandPlan:
    """
    Represents a structured plan of commands to be executed.
    
    This class encapsulates the AI's response as a structured plan with explanation, commands, and backup information.
    """
    
    def __init__(
        self,
        explanation: str,
        commands: List[str],
        requires_confirmation: bool = True,
        requires_backup: bool = False,
        backup_paths: Optional[List[str]] = None
    ):
        """
        Initialize a command plan.
        
        Args:
            explanation: Human-readable explanation of what the commands will do
            commands: List of shell commands to execute
            requires_confirmation: Whether user confirmation is needed
            requires_backup: Whether files should be backed up before execution
            backup_paths: Paths to back up if requires_backup is True
        """
        self.explanation = explanation
        self.commands = commands
        self.requires_confirmation = requires_confirmation
        self.requires_backup = requires_backup
        self.backup_paths = backup_paths or []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the command plan to a dictionary for serialization.
        
        Returns:
            A dictionary representation of the command plan
        """
        return {
            "explanation": self.explanation,
            "commands": self.commands,
            "requires_confirmation": self.requires_confirmation,
            "requires_backup": self.requires_backup,
            "backup_paths": self.backup_paths
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandPlan':
        """
        Create a command plan from a dictionary.
        
        Args:
            data: Dictionary containing command plan information
            
        Returns:
            A CommandPlan instance
        """
        return cls(
            explaination = data.get("explanation", ""),
            commands = data.get("commands", []),
            requires_confirmation = data.get("requires_confirmation", True),
            requires_backup=data.get("requires_backup", False),
            backup_paths=data.get("backup_paths", [])
        )