"""
AI Agent module for Termora.

This module handles the core intelligence of Termora, managing the 
interaction with AI models to process natural language requests and 
generate executable action plans (using shell commands or Python code).
"""

import os
import json
import time
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
    natural language requests and generate executable command plans.
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
            "max_tokens": int(os.getenv("MAX_TOKENS", "500")),
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
        
        # Build the complete prompt
        prompt = f"""You are Termora, an AI terminal assistant that helps users accomplish tasks by generating shell commands.

        {context_str}

        USER REQUEST: {user_request}

        INSTRUCTIONS:
        1. Analyze the request and determine what commands would accomplish the task.
        2. Consider the OS and current environment when generating commands.
        3. Always use safe approaches that won't cause data loss.
        4. For destructive operations (remove, move, etc.), identify paths that should be backed up.

        RESPONSE FORMAT:
        Return your response in the following JSON format:
        {{
        "explanation": "A clear explanation of what your plan will do",
        "commands": ["command1", "command2", ...],
        "requires_backup": boolean,
        "backup_paths": ["path1", "path2", ...]
        }}

        IMPORTANT: Your response must be valid JSON that can be parsed with json.loads().
        If you're not confident about a command's safety, you should:
        1. Explain the risk in the explanation section
        2. Mark requires_backup as true
        3. Add any paths that might be affected to backup_paths
        """
        
        return prompt
    
    async def process_request(self, user_request: str) -> CommandPlan:
        """
        Process a user request and return a command plan.
        
        Args:
            user_request: The natural language request from the user
            
        Returns:
            A CommandPlan object
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
        
    def _parse_response(self, response: str, original_request: str) -> CommandPlan:
        """
        Parse the AI response into a structured command plan.
        
        Args:
            response: The AI response string
            original_request: The original user request
            
        Returns:
            A CommandPlan object
        """
        # Try to parse as JSON
        try:
            # Looking for a JSON code block using regex
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find any JSON object in the response
                json_match = re.search(r"({.*})", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response
            
            data = json.loads(json_str)
            
            # Ensure required fields exist
            if "commands" not in data:
                data["commands"] = []
            if "explanation" not in data:
                data["explanation"] = "No explanation provided."

            # Check if any command is destructive
            requires_backup = data.get("requires_backup", False)
            for cmd in data.get("commands", []):
                from termora.utils.helpers import is_destructive_command
                if is_destructive_command(cmd):
                    requires_backup = True
                    break
                    
            # Create the command plan
            return CommandPlan(
                explanation=data["explanation"],
                commands=data["commands"],
                requires_backup=requires_backup,
                backup_paths=data.get("backup_paths", [])
            )
            
        except Exception as e:
            # If parsing fails, return a fallback command plan
            print(f"Error parsing AI response: {str(e)}")
            return CommandPlan(
                explanation=f"I couldn't generate a proper command plan for: '{original_request}'",
                commands=[f"echo 'Error: Could not parse the AI response for your request.'"],
                requires_confirmation=True,
                requires_backup=False
            )