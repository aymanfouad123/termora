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
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List available backups.
        
        Returns:
            A list of backup information dictionaries
        """
        backups = []
        
        for backup_file in self.backup_dir.glob("backup_*.tar.gz"):
            try:
                # Extract timestamp
                filename = backup_file.name
                if filename.startswith("backup_") and filename.endswith(".tar.gz"):
                    timestamp_str = filename[7:-7]      # Slicing timestamp from filename 
                    
                    # Try to parse the timestamp
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        formatted_time = "Unknown"
                    
                    # Get file size 
                    size_bytes = os.path.getsize(backup_file)
                    size_mb = size_bytes / (1024 * 1024)
                    
                    backups.append({
                        "id": filename,
                        "path": str(backup_file),
                        "timestamp": formatted_time,
                        "size_mb": round(size_mb, 2)
                    })
            
            except Exception as e:
                # Skip problematic backups
                self.console.print(f"[yellow]Error processing backup {backup_file}: {str(e)}[/yellow]")
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups
    
    def display_backups(self):
        """Display available backups in a formatted table."""
        backups = self.list_backups()
        
        if not backups:
            self.console.print("[yellow]No backups found.[/yellow]")
            return
        
        # Create a table
        table = Table(title="Available Backups")
        table.add_column("ID", style="cyan")
        table.add_column("Date & Time", style="green")
        table.add_column("Size", style="blue")
        
        # Add rows
        for backup in backups:
            table.add_row(
                backup["id"],
                backup["timestamp"],
                f"{backup['size_mb']} MB"
            )
        
        self.console.print(table)
    
    def save_execution_history(self, execution_info: Dict[str, Any]):
        """
        Save execution information to history file.
        
        Args:
            execution_info: Information about the executed commands
        """
        history = []
        
        # Load existing history
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                # If file is corrupted, start with empty history
                history = []
        
        # Add new execution info
        history.append({
            "timestamp": get_timestamp(),
            "commands": execution_info.get("commands", []),
            "backup_path": execution_info.get("backup_path"),
            "success": all(output.get("success", False) for output in execution_info.get("outputs", []))
        })
        
        # Keep only the latest 20 entries
        history = history[-20:]
        
        # Save updated history
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)
    
    def get_last_execution(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the last execution.
        
        Returns:
            Dictionary with last execution info, or None if no history
        """
        if not self.history_file.exists():
            return None
        
        try:
            with open(self.history_file, "r") as f:
                history = json.load(f)
                
            if not history:
                return None
                
            return history[-1]  # Return the latest entry
            
        except (json.JSONDecodeError, IndexError, FileNotFoundError):
            return None
        