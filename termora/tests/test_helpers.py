"""
Tests for the utility helper functions.

This module contains tests for the helper functions in termora.utils.helpers.
"""

import os
import platform
import datetime
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Importing the functions we want to test
from termora.utils.helpers import (
    get_termora_dir,
    resolve_path,
    get_timestamp,
    get_system_info,
    is_destructive_command
)


def test_get_termora_dir():
    """Test that get_termora_dir returns the correct directory."""
    termora_dir = get_termora_dir()
    
    # Check that it returns a Path object
    assert isinstance(termora_dir, Path)
    
    # Check that the directory exists
    assert termora_dir.exists()
    
    # Check that it's in the home directory
    assert str(termora_dir).startswith(str(Path.home()))
    
    # Check that it has the correct name
    assert termora_dir.name == ".termora"


def test_resolve_path():
    """Test that resolve_path handles different path formats correctly."""
    # Check tilde expansion
    home_path = resolve_path("~/test")
    assert home_path == Path.home() / "test"
    
    # Checking relative path
    relative_path = resolve_path("./test")
    assert relative_path == Path.cwd() / "test"
    
    # Check absolute path
    abs_path_str = "/tmp/test" if platform.system() != "Windows" else "C:\\test"
    abs_path = resolve_path(abs_path_str)
    assert abs_path == Path(abs_path_str)


def test_get_timestamp():
    """Test that get_timestamp returns correctly formatted string."""
    # Mock datetime to return a fixed date
    fixed_date = datetime.datetime(2023, 1, 1, 12, 0, 0)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_date
        
        # Test default format
        timestamp = get_timestamp()
        assert timestamp == "2023-01-01 12:00:00"
        
        # Test custom format
        custom_timestamp = get_timestamp("%Y/%m/%d")
        assert custom_timestamp == "2023/01/01"


def test_get_system_info():
    """Test that get_system_info returns a dictionary with required keys."""
    info = get_system_info()
    
    # Check that it returns a dictionary
    assert isinstance(info, dict)
    
    # Check that it contains all required keys
    required_keys = ["os", "os_version", "platform", "python_version", "hostname"]
    for key in required_keys:
        assert key in info


def test_is_destructive_command():
    """Test that is_destructive_command correctly identifies dangerous commands."""
    # Test destructive commands
    assert is_destructive_command("rm -rf /") is True
    assert is_destructive_command("mv /etc /tmp") is True
    assert is_destructive_command("dd if=/dev/zero of=/dev/sda") is True
    
    # Test safe commands
    assert is_destructive_command("ls -la") is False
    assert is_destructive_command("cd /tmp") is False
    assert is_destructive_command("echo 'hello world'") is False
    
    # Test edge cases
    assert is_destructive_command("firmware update") is False  # contains 'rm' but not as a command
    assert is_destructive_command("rm") is True  # just the command itself