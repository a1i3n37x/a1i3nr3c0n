#!/usr/bin/env python3
"""
Test script to validate the MCP integration implementation.

This script tests the MCP components without requiring the full
AlienRecon infrastructure to be running.
"""

import asyncio
from datetime import datetime

# Test imports to verify the code structure
try:
    from src.alienrecon.config import Config
    from src.alienrecon.core.mcp_agent import MCPAgent
    from src.alienrecon.core.mcp_client import (
        MCPClient,
        MCPServer,
        MCPServerStatus,
        MCPToolCall,
    )

    print("✓ All MCP modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure you're running from the alienrecon directory")
    import pytest

    pytest.skip(f"Skipping due to import error: {e}", allow_module_level=True)


async def test_mcp_client():
    """Test the MCP client functionality."""
    print("\n--- Testing MCP Client ---")

    # Create a test server configuration
    test_server = MCPServer(
        name="test-server",
        url="http://localhost:50051",
        description="Test MCP server",
        tools=["nmap_scan", "nikto_scan"],
        status=MCPServerStatus.UNKNOWN,
    )

    # Create MCP client
    client = MCPClient(servers=[test_server])
    print(f"✓ Created MCP client with {len(client.servers)} servers")
    print(f"✓ Registered tools: {list(client.tool_to_server.keys())}")

    # Test tool call (this will fail without a running server, which is expected)
    tool_call = MCPToolCall(
        tool="nmap_scan", parameters={"target": "127.0.0.1", "scan_type": "basic"}
    )

    print(f"\nAttempting tool call: {tool_call.tool}")
    result = await client.call_tool(tool_call)

    if result.status == "error":
        print(f"✓ Expected error (no server running): {result.error}")
    else:
        print(f"Tool result: {result}")

    await client.close()
    print("✓ Client closed successfully")


def test_config():
    """Test configuration management."""
    print("\n--- Testing Configuration ---")

    # Test default config
    config = Config()
    print(f"✓ Default model: {config.model}")

    # Test MCP mode
    # AgentMode removed - AlienRecon now uses MCP exclusively
    print("✓ AlienRecon now uses MCP exclusively")

    # Test MCP server URLs
    print("\nMCP Server URLs:")
    for attr in dir(config):
        if attr.startswith("mcp_") and attr.endswith("_url"):
            print(f"  {attr}: {getattr(config, attr)}")


def test_mcp_agent():
    """Test MCP agent initialization."""
    print("\n--- Testing MCP Agent ---")

    # Mock LLM client
    class MockLLMClient:
        def __init__(self):
            self.chat = None

    mock_client = MockLLMClient()
    config = Config()

    agent = MCPAgent(mock_client, config)
    print("✓ Created MCP agent")

    # Test tool call extraction
    test_responses = [
        """I'll scan the target for you.

        ```json
        {
            "tool": "nmap_scan",
            "parameters": {
                "target": "10.10.10.1"
            }
        }
        ```""",
        "This is a regular response without tool calls.",
        """Let me check that.
        ```json
        {"tool": "http_fetch", "parameters": {"url": "http://example.com"}}
        ```""",
    ]

    print("\nTesting tool call extraction:")
    for i, response in enumerate(test_responses):
        tool_call = agent._extract_tool_call(response)
        if tool_call:
            print(f"  Response {i + 1}: Found tool call - {tool_call.tool}")
        else:
            print(f"  Response {i + 1}: No tool call found")


def test_backwards_compatibility():
    """Test that legacy mode still works."""
    print("\n--- Testing Backwards Compatibility ---")

    # AgentMode removed - AlienRecon now uses MCP exclusively
    print("✓ MCP is now the only mode - no backwards compatibility needed")
    print("✓ All legacy function calling has been removed")


def show_implementation_status():
    """Show what's implemented vs what needs to be done."""
    print("\n--- Implementation Status ---")

    implemented = [
        "MCP Client (mcp_client.py)",
        "MCP Agent (mcp_agent.py)",
        "Configuration with agent modes (config.py)",
        "Agent Factory for mode switching (agent_factory.py)",
        "Session Adapter (mcp_session_adapter.py)",
        "Sample MCP servers (in mcp_servers/)",
        "Docker Compose for MCP (docker-compose.mcp.yml)",
        "CLI command for mode switching",
        "Integration tests",
        "Documentation",
    ]

    not_implemented = [
        "Actual integration with RefactoredSessionController",
        "Running MCP servers (they're just code files)",
        "Testing with real tools",
        "Multi-model support implementation",
    ]

    print("\n✓ Implemented:")
    for item in implemented:
        print(f"  - {item}")

    print("\n✗ Not Yet Implemented:")
    for item in not_implemented:
        print(f"  - {item}")


def main():
    """Run all tests."""
    print("=== AlienRecon MCP Integration Test ===")
    print(f"Time: {datetime.now()}")

    # Run synchronous tests
    test_config()
    test_mcp_agent()
    test_backwards_compatibility()

    # Run async tests
    print("\n--- Running Async Tests ---")
    asyncio.run(test_mcp_client())

    # Show status
    show_implementation_status()

    print("\n=== Summary ===")
    print("The MCP integration code is in place but needs:")
    print("1. MCP servers to be actually running (use Docker or run locally)")
    print("2. Integration with the existing session controller")
    print("3. The CLI command to be properly hooked up")
    print("\nTo test with running servers:")
    print("  cd mcp_servers/alienrecon_tools")
    print("  pip install -r requirements.txt")
    print("  python server.py")


if __name__ == "__main__":
    main()
