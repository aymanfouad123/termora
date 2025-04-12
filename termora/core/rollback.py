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
    
    def rollback_last(self) -> bool:
        """
        Rollback the last operation.
        
        Returns:
            True if rollback was successful, False otherwise
        """
        # Get last execution info
        last_execution = self.get_last_execution()
        
        if not last_execution:
            self.console.print("[yellow]No previous execution found to rollback.[/yellow]")
            return False
        
        backup_path = last_execution.get("backup_path")
        if not backup_path or not os.path.exists(backup_path):
            self.console.print("[red]Backup file not found for the last execution.[/red]")
            return False
        
        # Perform the rollback
        self.console.print(f"[blue]Rolling back last operation using backup: {backup_path}[/blue]")
        result = self._restore_from_backup(backup_path)
        
        if result:
            self.console.print("[green]Rollback completed successfully.[/green]")
        else:
            self.console.print("[red]Rollback failed.[/red]")
            
        return result
    
    def rollback_specific(self, backup_id: str) -> bool:
        """
        Rollback to a specific backup.
        
        Args:
            backup_id: ID of the backup to restore
            
        Returns:
            True if rollback was successful, False otherwise
        """
        # Find the backup file
        backup_path = self.backup_dir / backup_id
        
        if not backup_path.exists():
            self.console.print(f"[red]Backup file not found: {backup_id}[/red]")
            return False
        
        # Perform the rollback
        self.console.print(f"[blue]Rolling back using backup: {backup_path}[/blue]")
        result = self._restore_from_backup(str(backup_path))
        
        if result:
            self.console.print("[green]Rollback completed successfully.[/green]")
        else:
            self.console.print("[red]Rollback failed.[/red]")
            
        return result
    
    def _restore_from_backup(self, backup_path: str) -> bool:
        """
        Restore files from a backup archive.
        
        Args:
            backup_path: Path to the backup archive
            
        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            # Create a temporary directory to extract the backup
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract the backup
                self.console.print("[blue]Extracting backup...[/blue]")
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(path=temp_path)
                
                # Restore files from the extracted backup
                self.console.print("[blue]Restoring files...[/blue]")
                
                # Count total files for progress bar
                file_count = sum(1 for _ in temp_path.glob("**/*") if _.is_file())
                
                with Progress() as progress:
                    restore_task = progress.add_task("[green]Restoring...", total=file_count)
                    
                    for source_path in temp_path.glob("**/*"):
                        if source_path.is_file():
                            # Compute the target path (absolute path from root)
                            # This removes the temp directory prefix /tmp/tmpdir123/home/user/documents/important.txt becomes home/user/documents/important.txt
                            rel_path = source_path.relative_to(temp_path)
                            target_path = Path("/") / rel_path
                            
                            # Create parent directories if needed
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Copy the file
                            shutil.copy2(source_path, target_path)
                            
                            # Update progress
                            progress.update(restore_task, advance=1)
                self.console.print("[green]Restoration complete.[/green]")
                return True
                
        except Exception as e:
            self.console.print(f"[red]Error during rollback: {str(e)}[/red]")
            return False