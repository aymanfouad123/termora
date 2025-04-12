"""
Tests for the rollback module.

This module contains tests for the RollbackManager class in termora.core.rollback.
"""

import os
import json
import tempfile
import tarfile
import shutil
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

from termora.core.rollback import RollbackManager


class TestRollbackManager(unittest.TestCase):
    """Test case for RollbackManager class."""
    
    def setUp(self):
        """Set up a temporary test environment before each test."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create a mock termora directory in the temp directory
        self.mock_termora_dir = self.temp_path / ".termora"
        self.mock_backup_dir = self.mock_termora_dir / "backups"
        self.mock_backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a sample backup file
        self.sample_backup_path = self.create_sample_backup()
        
        # Create a sample history file
        self.mock_history_file = self.mock_termora_dir / "execution_history.json"
        self.create_sample_history()
        
        # Create the rollback manager with a patch to use our test directories
        with patch('termora.utils.helpers.get_termora_dir', return_value=self.mock_termora_dir):
            self.manager = RollbackManager()
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def create_sample_backup(self):
        """Create a sample backup archive for testing."""
        # Create some test files to back up
        test_content_dir = self.temp_path / "test_content"
        test_content_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a few test files with content
        (test_content_dir / "file1.txt").write_text("Test file 1 content")
        (test_content_dir / "file2.txt").write_text("Test file 2 content")
    
        # Create a subdirectory with a file
        test_subdir = test_content_dir / "subdir"
        test_subdir.mkdir(parents=True, exist_ok=True)
        (test_subdir / "file3.txt").write_text("Test file 3 in subdirectory")
        
        # Create a backup archive
        backup_path = self.mock_backup_dir / "backup_20230101_120000.tar.gz"

        with tarfile.open(backup_path, "w:gz") as tar:
            # Add files to the archive with their full paths
            tar.add(test_content_dir, arcname=str(test_content_dir.relative_to(self.temp_path)))
        
        return backup_path
    
    def create_sample_history(self):
        """Create a sample execution history file."""
        history = [
            {
                "timestamp": "2023-01-01 12:00:00",
                "commands": ["echo 'test'", "mkdir -p /tmp/test"],
                "backup_path": str(self.sample_backup_path),
                "success": True
            }
        ]
        
        with open(self.mock_history_file, "w") as f:
            json.dump(history, f, indent=2)
    
    def test_list_backups(self):
        """Test that list_backups correctly identifies backup files."""
        # Call list_backups
        backups = self.manager.list_backups()
        
        # Check that the sample backup was found
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0]["id"], "backup_20230101_120000.tar.gz")
        self.assertEqual(backups[0]["timestamp"], "2023-01-01 12:00:00")
    
    def test_get_last_execution(self):
        """Test that get_last_execution returns the last execution info."""
        # Call get_last_execution
        last_execution = self.manager.get_last_execution()
        
        # Check that the last execution was returned
        self.assertIsNotNone(last_execution)
        self.assertEqual(last_execution["timestamp"], "2023-01-01 12:00:00")
        self.assertEqual(last_execution["backup_path"], str(self.sample_backup_path))
    
    @patch('termora.core.rollback.RollbackManager._restore_from_backup')
    def test_rollback_last(self, mock_restore):
        """Test that rollback_last calls _restore_from_backup with the right path."""
        # Configure the mock to return True
        mock_restore.return_value = True
        
        # Call rollback_last
        result = self.manager.rollback_last()
        
        # Check that _restore_from_backup was called with the right path
        mock_restore.assert_called_once_with(str(self.sample_backup_path))
        self.assertTrue(result)
    
    @patch('termora.core.rollback.RollbackManager._restore_from_backup')
    def test_rollback_specific(self, mock_restore):
        """Test that rollback_specific calls _restore_from_backup with the right path."""
        # Configure the mock to return True
        mock_restore.return_value = True
        
        # Call rollback_specific
        backup_id = "backup_20230101_120000.tar.gz"
        result = self.manager.rollback_specific(backup_id)
        
        # Check that _restore_from_backup was called with the right path
        expected_path = str(self.mock_backup_dir / backup_id)
        mock_restore.assert_called_once_with(expected_path)
        self.assertTrue(result)
    
    def test_restore_from_backup(self):
        """Test that _restore_from_backup correctly restores files."""
        # Create a target directory where files will be restored
        target_dir = self.temp_path / "restore_target"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock the Path("/") to return our target directory instead
        with patch('pathlib.Path', return_value=target_dir) as mock_path:
            # Configuring mock_path to return target_dir when called with "/"
            def side_effect(path):
                if path == "/":
                    return target_dir
                return Path(path)
            mock_path.side_effect = side_effect
            
            # Call _restore_from_backup
            with patch.object(self.manager, 'console'):  # Suppress console output
                result = self.manager._restore_from_backup(str(self.sample_backup_path))
            
            # Check that restoration was successful
            self.assertTrue(result)
            
            # Check that files were restored correctly
            restored_content_dir = target_dir / "test_content"
            self.assertTrue((restored_content_dir / "file1.txt").exists())
            self.assertTrue((restored_content_dir / "file2.txt").exists())
            self.assertTrue((restored_content_dir / "subdir" / "file3.txt").exists())
            
            # Check file contents
            self.assertEqual((restored_content_dir / "file1.txt").read_text(), "Test file 1 content")
            self.assertEqual((restored_content_dir / "file2.txt").read_text(), "Test file 2 content")
            self.assertEqual((restored_content_dir / "subdir" / "file3.txt").read_text(), "Test file 3 in subdirectory")

if __name__ == "__main__":
    unittest.main()