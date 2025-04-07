"""
Tests for the command executor module.

This module contains tests for the CommandExecutor class in termora.core.executor.
"""

import os
import tempfile
import shutil
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Import the class we want to test
from termora.core.executor import CommandExecutor

# Import the CommandPlan class
from termora.core.agent import CommandPlan

class TestCommandExecutor(unittest.TestCase):
    """Test case for CommandExecutor class."""
    
    def setUp(self):
        """Set up a temporary test environment before each test."""
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files
        test_file1 = Path(self.temp_dir) / "test_file1.txt"
        test_file2 = Path(self.temp_dir) / "test_file2.txt"
        
        with open(test_file1, "w") as f:
            f.write("Test content 1")
        
        with open(test_file2, "w") as f:
            f.write("Test content 2")
        
        # Create a subdirectory with a file
        test_subdir = Path(self.temp_dir) / "test_subdir"
        test_subdir.mkdir()
        
        with open(test_subdir / "subdir_file.txt", "w") as f:
            f.write("Subdirectory file content")
            
        # Create executor with auto_confirm for testing
        self.executor = CommandExecutor(auto_confirm=True, debug=True)
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)