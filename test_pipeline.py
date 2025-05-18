"""
Test script for debugging the TermoraPipeline process function.
This script allows you to test the entire pipeline and fine-tune AI responses.
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path

# Add the termora directory to the path so we can import modules
sys.path.append(str(Path(__file__).parent))

from termora.core.pipeline import TermoraPipeline, Intent, TermoraPlan
from termora.core.agent import ActionPlan
from termora.core.context import TerminalContext

# Predefined templates for common test cases
INTENT_TEMPLATES = {
    "find_files": {
        "action": "find",
        "target_dir": ".",
        "file_filter": {
            "name_pattern": "*.md",
            "created_after": "1 week ago"
        },
        "recursive": True,
        "reasoning": "The user wants to find files matching a pattern in the current directory."
    },
    "move_files": {
        "action": "move",
        "target_dir": "~/Downloads",
        "file_filter": {
            "type": "image"
        },
        "destination": "~/vacation_photos",
        "recursive": False,
        "reasoning": "The user wants to move image files from the Downloads folder to a vacation_photos folder."
    },
    "count_files": {
        "action": "count",
        "target_dir": ".",
        "file_filter": {
            "modified_after": "yesterday"
        },
        "recursive": True,
        "reasoning": "The user wants to count files modified since yesterday."
    },
    "list_files": {
        "action": "list",
        "target_dir": "~/Documents",
        "file_filter": {
            "type": "document",
            "size_greater_than": "1M"
        },
        "sort_by": "size",
        "recursive": False,
        "reasoning": "The user wants to list document files larger than 1MB in the Documents folder, sorted by size."
    },
    "delete_files": {
        "action": "delete",
        "target_dir": "~/tmp",
        "file_filter": {
            "name_pattern": "*.tmp",
            "modified_before": "1 month ago"
        },
        "recursive": True,
        "reasoning": "The user wants to delete temporary files older than 1 month from the tmp directory."
    }
}

PLAN_TEMPLATES = {
    "find_files": {
        "plan": [
            {
                "type": "shell_command",
                "content": "find . -name '*.md' -type f -mtime -7",
                "explanation": "Find all markdown files created or modified in the last 7 days",
                "fallback": "ls -la | grep '\\.md$' | grep -E '$(date -v-7d \"+%b %e|%b  %e\")'"
            }
        ],
        "preview": {
            "natural_language": "I'll search for Markdown files in the current directory that were created or modified in the last 7 days.",
            "safety_notes": "This is a read-only operation that won't modify any files."
        },
        "requires_backup": False,
        "backup_paths": []
    },
    "move_files": {
        "plan": [
            {
                "type": "shell_command",
                "content": "mkdir -p ~/vacation_photos",
                "explanation": "Create the destination directory if it doesn't exist",
                "fallback": "mkdir -p ~/vacation_photos || echo 'Failed to create directory'"
            },
            {
                "type": "shell_command",
                "content": "find ~/Downloads -type f -name \"*.jpg\" -o -name \"*.jpeg\" -o -name \"*.png\" -o -name \"*.gif\" -exec mv {} ~/vacation_photos/ \\;",
                "explanation": "Move image files from Downloads to vacation_photos",
                "fallback": "for f in ~/Downloads/*.{jpg,jpeg,png,gif}; do [ -f \"$f\" ] && mv \"$f\" ~/vacation_photos/; done"
            }
        ],
        "preview": {
            "natural_language": "I'll create a vacation_photos directory if it doesn't exist, then move all image files from your Downloads folder to it.",
            "safety_notes": "This operation will move files. The original files will be moved, not copied."
        },
        "requires_backup": True,
        "backup_paths": ["~/Downloads/*.jpg", "~/Downloads/*.jpeg", "~/Downloads/*.png", "~/Downloads/*.gif"]
    },
    "count_files": {
        "plan": [
            {
                "type": "shell_command",
                "content": "find . -type f -mtime -1 | wc -l",
                "explanation": "Count files modified in the last day",
                "fallback": "ls -la --time=mtime | grep -v '^d' | grep \"$(date -v-1d \"+%b %e|%b  %e\")\" | wc -l"
            }
        ],
        "preview": {
            "natural_language": "I'll count the number of files in the current directory that were modified since yesterday.",
            "safety_notes": "This is a read-only operation that won't modify any files."
        },
        "requires_backup": False,
        "backup_paths": []
    },
    "list_files": {
        "plan": [
            {
                "type": "shell_command",
                "content": "find ~/Documents -type f -size +1M -exec ls -lSh {} \\;",
                "explanation": "List files larger than 1MB in Documents sorted by size",
                "fallback": "ls -lSh ~/Documents | grep -v '^d' | awk '$5 ~ /[0-9]M|[0-9]G/'"
            }
        ],
        "preview": {
            "natural_language": "I'll list document files larger than 1MB in your Documents folder, sorted by size.",
            "safety_notes": "This is a read-only operation that won't modify any files."
        },
        "requires_backup": False,
        "backup_paths": []
    },
    "delete_files": {
        "plan": [
            {
                "type": "shell_command",
                "content": "find ~/tmp -name \"*.tmp\" -type f -mtime +30 -exec mv {} ~/.Trash/ \\;",
                "explanation": "Move temporary files older than 1 month to the trash",
                "fallback": "for f in ~/tmp/*.tmp; do [ -f \"$f\" ] && [ $((($(date +%s) - $(stat -f %m \"$f\"))/86400)) -gt 30 ] && mv \"$f\" ~/.Trash/; done"
            }
        ],
        "preview": {
            "natural_language": "I'll safely delete temporary files older than 1 month from your tmp directory by moving them to the trash.",
            "safety_notes": "Files will be moved to the trash rather than permanently deleted. You can recover them if needed."
        },
        "requires_backup": True,
        "backup_paths": ["~/tmp/*.tmp"]
    }
}

class InteractiveDebugAgent:
    """Debug agent that allows editing of responses for fine-tuning."""
    def __init__(self, interactive=True, template=None):
        self.last_prompt = None
        self.call_count = 0
        self.interactive = interactive
        self.template = template
        
    def get_raw_completion(self, prompt):
        """Print the prompt and provide an editable JSON response for debugging."""
        self.last_prompt = prompt
        self.call_count += 1
        
        # Print the prompt with a clear header
        call_type = "Intent Extraction" if self.call_count == 1 else "Plan Generation"
        print(f"\n{'=' * 80}\n= PROMPT SENT TO AGENT FOR {call_type} {'=' * (75 - len(call_type))}")
        print(prompt)
        print(f"{'=' * 80}\n")
        
        # Generate response based on template or defaults
        if self.call_count == 1:  # Intent extraction
            if self.template and self.template in INTENT_TEMPLATES:
                response = INTENT_TEMPLATES[self.template].copy()
            else:
                # Default intent response
                response = {
                    "action": "find",
                    "target_dir": ".",
                    "file_filter": {
                        "name_pattern": "*.md",
                        "created_after": "1 week ago"
                    },
                    "recursive": True,
                    "reasoning": "The user wants to find Markdown files (.md) that were created within the last week. The request doesn't specify a target directory, so I'll use the current directory as the starting point. The time filter is set to find files created in the last week."
                }
        else:  # Plan generation
            if self.template and self.template in PLAN_TEMPLATES:
                response = PLAN_TEMPLATES[self.template].copy()
            else:
                # Default plan response
                response = {
                    "plan": [
                        {
                            "type": "shell_command",
                            "content": "find . -name '*.md' -type f -mtime -7",
                            "explanation": "Find all markdown files created or modified in the last 7 days",
                            "fallback": "ls -la | grep '\\.md$' | grep -E '$(date -v-7d \"+%b %e|%b  %e\")'"
                        }
                    ],
                    "preview": {
                        "natural_language": "I'll search for Markdown files in the current directory that were created or modified in the last 7 days.",
                        "safety_notes": "This is a read-only operation that won't modify any files."
                    },
                    "requires_backup": False,
                    "backup_paths": []
                }
        
        # If interactive mode is on, allow editing the response
        if self.interactive:
            print(f"= DEFAULT {call_type.upper()} RESPONSE {'=' * (70 - len(call_type))}")
            formatted_json = json.dumps(response, indent=2)
            print(formatted_json)
            print(f"{'=' * 80}")
            
            edit_choice = input("\nDo you want to edit this response? (y/n): ")
            if edit_choice.lower() == 'y':
                # Create a temporary file with the JSON
                with tempfile.NamedTemporaryFile(suffix=".json", mode='w+', delete=False) as tmp:
                    tmp.write(formatted_json)
                    tmp_path = tmp.name
                
                # Open the file in the default editor
                editor = os.environ.get('EDITOR', 'nano')  # Default to nano if no editor is set
                try:
                    subprocess.run([editor, tmp_path], check=True)
                    
                    # Read back the edited content
                    with open(tmp_path, 'r') as edited_file:
                        edited_content = edited_file.read()
                    
                    # Parse the edited JSON
                    try:
                        response = json.loads(edited_content)
                        print("Response updated successfully!")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing edited JSON: {e}")
                        print("Using default response instead.")
                except Exception as e:
                    print(f"Error opening editor: {e}")
                
                # Clean up the temporary file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        # Print the final response
        print(f"\n{'=' * 80}\n= FINAL {call_type.upper()} RESPONSE {'=' * (70 - len(call_type))}")
        print(json.dumps(response, indent=2))
        print(f"{'=' * 80}\n")
        
        return json.dumps(response)

class MockExecutor:
    """Mock executor that prints the plan instead of executing it."""
    def execute_plan(self, action_plan):
        print(f"\n{'=' * 80}\n= ACTION PLAN RECEIVED BY EXECUTOR {'=' * 47}")
        print(f"Explanation: {action_plan.explanation}")
        print("Actions:")
        for i, action in enumerate(action_plan.actions):
            print(f"  {i+1}. {action.get('type', 'unknown')}: {action.get('content', 'missing content')}")
            print(f"     Explanation: {action.get('explanation', 'No explanation')}")
            print(f"     Fallback: {action.get('fallback', 'No fallback')}")
        
        # Return a mock result
        return {
            "executed": True,
            "results": [{"status": "simulated", "output": "Test output"}]
        }

class MockHistoryManager:
    """Mock history manager."""
    def search_history(self, limit=10):
        return []
    
    def add_action_plan(self, action_plan, result, cwd):
        pass

class MockRollbackManager:
    """Mock rollback manager."""
    def save_execution_history(self, result):
        pass

def run_test(user_input, interactive=True, template=None):
    """Run a test with the provided input and allow interactive editing of AI responses."""
    print(f"\n{'=' * 80}\n= TESTING PIPELINE WITH INPUT: {user_input} {'=' * (51 - len(user_input))}")
    print(f"{'=' * 80}")
    
    # Create dependencies with the interactive debug agent
    agent = InteractiveDebugAgent(interactive=interactive, template=template)
    executor = MockExecutor()
    context_provider = TerminalContext()
    history_manager = MockHistoryManager()
    rollback_manager = MockRollbackManager()
    
    # Create and run the pipeline
    pipeline = TermoraPipeline(
        agent=agent,
        executor=executor,
        context_provider=context_provider,
        history_manager=history_manager,
        rollback_manager=rollback_manager
    )
    
    # Process the input and print the result
    result = pipeline.process(user_input)
    
    print(f"\n{'=' * 80}\n= FINAL RESULT {'=' * 66}")
    print(json.dumps(result, indent=2))
    print(f"{'=' * 80}")
    
    return result

def show_help():
    """Show help for the test script."""
    print(f"\n{'=' * 80}")
    print("= TERMORA PIPELINE TEST HARNESS")
    print("= Usage:")
    print("=   python test_pipeline.py [options] [\"user input\"]")
    print("= ")
    print("= Options:")
    print("=   --help, -h       Show this help message")
    print("=   --non-interactive, -n    Run without interactive edits")
    print("=   --template, -t    Use a predefined template (see below)")
    print("= ")
    print("= Available templates:")
    for template in INTENT_TEMPLATES.keys():
        print(f"=   {template}")
    print("= ")
    print("= Examples:")
    print("=   python test_pipeline.py \"find all markdown files\"")
    print("=   python test_pipeline.py -n \"count images in downloads folder\"")
    print("=   python test_pipeline.py -t move_files \"move photos to vacation folder\"")
    print(f"{'=' * 80}\n")

if __name__ == "__main__":
    # Process command line arguments
    interactive_mode = True
    test_input = None
    template = None
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        # Process flags
        if arg in ('--help', '-h'):
            show_help()
            sys.exit(0)
        elif arg in ('--non-interactive', '-n'):
            interactive_mode = False
            i += 1
        elif arg in ('--template', '-t'):
            if i + 1 < len(sys.argv):
                template = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --template requires a template name")
                show_help()
                sys.exit(1)
        else:
            # Collect remaining args as the user input
            test_input = " ".join(sys.argv[i:])
            break
        
    if test_input:
        # Run a single test with the provided input
        run_test(test_input, interactive=interactive_mode, template=template)
    else:
        # Interactive mode
        print(f"\n{'=' * 80}\n= INTERACTIVE DEBUG MODE {'=' * 59}")
        print(f"= Enter user inputs to test each stage of the pipeline (Ctrl+C to exit) {'=' * 19}")
        print(f"= Type 'help' for usage information {'=' * 42}")
        print(f"= Available templates: {', '.join(INTENT_TEMPLATES.keys())}")
        print(f"{'=' * 80}")
        
        try:
            while True:
                user_input = input("\nUser input (or 'template:name' to use a template): ")
                if not user_input.strip():
                    continue
                
                if user_input.lower() in ('help', '--help', '-h'):
                    show_help()
                    continue
                
                if user_input.lower() in ('exit', 'quit', 'q'):
                    print("\nExiting interactive mode.")
                    break
                
                # Check for template prefix
                template_prefix = "template:"
                if user_input.lower().startswith(template_prefix):
                    parts = user_input.split(" ", 1)
                    template_name = parts[0][len(template_prefix):]
                    
                    if len(parts) > 1:
                        test_input = parts[1]
                    else:
                        test_input = input("Enter user input to test with this template: ")
                    
                    if template_name in INTENT_TEMPLATES:
                        run_test(test_input, interactive=interactive_mode, template=template_name)
                    else:
                        print(f"Unknown template: {template_name}")
                        print(f"Available templates: {', '.join(INTENT_TEMPLATES.keys())}")
                else:
                    run_test(user_input, interactive=interactive_mode)
        except KeyboardInterrupt:
            print("\nExiting interactive mode.") 