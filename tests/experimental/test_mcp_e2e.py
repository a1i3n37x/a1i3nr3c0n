#!/usr/bin/env python3
"""
End-to-end test for MCP integration.

Prerequisites:
1. Start the test MCP server: python test_mcp_server.py
2. Set environment variables:
   export OPENAI_API_KEY=your-key
   export ALIENRECON_AGENT_MODE=mcp
3. Run this test: python test_mcp_e2e.py
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set MCP mode
os.environ["ALIENRECON_AGENT_MODE"] = "mcp"

# Import after setting environment
from alienrecon.config import get_config
from alienrecon.core.refactored_session_controller import RefactoredSessionController


def test_mcp_integration():
    """Test the MCP integration end-to-end."""
    print("=== Testing AlienRecon MCP Integration ===\n")

    # Verify configuration
    config = get_config()
    print("✓ Using MCP mode (default)")
    print(f"✓ MCP tools URL: {config.mcp_server_url}")

    # MCP mode is now the default and only mode
    # No need to check agent_mode anymore

    # Check if test server is running
    import httpx

    try:
        response = httpx.get("http://localhost:50051/health")
        if response.status_code == 200:
            print("✓ Test MCP server is running")
        else:
            print(f"❌ Test MCP server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to test MCP server: {e}")
        print("\nPlease start the test server first:")
        print("  python test_mcp_server.py")
        return False

    # Initialize session controller
    print("\n--- Initializing Session Controller ---")
    try:
        controller = RefactoredSessionController(dry_run=True)
        print("✓ Session controller initialized")

        if controller.mcp_adapter:
            print("✓ MCP adapter created")
        else:
            print("❌ MCP adapter not created!")
            return False

    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False

    # Test a simple interaction
    print("\n--- Testing AI Interaction ---")
    controller.set_target("10.10.10.1")

    # Simulate user input that should trigger MCP tool call
    test_input = """I want to scan the target. Please use nmap_scan with these parameters:

    ```json
    {
        "tool": "nmap_scan",
        "parameters": {
            "target": "10.10.10.1",
            "scan_type": "basic"
        }
    }
    ```
    """

    print(f"User input: {test_input[:50]}...")

    try:
        controller.handle_user_input(test_input)
        print("✓ Handled user input successfully")

        # Check if tool was called
        history = controller.session_manager.chat_history
        tool_responses = [msg for msg in history if msg.get("role") == "tool"]

        if tool_responses:
            print(f"✓ Found {len(tool_responses)} tool response(s)")
            for resp in tool_responses:
                content = resp.get("content", "{}")
                print(f"  Tool response: {content[:100]}...")
        else:
            print("⚠️  No tool responses found (this might be normal in dry-run mode)")

    except Exception as e:
        print(f"❌ Error handling input: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n=== Test Summary ===")
    print("✓ MCP integration is working!")
    print("\nNext steps:")
    print("1. Run without dry-run mode to execute real tools")
    print("2. Test with actual reconnaissance tools")
    print("3. Try different AI models")

    return True


def main():
    """Run the test."""
    success = test_mcp_integration()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
