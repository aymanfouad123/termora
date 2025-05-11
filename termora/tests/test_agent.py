"""
Tests for the agent module.

This module contains tests for the TermoraAgent class in termora.core.agent.py
"""

import pytest
import json
import sys
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from termora.core.agent import TermoraAgent, ActionPlan


@pytest.fixture
def agent():
    """Create a TermoraAgent instance for testing."""
    return TermoraAgent({"send_to_api": False})  # Use offline mode for tests

@pytest.fixture
def online_agent():
    """Create a TermoraAgent instance with API enabled for testing."""
    return TermoraAgent({"send_to_api": True, "ai_provider": "groq", "ai_model": "llama3-70b-8192"})


@pytest.fixture
def sample_action_plan():
    """Creating a sample ActionPlan for testing."""
    return ActionPlan(
        explanation="This is a test action plan",
        actions=[
            {
                "type": "shell_command",
                "content": "ls -la",
                "explanation": "List all files"
            },
            {
                "type": "python_code",
                "content": "print('Hello, World!')",
                "explanation": "Print a greeting",
                "dependencies": []
            }
        ],
        requires_confirmation=True,
        requires_backup=False,
        backup_paths=[]
    )

class TestActionPlan:
    """Tests for the ActionPlan class."""
    
    def test_initialization(self):
        """Test ActionPlan initialization with various parameters."""
        # Basic initialization
        plan = ActionPlan(
            explanation="Test explanation",
            actions=[{"type": "shell_command", "content": "echo test"}]
        )
        
        assert plan.explanation == "Test explanation"
        assert len(plan.actions) == 1
        assert plan.requires_confirmation is True
        assert plan.requires_backup is False
        assert plan.backup_paths == []
        
        # Initialization with all parameters
        plan2 = ActionPlan(
            explanation="Full test",
            actions=[{"type": "shell_command", "content": "ls"}],
            requires_confirmation=False,
            requires_backup=True,
            backup_paths=["/tmp/file.txt"]
        )
        
        assert plan2.requires_confirmation is False
        assert plan2.requires_backup is True
        assert len(plan2.backup_paths) == 1
    
    def test_has_python_code_property(self):
        """Test the has_python_code property."""
        # Plan with only shell commands
        shell_plan = ActionPlan(
            explanation="Shell commands only",
            actions=[
                {"type": "shell_command", "content": "ls"},
                {"type": "shell_command", "content": "pwd"}
            ]
        )
        assert shell_plan.has_python_code is False  
        
        # Plan with Python code
        mixed_plan = ActionPlan(
            explanation="Mixed actions",
            actions=[
                {"type": "shell_command", "content": "ls"},
                {"type": "python_code", "content": "print('test')"}
            ]
        )
        assert mixed_plan.has_python_code is True
        
    def test_commands_property(self):
        """Test the commands property for backward compatibility."""
        plan = ActionPlan(
            explanation="Test commands",
            actions=[
                {"type": "shell_command", "content": "ls"},
                {"type": "python_code", "content": "print('test')"},
                {"type": "shell_command", "content": "pwd"}
            ]
        )
        
        assert plan.commands == ["ls", "pwd"]
        assert len(plan.commands) == 2
    
    def test_to_dict_method(self):
        """Test conversion to dictionary."""
        plan = ActionPlan(
            explanation="Test serialization",
            actions=[{"type": "shell_command", "content": "echo test"}],
            requires_backup=True,
            backup_paths=["/tmp/file.txt"]
        )
        
        plan_dict = plan.to_dict()
        assert isinstance(plan_dict, dict)
        assert plan_dict["explanation"] == "Test serialization"
        assert len(plan_dict["actions"]) == 1
        assert plan_dict["requires_backup"] is True
        assert plan_dict["backup_paths"] == ["/tmp/file.txt"]

    def test_from_dict_method(self):
        """Test creation from dictionary."""
        data = {
            "explanation": "From dict test",
            "actions": [{"type": "shell_command", "content": "echo test"}],
            "requires_confirmation": False,
            "requires_backup": True,
            "backup_paths": ["/tmp/test.txt"]
        }
        
        plan = ActionPlan.from_dict(data)
        assert plan.explanation == "From dict test"
        assert plan.requires_confirmation is False
        assert plan.requires_backup is True
        assert plan.backup_paths == ["/tmp/test.txt"]
        
        # Testing with missing fields to check the use of defaults 
        minimal_data = {
            "explanation": "Minimal",
            "actions": []
        }
        minimal_plan = ActionPlan.from_dict(minimal_data)
        assert minimal_plan.requires_confirmation is True
        assert minimal_plan.requires_backup is False


def test_create_prompt(agent):
    """Test that the prompt is created correctly with context."""
    prompt = agent.create_prompt("list files in current directory")
    assert "USER REQUEST: list files in current directory" in prompt
    assert "You are Termora" in prompt


@pytest.mark.asyncio
async def test_parse_valid_json_response(agent):
    """Test parsing a valid JSON response."""
    sample_response = '''
    Here's what I'd recommend:
    
    ```json
    {
        "explanation": "This will list files in the current directory",
        "actions": [
            {
                "type": "shell_command",
                "content": "ls -la",
                "explanation": "Lists all files including hidden ones"
            }
        ],
        "requires_backup": false,
        "backup_paths": []
    }
    ```
    '''
    
    action_plan = agent._parse_response(sample_response, "list files")
    
    assert isinstance(action_plan, ActionPlan)
    assert action_plan.explanation == "This will list files in the current directory"
    assert len(action_plan.actions) == 1
    assert action_plan.actions[0]["content"] == "ls -la"


@pytest.mark.asyncio
async def test_parse_invalid_response(agent):
    """Test handling an invalid response."""
    invalid_response = "Sorry, I don't understand what you're asking for."
    
    action_plan = agent._parse_response(invalid_response, "do something impossible")
    
    assert isinstance(action_plan, ActionPlan)
    assert "I'm sorry, I couldn't properly process your request" in action_plan.explanation
    assert len(action_plan.actions) == 1
    assert "echo" in action_plan.actions[0]["content"]


@pytest.mark.asyncio
@patch("termora.core.agent.subprocess.run")
async def test_execute_python_code(mock_run, agent):
    """Test executing Python code."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "Hello, World!"
    mock_process.stderr = ""
    mock_run.return_value = mock_process
    
    result = await agent.execute_python_code('print("Hello, World!")')
    
    assert result["success"] is True
    assert result["output"] == "Hello, World!"
    assert result["error"] == ""

