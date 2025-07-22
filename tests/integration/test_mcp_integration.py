"""
Integration tests for MCP (Model Context Protocol) functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alienrecon.config import Config
from alienrecon.core.mcp_agent import MCPAgent
from alienrecon.core.mcp_client import (
    MCPClient,
    MCPServer,
    MCPServerStatus,
    MCPToolCall,
    MCPToolResult,
)


@pytest.fixture
def mock_config():
    """Create a test configuration."""
    config = Config(openai_api_key="test-key", model="gpt-4")
    return config


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server configuration."""
    return MCPServer(
        name="test-server",
        url="http://localhost:50000",
        description="Test server",
        tools=["test_tool", "another_tool"],
        status=MCPServerStatus.CONNECTED,
    )


class TestMCPClient:
    """Test MCP client functionality."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_mcp_server):
        """Test MCP client initialization with servers."""
        client = MCPClient(servers=[mock_mcp_server])

        assert "test-server" in client.servers
        assert client.tool_to_server["test_tool"] == "test-server"
        assert client.tool_to_server["another_tool"] == "test-server"

        await client.close()

    @pytest.mark.asyncio
    async def test_server_discovery(self, mock_mcp_server):
        """Test server health check and discovery."""
        client = MCPClient(servers=[mock_mcp_server])

        # Mock the HTTP client creation
        mock_http_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_http_client.get.return_value = mock_response
        mock_http_client.is_closed = False

        with patch(
            "alienrecon.core.mcp_client.httpx.AsyncClient",
            return_value=mock_http_client,
        ):
            await client.discover_servers()

            assert mock_mcp_server.status == MCPServerStatus.CONNECTED
            mock_http_client.get.assert_called_with("http://localhost:50000/health")

        await client.close()

    @pytest.mark.asyncio
    async def test_tool_call_success(self, mock_mcp_server):
        """Test successful tool execution via MCP."""
        client = MCPClient(servers=[mock_mcp_server])
        mock_mcp_server.status = MCPServerStatus.CONNECTED

        tool_call = MCPToolCall(tool="test_tool", parameters={"param1": "value1"})

        # Mock the HTTP client creation
        mock_http_client = AsyncMock()
        mock_response = MagicMock()  # Use MagicMock for the response
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {"data": "test_result"},
            "metadata": {"execution_time": 1.5},
        }
        mock_http_client.post.return_value = mock_response
        mock_http_client.is_closed = False

        with patch(
            "alienrecon.core.mcp_client.httpx.AsyncClient",
            return_value=mock_http_client,
        ):
            result = await client.call_tool(tool_call)

            assert result.tool == "test_tool"
            assert result.status == "success"
            assert result.result["data"] == "test_result"
            assert result.metadata["execution_time"] == 1.5

        await client.close()

    @pytest.mark.asyncio
    async def test_tool_call_server_error(self, mock_mcp_server):
        """Test tool execution with server error."""
        client = MCPClient(servers=[mock_mcp_server])
        mock_mcp_server.status = MCPServerStatus.CONNECTED

        tool_call = MCPToolCall(tool="test_tool", parameters={})

        # Mock the HTTP client creation
        mock_http_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_http_client.post.return_value = mock_response
        mock_http_client.is_closed = False

        with patch(
            "alienrecon.core.mcp_client.httpx.AsyncClient",
            return_value=mock_http_client,
        ):
            result = await client.call_tool(tool_call)

            assert result.tool == "test_tool"
            assert result.status == "error"
            assert "500" in result.error

        await client.close()

    @pytest.mark.asyncio
    async def test_tool_call_unknown_tool(self):
        """Test calling a tool that's not registered."""
        client = MCPClient(servers=[])

        tool_call = MCPToolCall(tool="unknown_tool", parameters={})

        result = await client.call_tool(tool_call)

        assert result.status == "error"
        assert "No MCP server registered" in result.error

        await client.close()


