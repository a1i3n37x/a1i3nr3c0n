"""
Comprehensive unit tests for MCP Client.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alienrecon.core.mcp_client import (
    MCPClient,
    MCPServer,
    MCPServerStatus,
    MCPToolCall,
)

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


class TestMCPServer:
    """Test MCPServer data class."""

    def test_server_initialization(self):
        """Test creating an MCP server configuration."""
        server = MCPServer(
            name="test-server",
            url="http://localhost:50051",
            description="Test server",
            tools=["tool1", "tool2"],
        )

        assert server.name == "test-server"
        assert server.url == "http://localhost:50051"
        assert server.description == "Test server"
        assert server.tools == ["tool1", "tool2"]
        assert server.status == MCPServerStatus.UNKNOWN
        assert server.error_message is None

    def test_server_with_error(self):
        """Test server with error state."""
        server = MCPServer(
            name="failing-server",
            url="http://localhost:50052",
            description="Failing server",
            tools=[],
            status=MCPServerStatus.ERROR,
            error_message="Connection refused",
        )

        assert server.status == MCPServerStatus.ERROR
        assert server.error_message == "Connection refused"


class TestMCPToolCall:
    """Test MCPToolCall model."""

    def test_tool_call_minimal(self):
        """Test creating a minimal tool call."""
        tool_call = MCPToolCall(tool="nmap_scan")

        assert tool_call.tool == "nmap_scan"
        assert tool_call.parameters == {}

    def test_tool_call_with_parameters(self):
        """Test creating a tool call with parameters."""
        params = {"target": "10.10.10.1", "scan_type": "basic"}
        tool_call = MCPToolCall(tool="nmap_scan", parameters=params)

        assert tool_call.tool == "nmap_scan"
        assert tool_call.parameters == params

    def test_tool_call_serialization(self):
        """Test tool call serialization."""
        tool_call = MCPToolCall(
            tool="test_tool", parameters={"param1": "value1", "param2": 123}
        )

        data = tool_call.model_dump()
        assert data["tool"] == "test_tool"
        assert data["parameters"]["param1"] == "value1"
        assert data["parameters"]["param2"] == 123


class TestMCPClient:
    """Test MCP Client functionality."""

    @pytest.fixture
    def mock_servers(self):
        """Create mock server configurations."""
        return [
            MCPServer(
                name="tools-server",
                url="http://localhost:50051",
                description="Tools server",
                tools=["nmap_scan", "nikto_scan"],
            ),
            MCPServer(
                name="fuzzing-server",
                url="http://localhost:50052",
                description="Fuzzing server",
                tools=["ffuf_dir", "ffuf_vhost"],
            ),
        ]

    def test_client_initialization(self, mock_servers):
        """Test client initialization with servers."""
        client = MCPClient(servers=mock_servers)

        # Check servers are registered
        assert "tools-server" in client.servers
        assert "fuzzing-server" in client.servers

        # Check tool routing
        assert client.tool_to_server["nmap_scan"] == "tools-server"
        assert client.tool_to_server["nikto_scan"] == "tools-server"
        assert client.tool_to_server["ffuf_dir"] == "fuzzing-server"
        assert client.tool_to_server["ffuf_vhost"] == "fuzzing-server"

    def test_register_server(self):
        """Test registering a server after initialization."""
        client = MCPClient()
        assert len(client.servers) == 0

        server = MCPServer(
            name="new-server",
            url="http://localhost:50053",
            description="New server",
            tools=["new_tool"],
        )

        client.register_server(server)

        assert "new-server" in client.servers
        assert client.tool_to_server["new_tool"] == "new-server"

    @pytest.mark.asyncio
    async def test_discover_servers_success(self, mock_servers):
        """Test successful server discovery."""
        client = MCPClient(servers=mock_servers)

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(
            client._client, "get", return_value=mock_response
        ) as mock_get:
            await client.discover_servers()

        # Verify health checks were made
        assert mock_get.call_count == 2
        mock_get.assert_any_call("http://localhost:50051/health")
        mock_get.assert_any_call("http://localhost:50052/health")

        # Verify server status
        assert client.servers["tools-server"].status == MCPServerStatus.CONNECTED
        assert client.servers["fuzzing-server"].status == MCPServerStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_discover_servers_failure(self, mock_servers):
        """Test server discovery with failures."""
        client = MCPClient(servers=mock_servers)

        # Mock one success and one failure
        async def mock_get(url):
            if "50051" in url:
                response = MagicMock()
                response.status_code = 200
                return response
            else:
                raise Exception("Connection refused")

        with patch.object(client._client, "get", side_effect=mock_get):
            await client.discover_servers()

        # Verify status
        assert client.servers["tools-server"].status == MCPServerStatus.CONNECTED
        assert client.servers["fuzzing-server"].status == MCPServerStatus.ERROR
        assert "Connection refused" in client.servers["fuzzing-server"].error_message

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_servers):
        """Test successful tool execution."""
        client = MCPClient(servers=mock_servers)
        client.servers["tools-server"].status = MCPServerStatus.CONNECTED

        tool_call = MCPToolCall(tool="nmap_scan", parameters={"target": "10.10.10.1"})

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {"ports": [22, 80]},
            "metadata": {"execution_time": 2.5},
        }

        with patch.object(
            client._client, "post", return_value=mock_response
        ) as mock_post:
            result = await client.call_tool(tool_call)

        # Verify request
        mock_post.assert_called_once_with(
            "http://localhost:50051/tools/nmap_scan", json=tool_call.model_dump()
        )

        # Verify result
        assert result.tool == "nmap_scan"
        assert result.status == "success"
        assert result.result["ports"] == [22, 80]
        assert result.metadata["execution_time"] == 2.5

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """Test calling an unknown tool."""
        client = MCPClient()

        tool_call = MCPToolCall(tool="unknown_tool")
        result = await client.call_tool(tool_call)

        assert result.status == "error"
        assert "No MCP server registered" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_server_not_connected(self, mock_servers):
        """Test calling tool when server is not connected."""
        client = MCPClient(servers=mock_servers)
        # Server status is UNKNOWN by default

        tool_call = MCPToolCall(tool="nmap_scan")
        result = await client.call_tool(tool_call)

        assert result.status == "error"
        assert "not connected" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_server_error(self, mock_servers):
        """Test handling server errors during tool execution."""
        client = MCPClient(servers=mock_servers)
        client.servers["tools-server"].status = MCPServerStatus.CONNECTED

        tool_call = MCPToolCall(tool="nmap_scan")

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        with patch.object(client._client, "post", return_value=mock_response):
            result = await client.call_tool(tool_call)

        assert result.status == "error"
        assert "500" in result.error
        assert "Internal server error" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_network_error(self, mock_servers):
        """Test handling network errors during tool execution."""
        client = MCPClient(servers=mock_servers)
        client.servers["tools-server"].status = MCPServerStatus.CONNECTED

        tool_call = MCPToolCall(tool="nmap_scan")

        with patch.object(
            client._client, "post", side_effect=Exception("Network error")
        ):
            result = await client.call_tool(tool_call)

        assert result.status == "error"
        assert "Network error" in result.error

    def test_get_available_tools(self, mock_servers):
        """Test getting list of available tools."""
        client = MCPClient(servers=mock_servers)

        # No tools available when servers not connected
        tools = client.get_available_tools()
        assert len(tools) == 0

        # Mark servers as connected
        client.servers["tools-server"].status = MCPServerStatus.CONNECTED
        client.servers["fuzzing-server"].status = MCPServerStatus.CONNECTED

        tools = client.get_available_tools()
        assert len(tools) == 4

        # Check tool format
        tool_names = [t["name"] for t in tools]
        assert "nmap_scan" in tool_names
        assert "nikto_scan" in tool_names
        assert "ffuf_dir" in tool_names
        assert "ffuf_vhost" in tool_names

        # Check server attribution
        nmap_tool = next(t for t in tools if t["name"] == "nmap_scan")
        assert nmap_tool["server"] == "tools-server"

    @pytest.mark.asyncio
    async def test_client_cleanup(self):
        """Test client cleanup."""
        client = MCPClient()

        # Mock the HTTP client's aclose method
        client._client.aclose = AsyncMock()

        await client.close()

        client._client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mock_servers):
        """Test handling concurrent tool calls."""
        client = MCPClient(servers=mock_servers)
        client.servers["tools-server"].status = MCPServerStatus.CONNECTED

        # Create multiple tool calls
        tool_calls = [
            MCPToolCall(tool="nmap_scan", parameters={"target": "10.10.10.1"}),
            MCPToolCall(tool="nikto_scan", parameters={"target": "10.10.10.2"}),
        ]

        # Mock responses
        async def mock_post(url, json):
            if "nmap_scan" in url:
                return MagicMock(
                    status_code=200,
                    json=lambda: {"result": {"tool": "nmap"}, "metadata": {}},
                )
            else:
                return MagicMock(
                    status_code=200,
                    json=lambda: {"result": {"tool": "nikto"}, "metadata": {}},
                )

        with patch.object(client._client, "post", side_effect=mock_post):
            # Execute tools concurrently
            results = await asyncio.gather(*[client.call_tool(tc) for tc in tool_calls])

        assert len(results) == 2
        assert results[0].result["tool"] == "nmap"
        assert results[1].result["tool"] == "nikto"
