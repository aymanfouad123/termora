"""
Rollback module for Termora.

This module handles restoring from backups created during command execution,
allowing users to undo potentially destructive operations.
"""

import os
import json
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from termora.utils.helpers import get_termora_dir, get_timestamp

class RollbackManager:
    """
    Manages backup and rollback operations.
    
    This class is responsible for restoring files from backups
    and managing the backup history.
    """
    
    def __init__(self):
        """Initialize the rollback manager."""
        self.console = Console(),
        self.termora_dir = get_termora_dir()
        self.backup_dir = self.termora_dir / "backups"
        self.history_file = self.termora_dir / "execution_history.json"
        
        # Ensure directories exist
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    