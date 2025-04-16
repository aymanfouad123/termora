"""
Tests for the agent module.

This module contains tests for the TermoraAgent class in termora.core.agent.py
"""

import pytest
import json
import sys
import subprocess
from unittest.mock import patch, MagicMock
from termora.core.agent import TermoraAgent, ActionPlan


@pytest.fixture
def agent():
    """Create a TermoraAgent instance for testing."""
    return TermoraAgent({"send_to_api": False})  # Use offline mode for tests


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

