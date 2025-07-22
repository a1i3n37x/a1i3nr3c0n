#!/usr/bin/env python3
"""
Test the consolidated MCP server with all tools.
"""

import asyncio
import os
import sys

import httpx

# Set MCP mode
os.environ["ALIENRECON_AGENT_MODE"] = "mcp"

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_all_tools():
    """Test various tools in the consolidated MCP server."""
    from alienrecon.core.mcp_server_manager import get_server_manager

    print("=== Testing Consolidated MCP Server ===\n")

    # Start MCP server
    print("Starting MCP server...")
    manager = get_server_manager()
    started = await manager.start_servers()

    if not started:
        print("Failed to start MCP server")
        return

    print("MCP server started successfully\n")

    async with httpx.AsyncClient() as client:
        # Test 1: FFUF Directory Enumeration (with a fake wordlist)
        print("=== Testing FFUF Directory Enumeration ===")
        try:
            response = await client.post(
                "http://localhost:50051/tools/ffuf_directory_enumeration",
                json={
                    "tool": "ffuf_directory_enumeration",
                    "parameters": {
                        "url": "http://example.com",
                        "wordlist": "/tmp/test_wordlist.txt",  # Will fail but that's ok
                    },
                },
            )
            result = response.json()
            print(f"Status: {result['status']}")
            print(f"Tool works: {'error' in result or 'result' in result}\n")
        except Exception as e:
            print(f"Error: {e}\n")

        # Test 2: SMB Enumeration
        print("=== Testing SMB Enumeration ===")
        try:
            response = await client.post(
                "http://localhost:50051/tools/smb_enumeration",
                json={"tool": "smb_enumeration", "parameters": {"target": "127.0.0.1"}},
            )
            result = response.json()
            print(f"Status: {result['status']}")
            print(f"Tool works: {'error' in result or 'result' in result}\n")
        except Exception as e:
            print(f"Error: {e}\n")

        # Test 3: Searchsploit Query
        print("=== Testing Searchsploit Query ===")
        try:
            response = await client.post(
                "http://localhost:50051/tools/searchsploit_query",
                json={
                    "tool": "searchsploit_query",
                    "parameters": {"query": "apache 2.4"},
                },
            )
            result = response.json()
            print(f"Status: {result['status']}")
            if result["status"] == "success":
                print(f"Found {result['result']['total_found']} exploits")
            print(f"Tool works: {'error' in result or 'result' in result}\n")
        except Exception as e:
            print(f"Error: {e}\n")

        # Test 4: Create Plan
        print("=== Testing Create Plan ===")
        try:
            response = await client.post(
                "http://localhost:50051/tools/create_plan",
                json={
                    "tool": "create_plan",
                    "parameters": {
                        "plan_name": "Test Recon Plan",
                        "plan_steps": [
                            {
                                "description": "Initial port scan",
                                "tool": "nmap_scan",
                                "parameters": {"target": "10.10.10.10"},
                            },
                            {
                                "description": "Web enumeration",
                                "tool": "nikto_scan",
                                "parameters": {"target": "10.10.10.10"},
                                "depends_on": [0],
                            },
                        ],
                    },
                },
            )
            result = response.json()
            print(f"Status: {result['status']}")
            if result["status"] == "success":
                print(f"Created plan with {result['metadata']['total_steps']} steps")
            print(f"Tool works: {'error' in result or 'result' in result}\n")
        except Exception as e:
            print(f"Error: {e}\n")

        # Test 5: HTTP Fetch
        print("=== Testing HTTP Fetch ===")
        try:
            response = await client.post(
                "http://localhost:50051/tools/http_fetch",
                json={
                    "tool": "http_fetch",
                    "parameters": {"url": "http://example.com"},
                },
            )
            result = response.json()
            print(f"Status: {result['status']}")
            if result["status"] == "success":
                print(f"Fetched {result['result']['body_length']} bytes")
            print(f"Tool works: {'error' in result or 'result' in result}\n")
        except Exception as e:
            print(f"Error: {e}\n")

    # Stop server
    print("Stopping MCP server...")
    manager.stop_all_servers()
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(test_all_tools())
