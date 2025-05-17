"""
Pipeline processing module for Termora.

This module implements a modular pipeline architecture for processing natural language requests,
extracting intent, generating plans, and coordinating execution with safety measures.

Key functionality:
- Intent: Data class representing extracted user intent
- TermoraPlan: Data class with complete plan and metadata
- TermoraPipeline: Orchestrates the processing flow from input to execution
- Intent extraction: Parse natural language into structured intents
- Plan generation: Create executable commands from intents
- Safety hand

The pipeline follows a clear sequence:
1. Input Parsing -> 2. Context Gathering -> 3. Intent Extraction -> 4. Plan Generation -> 5. Execution -> 6. History Logging
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import os
import json

@dataclass
class Intent:
    """Represents the extracted intent from user input."""
    action: str  # Primary action (move, find, count, etc.)
    target_dir: Optional[str] = None  # Target directory for operations
    file_filter: Optional[Dict[str, Any]] = None  # File selection criteria
    time_filter: Optional[Dict[str, Any]] = None  # Time-based constraints
    destination: Optional[str] = None  # Destination for move/copy operations
    limit: Optional[int] = None  # Result limit
    sort_by: Optional[str] = None  # Sorting criteria
    recursive: bool = True  # Whether to operate recursively

    def to_dict(self) -> Dict[str, Any]:
        """Convert intent to dictionary for serialization."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
@dataclass
class TermoraPlan:
    """Complete execution plan with all metadata."""
    user_input: str
    intent: Intent
    reasoning: str
    plan: List[Dict[str, Any]]  # List of action objects
    preview: Dict[str, str]
    requires_backup: bool = False
    backup_paths: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary for serialization."""
        return {
            "user_input": self.user_input,
            "intent": self.intent.to_dict(),
            "reasoning": self.reasoning,
            "plan": self.plan,
            "preview": self.preview,
            "requires_backup": self.requires_backup,
            "backup_paths": self.backup_paths or []
        }
    
class TermoraPipeline:
    """
    Pipeline orchestrator that manages the flow from input to execution.
    This acts as a facade coordinating the different components.
    """
    
    def __init__(self, agent, executor, context_provider, history_manager, rollback_manager):
        """Initialize the pipeline with required components."""
        self.agent = agent
        self.executor = executor
        self.context_provider = context_provider
        self.history_manager = history_manager
        self.rollback_manager = rollback_manager
    
    def process(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input through the entire pipeline.
        
        Args:
            user_input: Natural language input from user
            
        Returns:
            Execution results
        """
        
        # 1. Parse input 
        parsed_input = self._parse_input(user_input)
        
        # 2. Gather context
        context_data = self.context_provider.get_context()
        context_data["command_history"] = self.history_manager.search_history(limit=10)
        
        # 3. Extract intent via AI model
        intent, reasoning = self._extract_intent(parsed_input, context_data)
        
        # 4. Generate plan
        plan = self._generate_plan(intent, reasoning, parsed_input, context_data)
        
        # 5. Convert to generated plan to ActionPlan for execution
        action_plan = self._convert_to_action_plan(plan)
        
        # 6. Execute (with safety preview and confirmation)
        result = self.executor.execute_plan(action_plan)
        
        # 7. Log history and return result
        if result.get("executed", False):
            self.rollback_manager.save_execution_history(result)
            self.history_manager.add_action_plan(action_plan, result, os.getcwd())
        
        return result
    
    def _parse_input(self, user_input: str) -> str:
        """
        Parse and preprocess user input.
        
        Args:
            user_input: Raw user input
            
        Returns:
            Processed input
        """
        # Keeping it simple for now, room to do more complex pre-processing in the future 
        return user_input.strip()