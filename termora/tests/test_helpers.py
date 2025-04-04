"""
Tests for the utility helper functions.

This module contains tests for the helper functions in termora.utils.helpers.
"""

import os
import platform
import datetime
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Importing the functions we want to test
from termora.utils.helpers import (
    get_termora_dir,
    resolve_path,
    get_timestamp,
    get_system_info,
    is_destructive_command
)

class TestHelperFunctions(unittest.TestCase):
    """Test case for helper functions in termora.utils.helpers module."""

    def test_get_termora_dir(self):
        termora_dir = get_termora_dir()
        # Check that it returns a Path object
        self.assertIsInstance(termora_dir, Path)
        
        # Check that the directory exists
        self.assertTrue(termora_dir.exists())
        
        # Check that it's in the home directory
        self.assertTrue(str(termora_dir).startswith(str(Path.home())))
        
        # Check that it has the correct name
        self.assertEqual(termora_dir.name, ".termora")
        
    def test_resolve_path(self):
        """Test that resolve_path handles different path formats correctly."""
        # Check tilde expansion
        home_path = resolve_path("~/test")
        self.assertEqual(home_path, Path.home() / "test")
        
        # Checking relative path
        relative_path = resolve_path("./test")
        self.assertEqual(relative_path, Path.cwd() / "test")
        
        # Check absolute path
        abs_path_str = "/tmp/test" if platform.system() != "Windows" else "C:\\test"
        abs_path = resolve_path(abs_path_str)
        self.assertEqual(abs_path, Path(abs_path_str))
    
    def test_get_timestamp(self):
        """Test that get_timestamp returns correctly formatted string."""
        # Mock datetime to return a fixed date
        fixed_date = datetime.datetime(2023, 1, 1, 12, 0, 0)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_date
            
            # Test default format
            timestamp = get_timestamp()
            self.assertEqual(timestamp, "2023-01-01 12:00:00")
            
            # Test custom format
            custom_timestamp = get_timestamp("%Y/%m/%d")
            self.assertEqual(custom_timestamp, "2023/01/01")
        
    def test_get_system_info(self):
        """Test that get_system_info returns a dictionary with required keys."""
        info = get_system_info()
        
        # Check that it returns a dictionary
        self.assertIsInstance(info, dict)
        
        # Check that it contains all required keys
        required_keys = ["os", "os_version", "platform", "python_version", "hostname"]
        for key in required_keys:
            self.assertIn(key, info)

    def test_is_destructive_command(self):
        """Test that is_destructive_command correctly identifies dangerous commands."""
        # Test destructive commands
        self.assertTrue(is_destructive_command("rm -rf /"))
        self.assertTrue(is_destructive_command("mv /etc /tmp"))
        self.assertTrue(is_destructive_command("dd if=/dev/zero of=/dev/sda"))
        
        # Test safe commands
        self.assertFalse(is_destructive_command("ls -la"))
        self.assertFalse(is_destructive_command("cd /tmp"))
        self.assertFalse(is_destructive_command("echo 'hello world'"))
        
        # Test edge cases
        self.assertFalse(is_destructive_command("firmware update"))  # contains 'rm' but not as a command
        self.assertTrue(is_destructive_command("rm"))  # just the command itself

if __name__ == "__main__":
    unittest.main()