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

from termora.core.agent import ActionPlan

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
    
    def _extract_intent(self, user_input: str, context_data: Dict[str, Any]) -> tuple[Intent, str]:
        """
        Extract intent from user input through prompting.
        
        Args:
            user_input: User's request
            context_data: Current context
            
        Returns:
            Tuple of (Intent object, reasoning string)
        """
        
        # Use the agent with an intent extraction prompt
        intent_extraction_prompt = self._create_intent_extraction_prompt(user_input, context_data)

        # Get intent from AI
        response = self.agent.get_raw_completion(intent_extraction_prompt)
        
        # Parse the response
        intent_data = self._parse_intent_response(response)

        # Create Intent object
        intent = Intent(
            action=intent_data.get("action", "unknown"),
            target_dir=intent_data.get("target_dir"),
            file_filter=intent_data.get("file_filter"),
            time_filter=intent_data.get("time_filter"),
            destination=intent_data.get("destination"),
            limit=intent_data.get("limit"),
            sort_by=intent_data.get("sort_by"),
            recursive=intent_data.get("recursive", True)
        )
        
        reasoning = intent_data.get("reasoning", "")
    
        return intent, reasoning
    
    def _create_intent_extraction_prompt(self, user_input: str, context_data: Dict[str, Any]) -> str:
        """Create prompt for intent extraction."""
        context_str = self.context_provider.to_string()
        
        prompt = f"""You are Termora, an intelligent terminal assistant.
        
        {context_str}
        
        USER REQUEST: {user_input}
        
        TASK:
        Extract the intent and parameters from this user request.
        
        INSTRUCTIONS:
        1. Identify the primary action (move, find, list, count, delete, etc.)
        2. Extract all relevant parameters (paths, filters, options)
        3. Map vague references to specific technical details
        4. Provide step-by-step reasoning
        
        Return your analysis as JSON with this structure:
        {{
            "action": "primary_action",
            "target_dir": "directory to operate on",
            "file_filter": {{ filters for selecting files }},
            "time_filter": {{ date/time constraints }},
            "destination": "destination path if relevant",
            "limit": number_of_results,
            "sort_by": "sorting_criterion",
            "recursive": true_or_false,
            "reasoning": "Your step-by-step reasoning process"
        }}
        
        For example, with "Move all screenshots from March into an archive folder":
        {{
            "action": "move",
            "file_filter": {{ "name_pattern": "*screenshot*" }},
            "time_filter": {{ "from": "2024-03-01", "to": "2024-04-01" }}, # If no year is mentioned for a time period then assume the user is assuming to use the current year
            "destination": "~/archive",
            "reasoning": "The user wants to move files..."
        }}
        
        IMPORTANT: Your response must be valid JSON and include thorough reasoning.
        """
        
        return prompt
    
    def _parse_intent_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response to extract Intent data."""
        import json
        import re
        
        # Try to extract JSON from response
        try:
            # Look for JSON object in the response
            match = re.search(r'({.*})', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            else:
                return {"action": "unknown", "reasoning": "Failed to parse intent from response"}
        except Exception:
            return {"action": "unknown", "reasoning": "Failed to parse intent from response"}

    def _generate_plan(self, intent: Intent, reasoning: str, user_input: str, context_data: Dict[str, Any]) -> TermoraPlan:
        """
        Generate execution plan based on intent.
        
        Args:
            intent: Extracted intent object
            reasoning: Reasoning behind the intent extraction
            user_input: Original user input
            context_data: Current context
            
        Returns:
            TermoraPlan object
        """
        # Create plan generation prompt
        plan_prompt = self._create_plan_generation_prompt(intent, reasoning, user_input, context_data)
        
        # Get plan from AI
        response = self.agent.get_raw_completion(plan_prompt)
        
        # Parse the response
        plan_data = self._parse_plan_response(response)
        
        # Create plan object
        return TermoraPlan(
            user_input=user_input,
            intent=intent,
            reasoning=reasoning,
            plan=plan_data.get("plan", []),
            preview=plan_data.get("preview", {}),
            requires_backup=plan_data.get("requires_backup", False),
            backup_paths=plan_data.get("backup_paths", [])
        )

    def _create_plan_generation_prompt(self, intent: Intent, reasoning: str, user_input: str, context_data: Dict[str, Any]) -> str:
        """Create prompt for plan generation."""
        context_str = self.context_provider.to_string()
        intent_json = json.dumps(intent.to_dict(), indent=2)
        
        prompt = f"""You are Termora, an intelligent terminal assistant.
        
        {context_str}
        
        USER REQUEST: {user_input}
        
        EXTRACTED INTENT:
        {intent_json}
        
        REASONING:
        {reasoning}
        
        TASK:
        Generate a specific, safe execution plan based on this intent.
        
        INSTRUCTIONS:
        1. Design a sequence of shell commands to fulfill the intent
        2. Ensure commands are safe and include error checking
        3. Add proper path resolution for all referenced directories
        4. For potentially dangerous operations, implement a safe alternative
        5. For file deletion, use trash system instead of permanent deletion
        
        Return your plan as JSON with this structure:
        {{
            "plan": [
                {{
                    "type": "shell_command",
                    "content": "command to execute",
                    "explanation": "what this command does"
                }},
                // more actions...
            ],
            "preview": {{
                "natural_language": "Human-readable explanation of plan",
                "safety_notes": "Notes about safety precautions taken"
            }},
            "requires_backup": boolean,
            "backup_paths": ["path1", "path2", ...]
        }}
        
        IMPORTANT: Your response must be valid JSON with safe, properly escaped shell commands.
        """
        
        return prompt
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response to extract plan data."""
        import json
        import re
        
        # Try to extract JSON from response
        try:
            # Look for JSON object in the response
            match = re.search(r'({.*})', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            else:
                return {"plan": [], "preview": {"natural_language": "Failed to generate plan"}}
        except Exception:
            return {"plan": [], "preview": {"natural_language": "Failed to generate plan"}}
        
    def _convert_to_action_plan(self, plan: TermoraPlan) -> 'ActionPlan':
        """
        Convert TermoraPlan to ActionPlan for execution.
        
        Args:
            plan: TermoraPlan object
            
        Returns:
            ActionPlan object
        """
    
        # Create explanation from preview
        explanation = plan.preview.get("natural_language", "")
        if "safety_notes" in plan.preview:
            explanation += f"\n\n{plan.preview['safety_notes']}"
        
        # Convert to ActionPlan format
        return ActionPlan(
            explanation=explanation,
            actions=plan.plan,
            requires_confirmation=True,  # Always confirm
            requires_backup=plan.requires_backup,
            backup_paths=plan.backup_paths,
            reasoning=plan.reasoning
        )