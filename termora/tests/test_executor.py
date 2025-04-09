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
        
    def test_display_plan(self):
        """Test that display_plan correctly formats a command plan."""
        # Create a simple command plan
        plan = CommandPlan(
            explanation="Test explanation",
            commands=["echo 'hello'", "ls -la"],
            requires_backup=False
        )
        
        # Mock the console to capture output
        with patch.object(self.executor, 'console') as mock_console:
            self.executor.display_plan(plan)
            
            # Check that console.print was called with expected arguments
            mock_console.print.assert_any_call("\n[bold green] Termora Plan:[/bold green]")
            
            # Since we can't easily check the exact panel content we can check if the plan explanation was created
            for call_args in mock_console.print.call_args_list:
                args, kwargs = call_args
                if args and hasattr(args[0], 'title') and args[0].title == "[bold]Explanation[/bold]":
                    self.assertTrue(True)  # Found explanation panel
                    break
            else:
                self.fail("Explanation panel not found in output")
        
    def test_confirm_execution_auto(self):
        """Test that auto_confirm works correctly."""
        plan = CommandPlan(
            explaination="Test explaination",
            commands=["echo 'hello'"],
            requires_backup=False
        )
        
        # With auto_confirm=True, it should return True without asking
        self.assertTrue(self.executor.confirm_execution(plan))
    
        # Create another executor with auto_confirm=False, debug=True
        # In debug mode, it should return False without asking
        
        executor2 = CommandExecutor(auto_confirm=False, debug=True)
        self.assertFalse(executor2.confirm_execution(plan))
        
    def test_create_backup(self):
        """Test that create_backup correctly backs up files."""
        # Paths to back up
        paths = [
            str(Path(self.temp_dir) / "test_file1.txt"),
            str(Path(self.temp_dir) / "test_subdir")
        ]
        
        # Mock the console to prevent output
        with patch.object(self.executor, 'console'):
            # Call create_backup
            backup_path = self.executor.create_backup(paths)
            
            # Check that backup file exists
            self.assertTrue(os.path.exists(backup_path))
            
            # Check that it's a tar.gz file
            self.assertTrue(backup_path.endswith('.tar.gz'))
    
    def test_infer_backup_paths(self):
        """Test that _infer_backup_paths correctly identifies paths from commands."""
        # Test commands with paths to extract
        commands = [
            f"rm -rf {self.temp_dir}/test_file1.txt",
            f"mv {self.temp_dir}/test_file2.txt {self.temp_dir}/new_file.txt",
            f"echo 'content' > {self.temp_dir}/output.txt",
            f"sed -i 's/old/new/g' {self.temp_dir}/test_subdir/subdir_file.txt"
        ]
        
        # Call _infer_backup_paths
        backup_paths = self.executor._infer_backup_paths(commands)
        
        # Check that all expected paths are in the result
        expected_paths = [
            f"{self.temp_dir}/test_file1.txt",
            f"{self.temp_dir}/test_file2.txt",
            f"{self.temp_dir}/output.txt",
            f"{self.temp_dir}/test_subdir/subdir_file.txt"
        ]

        for path in expected_paths:
            self.assertIn(path, backup_paths)
    
    def test_execute_plan_debug_mode(self):
        """Test that execute_plan in debug mode doesn't run commands."""
        # Create a command plan
        plan = CommandPlan(
            explanation="Test explanation",
            commands=[f"rm -rf {self.temp_dir}/test_file1.txt"],
            requires_backup=True,
            backup_paths=[f"{self.temp_dir}/test_file1.txt"]
        )
        
        # Mock the console to prevent output
        with patch.object(self.executor, 'console'):
            # Execute the plan in debug mode
            result = self.executor.execute_plan(plan)
            
            # Check that execution was marked as not executed
            self.assertFalse(result["executed"])
            self.assertEqual(result["reason"], "Debug mode")
            
            # Check that the file still exists (command wasn't actually run)
            self.assertTrue(os.path.exists(f"{self.temp_dir}/test_file1.txt"))
    
        