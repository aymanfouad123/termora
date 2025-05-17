"""
Pipeline processing module for Termora.

This module implements a modular pipeline architecture for processing natural language requests,
extracting intent, generating plans, and coordinating execution with safety measures.

Key functionality:
- Intent: Data class representing extracted user intent
- TermoraPlan: Data class with complete plan and metadata
- TermoraPipeline: Orchestrates the processing flow from input to execution
- Intent extraction: Parse natural language into structured intents
- Plan generation: Create executable commands from intents
- Safety hand

The pipeline follows a clear sequence:
1. Input Parsing -> 2. Context Gathering -> 3. Intent Extraction -> 4. Plan Generation -> 5. Execution -> 6. History Logging
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import os
import json

@dataclass
class Intent:
    """Represents the extracted intent from user input."""
    action: str  # Primary action (move, find, count, etc.)
    target_dir: Optional[str] = None  # Target directory for operations
    file_filter: Optional[Dict[str, Any]] = None  # File selection criteria
    time_filter: Optional[Dict[str, Any]] = None  # Time-based constraints
    destination: Optional[str] = None  # Destination for move/copy operations
    limit: Optional[int] = None  # Result limit
    sort_by: Optional[str] = None  # Sorting criteria
    recursive: bool = True  # Whether to operate recursively

    def to_dict(self) -> Dict[str, Any]:
        """Convert intent to dictionary for serialization."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
@dataclass
class TermoraPlan:
    """Complete execution plan with all metadata."""
    user_input: str
    intent: Intent
    reasoning: str
    plan: List[Dict[str, Any]]  # List of action objects
    preview: Dict[str, str]
    requires_backup: bool = False
    backup_paths: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary for serialization."""
        return {
            "user_input": self.user_input,
            "intent": self.intent.to_dict(),
            "reasoning": self.reasoning,
            "plan": self.plan,
            "preview": self.preview,
            "requires_backup": self.requires_backup,
            "backup_paths": self.backup_paths or []
        }
        