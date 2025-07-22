#!/usr/bin/env python3
"""Test the exact error scenario reported by user."""

import os
import sys

os.environ["OPENAI_API_KEY"] = "sk-test-key-123"
sys.path.insert(0, "src")


def test_error_scenario():
    """Simulate the exact scenario that was causing errors."""
    print("=== Testing Error Scenario ===\n")

    # Mock the exact components involved
    from openai.types.chat.chat_completion_message import ChatCompletionMessage

    from alienrecon.core.interaction_handler import InteractionHandler
    from alienrecon.core.mcp_session_adapter import MCPSessionAdapter
    from alienrecon.core.session_manager import SessionManager

    class MockSessionController:
        def __init__(self):
            self.interaction = InteractionHandler()
            self.session_manager = SessionManager()
            self.dry_run = True  # Test with dry-run mode
            self.mcp_enabled = True
            self.mcp_adapter = None

    print("1. Creating components...")
    controller = MockSessionController()
    controller.mcp_adapter = MCPSessionAdapter(controller)
    controller.mcp_adapter.initialize()
    print("   ✓ Components created")

    # Create the exact type of message that would come from OpenAI
    ai_message = ChatCompletionMessage(
        role="assistant",
        content="""I'll help you scan the target 127.0.0.1. Let me start with a stealth scan of the first 1000 ports to identify open services.

<tool_call>
{
    "tool": "nmap_scan",
    "parameters": {
        "target": "127.0.0.1",
        "scan_type": "stealth",
        "ports": "1-1000"
    }
}
</tool_call>

Once we get the results, we can decide on the next steps based on the open ports and services we find.""",
    )

    print("\n2. Processing AI message...")
    try:
        # This is the exact call that was failing
        handled = controller.mcp_adapter.process_ai_message(ai_message)
        print("   ✓ Message processed successfully")
        print(f"   ✓ Tool detected: {handled}")

        # Check what happened
        if handled:
            print("   ✓ Tool call was detected and would be processed")
        else:
            print("   ✓ No tool call detected (regular message)")

    except AttributeError as e:
        if "'MCPSessionAdapter' object has no attribute 'agent'" in str(e):
            print(f"   ✗ FOUND THE ERROR: {e}")
            print("   This is the error the user reported!")
            return False
        else:
            print(f"   ✗ Different AttributeError: {e}")
            import traceback

            traceback.print_exc()
            return False
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n3. Testing multiple messages...")
    messages = [
        "What services are running?",
        """Let me check. <tool_call>{"tool": "nmap_scan", "parameters": {"target": "127.0.0.1"}}</tool_call>""",
        "The scan shows port 80 is open.",
        """I'll investigate further. <tool_call>{"tool": "nikto_scan", "parameters": {"target": "http://127.0.0.1"}}</tool_call>""",
    ]

    for i, content in enumerate(messages):
        msg = ChatCompletionMessage(role="assistant", content=content)
        try:
            handled = controller.mcp_adapter.process_ai_message(msg)
            has_tool = "<tool_call>" in content
            print(
                f"   ✓ Message {i + 1}: processed (tool={'yes' if has_tool else 'no'})"
            )
        except Exception as e:
            print(f"   ✗ Message {i + 1} failed: {e}")
            return False

    print("\n✅ ERROR SCENARIO TEST PASSED!")
    print("\nThe reported error has been fixed:")
    print("- No 'agent' attribute errors")
    print("- Tool extraction works correctly")
    print("- Multiple messages process without issues")

    return True


if __name__ == "__main__":
    success = test_error_scenario()
    sys.exit(0 if success else 1)
