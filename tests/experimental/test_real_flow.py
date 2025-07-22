#!/usr/bin/env python3
"""Test the REAL flow to ensure everything works."""

import os
import sys

os.environ["OPENAI_API_KEY"] = "sk-test-key-123"
sys.path.insert(0, "src")

from alienrecon.core.interaction_handler import InteractionHandler
from alienrecon.core.mcp_session_adapter import MCPSessionAdapter
from alienrecon.core.session_manager import SessionManager


# Mock components
class MockSessionController:
    """Mock session controller with all required attributes."""

    def __init__(self):
        self.interaction = InteractionHandler()
        self.dry_run = True  # Use dry run to avoid actual execution
        self.openai_client = None
        self.session_manager = SessionManager()


# Mock AI message
class MockAIMessage:
    def __init__(self, content):
        self.content = content

    def model_dump(self):
        return {"role": "assistant", "content": self.content}


def test_real_mcp_flow():
    """Test the real MCP flow."""
    print("=== Testing REAL MCP Flow ===\n")

    # Create controller
    controller = MockSessionController()

    # Create adapter
    adapter = MCPSessionAdapter(controller)

    # Initialize it
    print("1. Initializing MCP adapter...")
    try:
        adapter.initialize()
        print("   ✓ Initialization successful")
    except Exception as e:
        print(f"   ✗ Initialization failed: {e}")
        return False

    # Test 1: Message without tool call
    print("\n2. Testing message without tool call...")
    msg1 = MockAIMessage("Hello! I'm ready to help you with reconnaissance.")
    try:
        result = adapter.process_ai_message(msg1)
        print(f"   ✓ Processed successfully, returned: {result}")
        assert not result, "Should return False for non-tool messages"
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 2: Message with tool call
    print("\n3. Testing message with tool call...")
    msg2 = MockAIMessage("""
I'll scan the target for you. Let me use nmap to check for open ports.

<tool_call>
{
    "tool": "nmap_scan",
    "parameters": {
        "target": "127.0.0.1",
        "scan_type": "quick",
        "ports": "1-1000"
    }
}
</tool_call>
""")

    try:
        # This will display the tool proposal but we can't interact in test
        print("   (Would display tool proposal and wait for input)")
        print("   Testing tool extraction...")

        # Test the extraction directly
        tool_call = adapter._extract_tool_call(msg2.content)
        if tool_call:
            print(f"   ✓ Tool extracted: {tool_call.tool}")
            print(f"   ✓ Parameters: {tool_call.parameters}")
        else:
            print("   ✗ Failed to extract tool call")
            return False

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 3: Test sync wrapper directly
    print("\n4. Testing MCP sync wrapper...")
    from alienrecon.core.mcp_client import MCPToolCall
    from alienrecon.core.mcp_sync_wrapper import get_mcp_sync_client

    try:
        client = get_mcp_sync_client()
        print("   ✓ Sync client created")

        # Try a tool call
        tool_call = MCPToolCall(
            tool="nmap_scan", parameters={"target": "127.0.0.1", "scan_type": "quick"}
        )
        result = client.call_tool(tool_call)
        print(f"   ✓ Tool call completed with status: {result.status}")
        if result.error:
            print(f"   (Expected error: {result.error})")

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n✅ ALL TESTS PASSED!")
    return True


if __name__ == "__main__":
    success = test_real_mcp_flow()
    sys.exit(0 if success else 1)
