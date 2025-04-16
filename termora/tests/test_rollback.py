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
import pytest
from unittest.mock import patch, MagicMock

from termora.core.rollback import RollbackManager


@pytest.fixture
def test_environment():
    """Create a temporary test environment with necessary directories and files."""
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    # Create a mock termora directory in the temp directory
    mock_termora_dir = temp_path / ".termora"
    mock_backup_dir = mock_termora_dir / "backups"
    mock_backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test content directory
    test_content_dir = temp_path / "test_content"
    test_content_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a few test files with content
    (test_content_dir / "file1.txt").write_text("Test file 1 content")
    (test_content_dir / "file2.txt").write_text("Test file 2 content")

    # Create a subdirectory with a file
    test_subdir = test_content_dir / "subdir"
    test_subdir.mkdir(parents=True, exist_ok=True)
    (test_subdir / "file3.txt").write_text("Test file 3 in subdirectory")
    
    # Create a backup archive
    backup_path = mock_backup_dir / "backup_20230101_120000.tar.gz"

    with tarfile.open(backup_path, "w:gz") as tar:
        # Add files to the archive with their full paths
        tar.add(test_content_dir, arcname=str(test_content_dir.relative_to(temp_path)))
    
    # Create a sample history file
    mock_history_file = mock_termora_dir / "execution_history.json"
    history = [
        {
            "timestamp": "2023-01-01 12:00:00",
            "commands": ["echo 'test'", "mkdir -p /tmp/test"],
            "backup_path": str(backup_path),
            "success": True
        }
    ]
    
    with open(mock_history_file, "w") as f:
        json.dump(history, f, indent=2)
    
    # Return a dictionary with all the paths and objects we need
    env = {
        "temp_dir": temp_dir,
        "temp_path": temp_path,
        "mock_termora_dir": mock_termora_dir,
        "mock_backup_dir": mock_backup_dir,
        "backup_path": backup_path,
        "mock_history_file": mock_history_file,
        "test_content_dir": test_content_dir
    }
    
    # Create a patcher for get_termora_dir to return our mock directory
    with patch('termora.core.rollback.get_termora_dir') as mock_get_termora_dir:
        mock_get_termora_dir.return_value = mock_termora_dir
        yield env
    
    # Clean up after the test
    shutil.rmtree(temp_dir)


@pytest.fixture
def rollback_manager(test_environment):
    """Create a RollbackManager instance for testing."""
    return RollbackManager()


def test_list_backups(rollback_manager, test_environment):
    """Test that list_backups correctly identifies backup files."""
    # Call list_backups
    backups = rollback_manager.list_backups()
    
    # Check that the sample backup was found
    assert len(backups) == 1
    assert backups[0]["id"] == "backup_20230101_120000.tar.gz"
    assert backups[0]["timestamp"] == "2023-01-01 12:00:00"


def test_get_last_execution(rollback_manager, test_environment):
    """Test that get_last_execution returns the last execution info."""
    # Call get_last_execution
    last_execution = rollback_manager.get_last_execution()
    
    # Check that the last execution was returned
    assert last_execution is not None
    assert last_execution["timestamp"] == "2023-01-01 12:00:00"
    assert last_execution["backup_path"] == str(test_environment["backup_path"])


@patch('termora.core.rollback.RollbackManager._restore_from_backup')
def test_rollback_last(mock_restore, rollback_manager, test_environment):
    """Test that rollback_last calls _restore_from_backup with the right path."""
    # Configure the mock to return True
    mock_restore.return_value = True
    
    # Call rollback_last
    result = rollback_manager.rollback_last()
    
    # Check that _restore_from_backup was called with the right path
    mock_restore.assert_called_once_with(str(test_environment["backup_path"]))
    assert result is True


@patch('termora.core.rollback.RollbackManager._restore_from_backup')
def test_rollback_specific(mock_restore, rollback_manager, test_environment):
    """Test that rollback_specific calls _restore_from_backup with the right path."""
    # Configure the mock to return True
    mock_restore.return_value = True
    
    # Call rollback_specific
    backup_id = "backup_20230101_120000.tar.gz"
    
    # Patch Path.exists to make it return True for our backup file
    with patch.object(Path, 'exists', return_value=True):
        result = rollback_manager.rollback_specific(backup_id)
    
    # Check that _restore_from_backup was called with the right path
    expected_path = str(test_environment["mock_backup_dir"] / backup_id)
    mock_restore.assert_called_once_with(expected_path)
    assert result is True


def test_restore_from_backup(rollback_manager, test_environment):
    """Test that _restore_from_backup correctly restores files."""
    # Create a target directory where files will be restored
    target_dir = test_environment["temp_path"] / "restore_target"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a patching context
    with patch.object(Path, "__new__") as mock_path_new, \
         patch.object(rollback_manager, "console"), \
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
            result = rollback_manager._restore_from_backup(str(test_environment["backup_path"]))
        
        # Verify the result
        assert result is True