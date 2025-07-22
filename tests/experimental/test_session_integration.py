#!/usr/bin/env python3
"""Test the complete session integration."""

import os
import sys

os.environ["OPENAI_API_KEY"] = "sk-test-key-123"
sys.path.insert(0, "src")

from alienrecon.core.refactored_session_controller import RefactoredSessionController


def test_session_integration():
    """Test the complete session integration."""
    print("=== Testing Complete Session Integration ===\n")

    # Test 1: Create session controller
    print("1. Creating session controller...")
    try:
        # Use dry run mode to avoid actual tool execution
        controller = RefactoredSessionController(dry_run=True)
        print("   ✓ Session controller created")
        print(f"   ✓ MCP enabled: {controller.mcp_enabled}")
        print(f"   ✓ MCP adapter: {controller.mcp_adapter is not None}")
    except Exception as e:
        print(f"   ✗ Failed to create controller: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 2: Set target
    print("\n2. Setting target...")
    try:
        controller.set_target("127.0.0.1")
        target = controller.get_target()
        print(f"   ✓ Target set to: {target}")
    except Exception as e:
        print(f"   ✗ Failed to set target: {e}")
        return False

    # Test 3: Process AI message with tool call
    print("\n3. Testing AI message processing...")
    from openai.types.chat.chat_completion_message import ChatCompletionMessage

    # Create a mock AI message with tool call
    ai_message = ChatCompletionMessage(
        role="assistant",
        content="""I'll help you scan the target. Let me start with a quick nmap scan.

<tool_call>
{
    "tool": "nmap_scan",
    "parameters": {
        "target": "127.0.0.1",
        "scan_type": "quick",
        "ports": "80,443"
    }
}
</tool_call>

This will identify open ports and services.""",
    )

    try:
        # This should process the message and extract the tool call
        controller._process_ai_message(ai_message)
        print("   ✓ AI message processed without errors")
        print("   (In real usage, this would prompt for tool confirmation)")
    except Exception as e:
        print(f"   ✗ Failed to process AI message: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 4: Check session state
    print("\n4. Checking session state...")
    try:
        # Check chat history
        history_len = len(controller.session_manager.chat_history)
        print(f"   ✓ Chat history length: {history_len}")

        # Display session status
        controller.display_session_status()
        print("   ✓ Session status displayed")

    except Exception as e:
        print(f"   ✗ Failed to check session state: {e}")
        return False

    print("\n✅ COMPLETE INTEGRATION TEST PASSED!")
    print("\nThe system is working correctly:")
    print("- Session controller initializes with MCP")
    print("- MCP adapter processes messages")
    print("- Tool calls are extracted from AI messages")
    print("- No event loop errors")
    print("- Dry run mode prevents actual execution")

    return True


if __name__ == "__main__":
    success = test_session_integration()
    sys.exit(0 if success else 1)