class TestMCPAgent:
    """Test MCP agent functionality."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_config):
        """Test MCP agent initialization."""
        mock_llm_client = MagicMock()
        agent = MCPAgent(mock_llm_client, mock_config)

        # Mock the MCP client
        mock_client = AsyncMock()
        mock_client.discover_servers = AsyncMock()

        # Mock create_mcp_client to return our mock client
        with patch(
            "alienrecon.core.mcp_agent.create_mcp_client", return_value=mock_client
        ):
            # Also mock get_available_tools
            mock_client.get_available_tools = MagicMock(return_value=[])

            await agent.initialize()

            assert agent.mcp_client is not None
            mock_client.discover_servers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_message_with_tool_call(self, mock_config):
        """Test processing a message that triggers a tool call."""
        mock_llm_client = MagicMock()
        agent = MCPAgent(mock_llm_client, mock_config)

        # Mock MCP client
        agent.mcp_client = AsyncMock()
        mock_result = MCPToolResult(
            tool="nmap_scan", status="success", result={"ports": [22, 80, 443]}
        )
        agent.mcp_client.call_tool.return_value = mock_result

        # Mock LLM response with tool call
        llm_response = """
        I'll scan the target for you.

        ```json
        {
            "tool": "nmap_scan",
            "parameters": {
                "target": "10.10.10.1"
            }
        }
        ```
        """

        with patch.object(agent, "_get_llm_response") as mock_llm:
            mock_llm.return_value = llm_response

            response, tool_result = await agent.process_message("Scan 10.10.10.1", [])

            assert tool_result is not None
            assert tool_result.tool == "nmap_scan"
            assert tool_result.status == "success"
            assert "✓ Executed nmap_scan" in response

    @pytest.mark.asyncio
    async def test_process_message_no_tool_call(self, mock_config):
        """Test processing a regular conversational message."""
        mock_llm_client = MagicMock()
        agent = MCPAgent(mock_llm_client, mock_config)

        # Mock LLM response without tool call
        llm_response = "I can help you with reconnaissance tasks."

        with patch.object(agent, "_get_llm_response") as mock_llm:
            mock_llm.return_value = llm_response

            response, tool_result = await agent.process_message("What can you do?", [])

            assert tool_result is None
            assert response == llm_response

    def test_extract_tool_call_valid_json(self, mock_config):
        """Test extracting tool call from valid JSON in response."""
        agent = MCPAgent(MagicMock(), mock_config)

        response = """
        Let me scan that for you.

        ```json
        {
            "tool": "nmap_scan",
            "parameters": {
                "target": "192.168.1.1",
                "scan_type": "basic"
            }
        }
        ```
        """

        tool_call = agent._extract_tool_call(response)

        assert tool_call is not None
        assert tool_call.tool == "nmap_scan"
        assert tool_call.parameters["target"] == "192.168.1.1"
        assert tool_call.parameters["scan_type"] == "basic"

    def test_extract_tool_call_invalid_json(self, mock_config):
        """Test extracting tool call from invalid JSON."""
        agent = MCPAgent(MagicMock(), mock_config)

        response = """
        ```json
        {invalid json}
        ```
        """

        tool_call = agent._extract_tool_call(response)
        assert tool_call is None

    def test_extract_tool_call_no_json(self, mock_config):
        """Test extracting tool call when no JSON is present."""
        agent = MCPAgent(MagicMock(), mock_config)

        response = "This is just a regular response."

        tool_call = agent._extract_tool_call(response)
        assert tool_call is None


class TestMCPIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_full_tool_execution_flow(self, mock_config):
        """Test complete flow from user input to tool execution."""
        # This would be an integration test with actual servers running
        # For now, we'll mock the components

        mock_llm_client = MagicMock()
        agent = MCPAgent(mock_llm_client, mock_config)

        # Set up mocks
        agent.mcp_client = AsyncMock()
        agent.mcp_client.get_available_tools.return_value = [
            {"name": "nmap_scan", "server": "test", "description": "Port scanner"}
        ]

        # Simulate successful tool execution
        tool_result = MCPToolResult(
            tool="nmap_scan",
            status="success",
            result={
                "hosts": [
                    {
                        "ip": "10.10.10.1",
                        "ports": [
                            {"port": 22, "service": "ssh", "state": "open"},
                            {"port": 80, "service": "http", "state": "open"},
                        ],
                    }
                ]
            },
            metadata={"execution_time": 2.5},
        )
        agent.mcp_client.call_tool.return_value = tool_result

        # Mock LLM to return tool call
        with patch.object(agent, "_get_llm_response") as mock_llm:
            mock_llm.return_value = """
            I'll scan the target for open ports.

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

            response, result = await agent.process_message(
                "Scan 10.10.10.1 for open ports", []
            )

            # Verify the flow
            assert result is not None
            assert result.status == "success"
            assert len(result.result["hosts"][0]["ports"]) == 2
            assert "✓ Executed nmap_scan" in response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
