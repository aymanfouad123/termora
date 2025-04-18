"""
AI Agent module for Termora.

This module handles the core intelligence of Termora, managing the 
interaction with AI models to process natural language requests and 
generate executable action plans (using shell commands or Python code).
"""

import os
import json
import sys
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import re
from dotenv import load_dotenv

# For AI model integration
import litellm
import requests

# Internal imports
from termora.core.context import TerminalContext
from termora.core.history import HistoryManager
from termora.utils.helpers import get_termora_dir

class ActionPlan:
    """
    Represents a structured plan of actions to be executed.
    
    This class encapsulates the AI's response as a structured plan that can contain shell commands, Python code, or a combination of both.
    """
    
    def __init__(
        self,
        explanation: str,
        actions: List[Dict[str, Any]],
        requires_confirmation: bool = True,
        requires_backup: bool = False,
        backup_paths: Optional[List[str]] = None
    ):
        """
        Initialize an action plan.
        
        Args:
            explanation: Human-readable explanation of what the plan will do
            actions: List of action objects (commands or code)
            requires_confirmation: Whether user confirmation is needed
            requires_backup: Whether files should be backed up before execution
            backup_paths: Paths to back up if requires_backup is True
        """
        
        self.explanation = explanation
        self.actions = actions
        self.requires_confirmation = requires_confirmation
        self.requires_backup = requires_backup
        self.backup_paths = backup_paths or []
    
    @property
    def has_python_code(self) -> bool:
        """Check if any action contains Python code."""
        return any(action.get("type") == "python_code" for action in self.actions)
    
    @property
    def commands(self) -> List[str]:
        """Get list of shell commands (for backward compatibility)."""
        return [action["content"] for action in self.actions 
                if action.get("type") == "shell_command"]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the action plan to a dictionary for serialization.
        
        Returns:
            A dictionary representation of the action plan
        """
        return {
            "explanation": self.explanation,
            "actions": self.actions,
            "requires_confirmation": self.requires_confirmation,
            "requires_backup": self.requires_backup,
            "backup_paths": self.backup_paths
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionPlan':
        """
        Create an action plan from a dictionary.
        
        Args:
            data: Dictionary containing action plan information
            
        Returns:
            An ActionPlan instance
        """
        
        return cls(
            explanation=data.get("explanation", ""),
            actions=data.get("actions", []),
            requires_confirmation=data.get("requires_confirmation", True),
            requires_backup=data.get("requires_backup", False),
            backup_paths=data.get("backup_paths", [])
        )

class TermoraAgent:
    """
    The core intelligence of Termora.
    
    This class handles the interaction with AI models to process
    natural language requests and generate executable action plans.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Termora agent.
        
        Args:
            config: Configuration dictionary (optional)
        """
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Set default configuration
        self.config = {
            "ai_provider": os.getenv("AI_PROVIDER", "groq"),
            "ai_model": os.getenv("AI_MODEL", "llama3-70b-8192"),
            "api_key": None,  # Will be set based on provider
            "max_tokens": int(os.getenv("MAX_TOKENS", "2000")),  # Increased for code generation
            "temperature": float(os.getenv("TEMPERATURE", "0.7")),
            "send_to_api": os.getenv("SEND_TO_API", "True").lower() == "true",
            "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434")
        }
        
        # Override defaults with provided config
        if config: self.config.update(config)
        
        # Set API key based on provider
        self._set_api_key()
        
        # Create context gatherer
        self.context = TerminalContext()
        
        # Create history manager
        self.history_manager = HistoryManager()
        
    def _set_api_key(self):
        """Set the appropriate API key based on the configured provider."""
        provider = self.config["ai_provider"].lower()
        
        if provider == "groq":
            self.config["api_key"] = os.getenv("GROQ_API_KEY")
        elif provider == "openai":
            self.config["api_key"] = os.getenv("OPENAI_API_KEY")
        elif provider == "ollama":
            # No API key needed for local Ollama
            pass
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    def create_prompt(self, user_request: str) -> str:
        """
        Create a prompt for the AI model based on user request and context.
        
        Args:
            user_request: The natural language request from the user
            
        Returns:
            A formatted prompt string
        """
        
        # Get system context as string
        context_str = self.context.to_string()
        
        # Get relevant history
        relevant_history = self._get_relevant_history(user_request)
        history_str = self._format_history(relevant_history)
        
        # Build the complete prompt
        prompt = f"""You are Termora, an agentic AI terminal assistant that helps users accomplish tasks by generating the optimal solution.

        {context_str}

        RELEVANT HISTORY:
        {history_str}

        USER REQUEST: {user_request}

        INSTRUCTIONS:
        1. Analyze the request and determine the best approach to accomplish the task.
        2. You can use shell commands, generate Python code, or a combination of both.
        3. Consider the OS and current environment when generating your solution.
        4. Always use safe approaches that won't cause data loss.
        5. For potentially destructive operations, identify paths that should be backed up.

        RESPONSE FORMAT:
        Return your response in the following JSON format:
        {{
            "explanation": "A clear explanation of what your plan will do",
            "actions": [
                {{
                    "type": "shell_command",
                    "content": "command to execute",
                    "explanation": "what this command does"
                }},
                {{
                    "type": "python_code",
                    "content": "Python code to execute",
                    "explanation": "what this code does",
                    "dependencies": ["package1", "package2"]
                }}
            ],
            "requires_backup": boolean,
            "backup_paths": ["path1", "path2", ...]
        }}

        IMPORTANT: Your response must be valid JSON that can be parsed with json.loads().
        For Python code, be sure to include any necessary imports.
        If a task would be better accomplished with Python code than shell commands, don't hesitate to use Python.
        """
        
        return prompt
    
    def _get_relevant_history(self, user_request: str) -> List[Dict[str, Any]]:
        """
        Get relevant command history based on the user request.
        
        Args:
            user_request: The user's natural language request
            
        Returns:
            List of relevant history entries
        """
        # Currently a simple implementation - will be enhanced later
        # Get the 5 most recent commands
        return self.history_manager.search_history(limit=5)
    
    def _format_history(self, history: List[Dict[str, Any]]) -> str:
        """Format history entries into a string for the prompt."""
        if not history:
            return "No relevant history found."
        
        result = []
        for entry in history:
            cmd = entry.get("command", "")
            dir_path = entry.get("directory", "")
            timestamp = entry.get("timestamp", "")
            
            result.append(f"Command: {cmd}")
            result.append(f"Directory: {dir_path}")
            result.append(f"Time: {timestamp}")
            result.append("")  # Empty line for separation
            
        return "\n".join(result)
    
    async def process_request(self, user_request: str) -> ActionPlan:
        """
        Process a user request and return an action plan.
        
        Args:
            user_request: The natural language request from the user
            
        Returns:
            An ActionPlan object
        """
        
        # Create the prompt
        prompt = self.create_prompt(user_request)
        
        # Call the appropriate AI provider
        response = await self._call_ai_provider(prompt)
        
        # Parse the response
        return self._parse_response(response, user_request)
    
    async def _call_ai_provider(self, prompt: str) -> str:
        """
        Call the AI provider with the given prompt.
        
        Args:
            prompt: The prepared prompt string
            
        Returns:
            The AI response as a string
        """
        provider = self.config["ai_provider"].lower()
        model = self.config["ai_model"]
        
        # Check if we should send to API
        if not self.config["send_to_api"]:
            return self._get_offline_fallback_response(prompt)
        
        try:
            if provider == "ollama":
                return await self._call_ollama(prompt)
            else:
                # Use litellm for other providers
                response = await litellm.acompletion(
                    model=f"{provider}/{model}",
                    messages=[{"role": "user", "content": prompt}],
                    api_key=self.config["api_key"],
                    max_tokens=self.config["max_tokens"],
                    temperature=self.config["temperature"]
                )
                return response.choices[0].message.content
        except Exception as e:
            # Log the error
            print(f"Error calling AI provider: {str(e)}")
            
            # Return a fallback response
            return self._get_error_fallback_response()
        
    async def _call_ollama(self, prompt: str) -> str:
        """
        Call a local Ollama instance with the given prompt.
        
        Args:
            prompt: The prepared prompt string
            
        Returns:
            The AI response as a string
        """
        try:
            ollama_url = f"{self.config['ollama_host']}/api/generate"
            response = requests.post(
                ollama_url,
                json={
                    "model": self.config["ai_model"],
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config["temperature"],
                        "num_predict": self.config["max_tokens"],
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            print(f"Error calling Ollama: {str(e)}")
            return self._get_error_fallback_response()
    
    def _get_offline_fallback_response(self, prompt: str) -> str:
        """
        Provide a simple response when send_to_api is disabled.
        
        Args:
            prompt: The original prompt
            
        Returns:
            A simple fallback response
        """
        return json.dumps({
            "explanation": "API requests are disabled. Using offline fallback mode with limited functionality.",
            "commands": ["echo 'API requests are disabled. Please enable SEND_TO_API in your .env file or use --allow-api flag.'"],
            "requires_backup": False,
            "backup_paths": []
        })
    
    def _get_error_fallback_response(self) -> str:
        """
        Provide a fallback response when AI calls fail.
        
        Returns:
            A simple error response
        """
        return json.dumps({
            "explanation": "There was an error processing your request. Please check your API key and internet connection.",
            "commands": ["echo 'Error: Could not connect to AI service. Please check your configuration.'"],
            "requires_backup": False,
            "backup_paths": []
        })
        
    def _parse_response(self, response: str, original_request: str) -> ActionPlan:
        """
        Parse the AI response into an ActionPlan.
        
        Args:
            response: The raw response from the AI
            original_request: The original user request
            
        Returns:
            An ActionPlan object
        """
        
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'{.*}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # Create ActionPlan from the data
                return ActionPlan(
                    explanation=data.get("explanation", ""),
                    actions=data.get("actions", []),
                    requires_confirmation=True,
                    requires_backup=data.get("requires_backup", False),
                    backup_paths=data.get("backup_paths", [])
                )
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            # If parsing fails, create a simple fallback plan
            return ActionPlan(
                explanation=f"I'm sorry, I couldn't properly process your request: {original_request}",
                actions=[
                    {
                        "type": "shell_command",
                        "content": "echo 'Request could not be processed. Please try again with a clearer description.'",
                        "explanation": "Display an error message"
                    }
                ],
                requires_confirmation=True,
                requires_backup=False
            )
    
    async def execute_python_code(self, code: str) -> Dict[str, Any]:
        """
        Execute Python code in a safe temporary environment.
        
        Args:
            code: Python code to execute
            
        Returns:
            Dict with execution results
        """
        try:
            # Create a temporary directory and file
            with tempfile.TemporaryDirectory() as temp_dir:
                script_path = Path(temp_dir) / "termora_script.py"
                
                # Write code to file
                with open(script_path, "w") as f:
                    f.write(code)
                
                # Execute the Python script
                process = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True
                )
                
                return {
                    "success": process.returncode == 0,
                    "output": process.stdout,
                    "error": process.stderr,
                    "return_code": process.returncode
                }
                
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": 1
            }