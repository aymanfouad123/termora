"""
Test script for debugging the TermoraPipeline process function.
This script allows you to test the entire pipeline and fine-tune AI responses.
"""

import os
import sys
from pathlib import Path

# Add the termora directory to the path so we can import modules
sys.path.append(str(Path(__file__).parent))

from termora.core.pipeline import TermoraPipeline
from termora.core.context import TerminalContext
from termora.core.agent import TermoraAgent
from termora.core.executor import CommandExecutor
from termora.core.rollback import RollbackManager
from termora.core.history import HistoryManager


def run_test(user_input, model="groq", verbose=False):
    """Run a test with the provided input using the real TermoraAgent."""
    print(f"\n{'=' * 80}\n= TESTING PIPELINE WITH INPUT: {user_input} {'=' * (51 - len(user_input))}")
    print(f"{'=' * 80}")

    # Create agent config with the selected model (same as main.py)
    agent_config = {
        "ai_provider": model,
        "ai_model": "llama3-70b-8192" if model == "groq" else "gpt-4" if model == "openai" else "llama3",
        "temperature": 0.7,
        "max_tokens": 2000
    }
    agent = TermoraAgent(config=agent_config)
    executor = CommandExecutor()
    context_provider = TerminalContext()
    history_manager = HistoryManager()
    rollback_manager = RollbackManager()

    pipeline = TermoraPipeline(
        agent=agent,
        executor=executor,
        context_provider=context_provider,
        history_manager=history_manager,
        rollback_manager=rollback_manager
    )

    result = pipeline.process(user_input)

    print(f"\n{'=' * 80}\n= FINAL RESULT {'=' * 66}")
    import json
    print(json.dumps(result, indent=2))
    print(f"{'=' * 80}")
    return result


def show_help():
    print(f"\n{'=' * 80}")
    print("= TERMORA PIPELINE REAL AGENT TEST HARNESS")
    print("= Usage:")
    print("=   python test_pipeline.py [options] [\"user input\"]")
    print("= ")
    print("= Options:")
    print("=   --help, -h       Show this help message")
    print("=   --model, -m      AI model to use (openai, groq, ollama)")
    print("=   --verbose, -v    Show verbose output")
    print("= ")
    print("= Example:")
    print("=   python test_pipeline.py \"find all markdown files\"")
    print(f"{'=' * 80}\n")

if __name__ == "__main__":
    # Process command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test TermoraPipeline with real agent")
    parser.add_argument("input", nargs="*", help="User input to test")
    parser.add_argument("--model", "-m", choices=["openai", "groq", "ollama"], default="groq", help="AI model to use")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    parser.add_argument("--help", "-h", action="store_true", help="Show help message and exit")
    args = parser.parse_args()

    if args.help:
        show_help()
        sys.exit(0)

    if args.input:
        user_input = " ".join(args.input)
        run_test(user_input, model=args.model, verbose=args.verbose)
    else:
        show_help() 