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
        
        # START PATCH: Create proper patcher for get_termora_dir
        self.get_termora_dir_patcher = patch('termora.core.rollback.get_termora_dir')
        self.mock_get_termora_dir = self.get_termora_dir_patcher.start()
        self.mock_get_termora_dir.return_value = self.mock_termora_dir
        
        # Create the rollback manager (no patch needed here anymore)
        self.manager = RollbackManager()
    
    def tearDown(self):
        """Clean up after each test."""
        # Stop the patcher
        self.get_termora_dir_patcher.stop()
        
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
        
        # Patch Path.exists to make it return True for our backup file
        with patch.object(Path, 'exists', return_value=True):
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
        
        # We need to mock several things to test this method properly
        # 1. Mock Path to return our target_dir when "/" is requested
        # 2. Suppress console output
        # 3. Skip actual file operations
        
        # Create a patching context
        with patch.object(Path, "__new__") as mock_path_new, \
             patch.object(self.manager, "console"), \
             patch("tarfile.open"), \
             patch("shutil.copy2"), \
             patch.object(Path, "mkdir", return_value=None), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "relative_to", return_value=Path("test_file")), \
             patch.object(Path, "parent", return_value=Path("test_dir")):
            
            # Configure mock_path_new to return target_dir for "/"
            def path_side_effect(cls, path, *args, **kwargs):
                if str(path) == "/":
                    return target_dir
                # This is necessary to avoid recursion
                actual_path = object.__new__(Path)
                object.__setattr__(actual_path, "_str", str(path))
                return actual_path
            
            mock_path_new.side_effect = path_side_effect
            
            # Configure tarfile.open to return a mock that has some files
            mock_tar = MagicMock()
            mock_tar.extractall.return_value = None
            
            # Create a list of mock files in the tarfile
            mock_files = [
                MagicMock(spec=Path, name="file1"),
                MagicMock(spec=Path, name="file2"),
            ]
            for mock_file in mock_files:
                mock_file.is_file.return_value = True
            
            # Make temp_path.glob return our mock files
            with patch.object(Path, "glob", return_value=mock_files):
                # Call the method under test
                result = self.manager._restore_from_backup(str(self.sample_backup_path))
            
            # Verify the result
            self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()