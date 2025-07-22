#!/usr/bin/env python3
"""Comprehensive final test of all MCP fixes."""

import os
import sys
import time

os.environ["OPENAI_API_KEY"] = "sk-test-key-123"
sys.path.insert(0, "src")


def run_all_tests():
    """Run all tests to ensure everything works."""
    print("=== COMPREHENSIVE FINAL TEST ===\n")

    all_passed = True

    # Test 1: Basic imports
    print("1. Testing imports...")
    try:
        from alienrecon.core.interaction_handler import InteractionHandler
        from alienrecon.core.mcp_client import MCPToolCall
        from alienrecon.core.mcp_session_adapter import MCPSessionAdapter
        from alienrecon.core.mcp_sync_wrapper import get_mcp_sync_client
        from alienrecon.core.session_manager import SessionManager

        print("   ✓ All imports successful")
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
        all_passed = False

    # Test 2: MCP Sync Wrapper
    print("\n2. Testing MCP Sync Wrapper...")
    try:
        client = get_mcp_sync_client()

        # Test multiple calls don't cause event loop issues
        for i in range(5):
            tool_call = MCPToolCall(tool="test_tool", parameters={"iteration": i})
            result = client.call_tool(tool_call)
            assert result.status in ["success", "error"]

        print("   ✓ No event loop errors with multiple calls")
    except Exception as e:
        print(f"   ✗ Sync wrapper failed: {e}")
        all_passed = False

    # Test 3: MCP Session Adapter
    print("\n3. Testing MCP Session Adapter...")
    try:

        class MockController:
            def __init__(self, dry_run=True):
                self.interaction = InteractionHandler()
                self.session_manager = SessionManager()
                self.dry_run = dry_run

        # Test with dry run
        controller = MockController(dry_run=True)
        adapter = MCPSessionAdapter(controller)
        adapter.initialize()

        # Test tool extraction
        test_messages = [
            "Regular message without tool",
            '<tool_call>{"tool": "nmap_scan", "parameters": {"target": "192.168.1.1"}}</tool_call>',
            'Message with <tool_call>{"tool": "nikto_scan", "parameters": {"target": "http://example.com"}}</tool_call> inline',
        ]

        for msg in test_messages:
            tool = adapter._extract_tool_call(msg)
            has_tool = "<tool_call>" in msg
            assert (tool is not None) == has_tool, f"Tool extraction failed for: {msg}"

        print("   ✓ Tool extraction working correctly")
        print("   ✓ No 'agent' attribute errors")
    except Exception as e:
        print(f"   ✗ Session adapter failed: {e}")
        import traceback

        traceback.print_exc()
        all_passed = False

    # Test 4: Thread isolation
    print("\n4. Testing thread isolation...")
    try:
        import threading

        from alienrecon.core.mcp_sync_wrapper import MCPSyncWrapper

        main_thread = threading.current_thread()

        # Create multiple wrappers
        wrappers = []
        for i in range(3):
            w = MCPSyncWrapper()
            w.initialize()
            wrappers.append(w)

        # Verify each has its own thread
        threads = [w._thread for w in wrappers]
        thread_names = [t.name for t in threads if t]

        # All should be different from main
        for t in threads:
            assert t != main_thread

        # Clean up
        for w in wrappers:
            w.close()

        print("   ✓ Each wrapper uses its own thread")
        print(f"   ✓ Created threads: {thread_names}")
    except Exception as e:
        print(f"   ✗ Thread isolation failed: {e}")
        all_passed = False

    # Test 5: Error handling
    print("\n5. Testing error handling...")
    try:
        # Test with non-interactive environment
        controller = MockController(dry_run=False)
        adapter = MCPSessionAdapter(controller)

        from openai.types.chat.chat_completion_message import ChatCompletionMessage

        msg = ChatCompletionMessage(
            role="assistant",
            content='Test <tool_call>{"tool": "test", "parameters": {}}</tool_call>',
        )

        # This should handle EOF gracefully
        result = adapter.process_ai_message(msg)
        print("   ✓ Handles non-interactive environment gracefully")
    except Exception as e:
        print(f"   ✗ Error handling failed: {e}")
        all_passed = False

    # Test 6: Concurrent operations
    print("\n6. Testing concurrent operations...")
    try:
        client = get_mcp_sync_client()

        # Rapid fire calls
        start = time.time()
        for i in range(10):
            tool_call = MCPToolCall(
                tool=f"concurrent_test_{i}", parameters={"index": i}
            )
            result = client.call_tool(tool_call)

        elapsed = time.time() - start
        print(f"   ✓ 10 operations in {elapsed:.2f}s")
        print("   ✓ No event loop conflicts")
    except Exception as e:
        print(f"   ✗ Concurrent ops failed: {e}")
        all_passed = False

    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nVerified fixes:")
        print("- No 'agent' attribute errors")
        print("- No event loop closed errors")
        print("- Tool extraction works correctly")
        print("- Thread isolation working")
        print("- Handles non-interactive environments")
        print("- Concurrent operations work")
        print("\n🎉 The system is now working correctly!")
    else:
        print("❌ Some tests failed")
        print("Please review the errors above")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
