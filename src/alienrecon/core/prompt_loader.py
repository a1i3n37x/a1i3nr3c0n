# src/alienrecon/core/prompt_loader.py
"""Utility module for loading prompts from files."""

from pathlib import Path


def load_prompt(prompt_name: str) -> str:
    """Load a prompt from the prompts directory.

    Args:
        prompt_name: Name of the prompt file (without .txt extension)

    Returns:
        The prompt content as a string

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    # Get the prompts directory path
    current_dir = Path(__file__).parent
    prompts_dir = current_dir.parent / "data" / "prompts"
    prompt_file = prompts_dir / f"{prompt_name}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    with open(prompt_file, encoding="utf-8") as f:
        return f.read()


def load_prompt_with_fallback(prompt_name: str, fallback: str) -> str:
    """Load a prompt from file with a fallback value.

    Args:
        prompt_name: Name of the prompt file (without .txt extension)
        fallback: Fallback string to use if file doesn't exist

    Returns:
        The prompt content or fallback string
    """
    try:
        return load_prompt(prompt_name)
    except FileNotFoundError:
        return fallback


# Convenience functions for specific prompts
def load_system_prompt() -> str:
    """Load the main system prompt for the AI agent."""
    return load_prompt("system_prompt")


def load_welcome_message() -> str:
    """Load the welcome message shown when no target is set."""
    return load_prompt("welcome_message")


def load_welcome_message_with_target() -> str:
    """Load the welcome message shown when a target is already set."""
    return load_prompt("welcome_message_with_target")


def load_terminal_simulation_prompt() -> str:
    """Load the terminal simulation prompt for web interface."""
    return load_prompt("terminal_simulation_prompt")
