#!/usr/bin/env python3
"""
Test the enhanced tool confirmation features.
"""

import json
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from alienrecon.core.mcp_client import MCPToolCall
from alienrecon.core.mcp_session_adapter import MCPSessionAdapter


class MockSessionController:
    """Mock session controller for testing."""

    def __init__(self):
        self.dry_run = False
        self.session_manager = MockSessionManager()
        self.interaction = MockInteraction()


class MockSessionManager:
    """Mock session manager."""

    def __init__(self):
        self.chat_history = []


class MockInteraction:
    """Mock interaction handler with simulated input."""

    def __init__(self):
        self.console = self
        self.input_sequence = []
        self.input_index = 0

    def set_inputs(self, inputs):
        """Set a sequence of inputs for testing."""
        self.input_sequence = inputs
        self.input_index = 0

    def display_info(self, msg):
        print(f"Info: {msg}")

    def display_warning(self, msg):
        print(f"Warning: {msg}")

    def print(self, *args, **kwargs):
        # Extract text from rich markup
        text = str(args[0]) if args else ""
        # Simple removal of common markup
        text = text.replace("[bold yellow]", "").replace("[/bold yellow]", "")
        text = text.replace("[bold]", "").replace("[/bold]", "")
        text = text.replace("[cyan]", "").replace("[/cyan]", "")
        text = text.replace("[red]", "").replace("[/red]", "")
        text = text.replace("[green]", "").replace("[/green]", "")
        text = text.replace("[yellow]", "").replace("[/yellow]", "")
        text = text.replace("[dim]", "").replace("[/dim]", "")
        text = text.replace("[bold cyan]", "").replace("[/bold cyan]", "")
        text = text.replace("[bold magenta]", "").replace("[/bold magenta]", "")
        print(text)

    def input(self, prompt=""):
        """Simulate user input."""
        self.print(prompt, end="")
        if self.input_index < len(self.input_sequence):
            response = self.input_sequence[self.input_index]
            self.input_index += 1
            print(response)  # Echo the input
            return response
        else:
            raise EOFError("No more test inputs")

    def prompt_input(self, prompt):
        """Simulate prompt input."""
        return self.input(prompt)


def test_edit_parameters():
    """Test parameter editing functionality."""
    print("=== Test 1: Parameter Editing ===\n")

    # Create mock controller
    controller = MockSessionController()
    adapter = MCPSessionAdapter(controller)

    # Set up test inputs: edit, change port, add custom flag, confirm
    controller.interaction.set_inputs(
        [
            "e",  # Edit parameters
            "",  # Keep target (press enter)
            "1-5000",  # Change ports
            "",  # Keep scan_type
            "fast=true",  # Add new parameter
            "",  # Done adding parameters
            "c",  # Confirm execution
        ]
    )

    # Create test tool call
    tool_call = MCPToolCall(
        tool="nmap_scan",
        parameters={"target": "192.168.1.1", "ports": "1-1000", "scan_type": "stealth"},
    )

    print("Original tool call:")
    print(f"  Tool: {tool_call.tool}")
    print(f"  Parameters: {json.dumps(tool_call.parameters, indent=4)}")
    print()

    # Get user confirmation
    choice, updated_tool_call = adapter._get_user_confirmation(tool_call)

    print(f"\nFinal choice: {choice}")
    if updated_tool_call:
        print("Updated parameters:")
        print(f"  {json.dumps(updated_tool_call.parameters, indent=4)}")


def test_skip_tool():
    """Test skipping a tool."""
    print("\n\n=== Test 2: Skip Tool ===\n")

    controller = MockSessionController()
    adapter = MCPSessionAdapter(controller)

    # Set up test input: skip
    controller.interaction.set_inputs(["s"])

    tool_call = MCPToolCall(
        tool="nikto_scan", parameters={"target": "http://example.com"}
    )

    choice, _ = adapter._get_user_confirmation(tool_call)
    print(f"Choice: {choice} (should be 's' for skip)")


def test_direct_confirm():
    """Test direct confirmation without editing."""
    print("\n\n=== Test 3: Direct Confirm ===\n")

    controller = MockSessionController()
    adapter = MCPSessionAdapter(controller)

    # Set up test input: confirm
    controller.interaction.set_inputs(["c"])

    tool_call = MCPToolCall(
        tool="http_fetch", parameters={"url": "http://example.com/robots.txt"}
    )

    choice, updated = adapter._get_user_confirmation(tool_call)
    print(f"Choice: {choice} (should be 'c' for confirm)")
    print(f"Parameters updated: {updated is not None}")


def test_parameter_types():
    """Test editing different parameter types."""
    print("\n\n=== Test 4: Parameter Type Parsing ===\n")

    controller = MockSessionController()
    adapter = MCPSessionAdapter(controller)

    # Test inputs with different types
    controller.interaction.set_inputs(
        [
            "e",  # Edit
            "10.0.0.1",  # String
            "8080",  # Integer
            "2.5",  # Float
            "true",  # Boolean
            "80,443,8080",  # List
            "",  # Done
            "c",  # Confirm
        ]
    )

    tool_call = MCPToolCall(
        tool="complex_scan",
        parameters={
            "host": "192.168.1.1",
            "port": 80,
            "timeout": 1.0,
            "verbose": False,
            "ports": [22, 80],
        },
    )

    print("Testing parameter type parsing...")
    choice, updated = adapter._get_user_confirmation(tool_call)

    if updated:
        print("\nParsed parameter types:")
        for key, value in updated.parameters.items():
            print(f"  {key}: {value} ({type(value).__name__})")


if __name__ == "__main__":
    print("Testing Enhanced Tool Confirmation\n")

    try:
        test_edit_parameters()
        test_skip_tool()
        test_direct_confirm()
        test_parameter_types()

        print("\n\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
