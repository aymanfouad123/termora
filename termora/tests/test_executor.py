"""
Tests for the command executor module.

This module contains tests for the CommandExecutor class in termora.core.executor.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Import the class we want to test
from termora.core.executor import CommandExecutor

# Import the ActionPlan class
from termora.core.agent import ActionPlan


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files."""
    # Create a temporary directory
    dir_path = tempfile.mkdtemp()
    
    # Create test files
    test_file1 = Path(dir_path) / "test_file1.txt"
    test_file2 = Path(dir_path) / "test_file2.txt"
    
    with open(test_file1, "w") as f:
        f.write("Test content 1")
    
    with open(test_file2, "w") as f:
        f.write("Test content 2")
    
    # Create a subdirectory with a file
    test_subdir = Path(dir_path) / "test_subdir"
    test_subdir.mkdir()
    
    with open(test_subdir / "subdir_file.txt", "w") as f:
        f.write("Subdirectory file content")
    
    # Yield the directory path for the tests to use
    yield dir_path
    
    # Clean up after the tests
    shutil.rmtree(dir_path)


@pytest.fixture
def executor():
    """Create a CommandExecutor instance for testing."""
    return CommandExecutor(auto_confirm=True, debug=True)


def test_display_plan(executor):
    """Test that display_plan correctly formats a command plan."""
    # Create a simple command plan
    plan = ActionPlan(
        explanation="Test explanation",
        actions=[
            {
                "type": "shell_command",
                "content": "echo 'hello'",
                "explanation": "Print hello"
            },
            {
                "type": "shell_command",
                "content": "ls -la",
                "explanation": "List files"
            }
        ],
        requires_backup=False
    )
    
    # Mock the console to capture output
    with patch.object(executor, 'console') as mock_console:
        executor.display_plan(plan)
        
        # Check that console.print was called with expected arguments
        mock_console.print.assert_any_call("\n[bold green] Termora Plan:[/bold green]")
        
        # Check if the plan explanation was created
        explanation_panel_found = False
        for call_args in mock_console.print.call_args_list:
            args, kwargs = call_args
            if args and hasattr(args[0], 'title') and args[0].title == "[bold]Explanation[/bold]":
                explanation_panel_found = True
                break
        
        assert explanation_panel_found, "Explanation panel not found in output"


def test_confirm_execution_auto(executor):
    """Test that auto_confirm works correctly."""
    plan = ActionPlan(
        explanation="Test explanation",
        actions=[
            {
                "type": "shell_command",
                "content": "echo 'hello'",
                "explanation": "Print hello"
            }
        ],
        requires_backup=False
    )
    
    # With auto_confirm=True, it should return True without asking
    assert executor.confirm_execution(plan) is True
    
    # Create another executor with auto_confirm=False, debug=True
    # In debug mode, it should return False without asking
    executor2 = CommandExecutor(auto_confirm=False, debug=True)
    assert executor2.confirm_execution(plan) is False


def test_create_backup(executor, temp_dir):
    """Test that create_backup correctly backs up files."""
    # Paths to back up
    paths = [
        str(Path(temp_dir) / "test_file1.txt"),
        str(Path(temp_dir) / "test_subdir")
    ]
    
    # Mock the console to prevent output
    with patch.object(executor, 'console'):
        # Call create_backup
        backup_path = executor.create_backup(paths)
        
        # Check that backup file exists
        assert os.path.exists(backup_path)
        
        # Check that it's a tar.gz file
        assert backup_path.endswith('.tar.gz')


def test_infer_backup_paths(executor, temp_dir):
    """Test that _infer_backup_paths correctly identifies paths from commands."""
    # Test commands with paths to extract
    commands = [
        f"rm -rf {temp_dir}/test_file1.txt",
        f"mv {temp_dir}/test_file2.txt {temp_dir}/new_file.txt",
        f"echo 'content' > {temp_dir}/output.txt",
        f"sed -i 's/old/new/g' {temp_dir}/test_subdir/subdir_file.txt"
    ]
    
    # Call _infer_backup_paths
    backup_paths = executor._infer_backup_paths(commands)
    
    # Check that all expected paths are in the result
    expected_paths = [
        f"{temp_dir}/test_file1.txt",
        f"{temp_dir}/test_file2.txt",
        f"{temp_dir}/output.txt",
        f"{temp_dir}/test_subdir/subdir_file.txt"
    ]

    for path in expected_paths:
        assert path in backup_paths


def test_execute_plan_debug_mode(executor, temp_dir):
    """Test that execute_plan in debug mode doesn't run commands."""
    # Create a command plan
    plan = ActionPlan(
        explanation="Test explanation",
        actions=[
            {
                "type": "shell_command",
                "content": f"rm -rf {temp_dir}/test_file1.txt",
                "explanation": "Remove a file"
            }
        ],
        requires_backup=True,
        backup_paths=[f"{temp_dir}/test_file1.txt"]
    )
    
    # Mock the console to prevent output
    with patch.object(executor, 'console'):
        # Execute the plan in debug mode
        result = executor.execute_plan(plan)
        
        # Check that execution was marked as not executed
        assert result["executed"] is False
        assert result["reason"] == "Debug mode"
        
        # Check that the file still exists (command wasn't actually run)
        assert os.path.exists(f"{temp_dir}/test_file1.txt")


@patch('subprocess.run')
def test_execute_plan_success(mock_run, temp_dir):
    """Test that execute_plan correctly executes commands."""
    # Mock subprocess.run to return success
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "Command output"
    mock_process.stderr = ""
    mock_run.return_value = mock_process
    
    # Creating a command plan with a non-destructive command
    plan = ActionPlan(
        explanation="Test explanation",
        actions=[
            {
                "type": "shell_command",
                "content": f"echo 'Test'",
                "explanation": "Print a test message"
            }
        ],
        requires_backup=False
    )
    
    # Create executor with auto_confirm and without debug mode
    executor = CommandExecutor(auto_confirm=True, debug=False)
    
    # Mock the console to prevent output
    with patch.object(executor, 'console'):
        # Execute the plan
        result = executor.execute_plan(plan)
        
        # Check that execution was marked as executed
        assert result["executed"] is True
        
        # Check that subprocess.run was called with the command
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs['shell'] is True
        
        # Check that output was captured
        assert result["outputs"][0]["stdout"] == "Command output"
        assert result["outputs"][0]["return_code"] == 0
        assert result["outputs"][0]["success"] is True