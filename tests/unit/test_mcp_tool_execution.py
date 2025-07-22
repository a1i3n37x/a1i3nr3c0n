"""Test MCP tool execution functionality."""

from unittest.mock import MagicMock, patch

import pytest

from alienrecon.core.mcp_client import MCPToolCall, MCPToolResult
from alienrecon.core.mcp_session_adapter import MCPSessionAdapter


class TestMCPToolExecution:
    """Test MCP tool execution in the session adapter."""

    @pytest.fixture
    def mock_session_controller(self):
        """Create a mock session controller."""
        controller = MagicMock()
        controller.get_target.return_value = "10.10.10.1"
        # Properly mock the spinner context manager
        spinner_mock = MagicMock()
        spinner_mock.__enter__ = MagicMock(return_value=spinner_mock)
        spinner_mock.__exit__ = MagicMock(return_value=None)
        controller.interaction.create_spinner.return_value = spinner_mock
        return controller

    @pytest.fixture
    def adapter(self, mock_session_controller):
        """Create MCPSessionAdapter instance."""
        return MCPSessionAdapter(mock_session_controller)

    @patch("alienrecon.core.mcp_session_adapter.get_mcp_sync_client")
    def test_execute_tool_via_mcp_with_params(self, mock_get_client, adapter):
        """Test that tool execution passes the complete MCPToolCall object."""
        # Setup mock client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create expected result
        expected_result = MCPToolResult(
            tool="nmap_scan", status="success", result={"ports": [22, 80]}, error=None
        )
        mock_client.call_tool.return_value = expected_result

        # Create tool call
        tool_call = MCPToolCall(
            tool="nmap_scan", parameters={"target": "192.168.1.1", "ports": "1-1000"}
        )

        # Execute
        result = adapter._execute_tool_via_mcp(tool_call)

        # Verify the call_tool was called with the complete MCPToolCall object
        mock_client.call_tool.assert_called_once_with(tool_call)
        assert result == expected_result

    @patch("alienrecon.core.mcp_session_adapter.get_mcp_sync_client")
    def test_execute_tool_adds_target_from_session(self, mock_get_client, adapter):
        """Test that target is added from session when not provided."""
        # Setup mock client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create tool call without target
        tool_call = MCPToolCall(tool="nmap_scan", parameters={"ports": "80,443"})

        # Execute
        adapter._execute_tool_via_mcp(tool_call)

        # Verify the call_tool was called with updated parameters
        actual_call = mock_client.call_tool.call_args[0][0]
        assert isinstance(actual_call, MCPToolCall)
        assert actual_call.tool == "nmap_scan"
        assert actual_call.parameters["target"] == "10.10.10.1"
        assert actual_call.parameters["ports"] == "80,443"

    @patch("alienrecon.core.mcp_session_adapter.get_mcp_sync_client")
    def test_execute_tool_preserves_existing_target(self, mock_get_client, adapter):
        """Test that existing target in parameters is not overwritten."""
        # Setup mock client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create tool call with target
        tool_call = MCPToolCall(
            tool="nmap_scan", parameters={"target": "192.168.1.100", "ports": "22"}
        )

        # Execute
        adapter._execute_tool_via_mcp(tool_call)

        # Verify the original target was preserved
        actual_call = mock_client.call_tool.call_args[0][0]
        assert actual_call.parameters["target"] == "192.168.1.100"

    @patch("alienrecon.core.mcp_session_adapter.get_mcp_sync_client")
    def test_execute_tool_handles_exception(self, mock_get_client, adapter):
        """Test that exceptions are handled gracefully."""
        # Setup mock client to raise exception
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.call_tool.side_effect = Exception("Connection failed")

        # Create tool call
        tool_call = MCPToolCall(tool="nmap_scan", parameters={"target": "192.168.1.1"})

        # Execute - should not raise, but return None
        result = adapter._execute_tool_via_mcp(tool_call)

        assert result is None
        # Verify error was displayed
        adapter.session_controller.interaction.display_error.assert_called_once_with(
            "Tool execution failed: Connection failed"
        )

    @patch("alienrecon.core.mcp_session_adapter.get_mcp_sync_client")
    def test_execute_tool_non_target_tool(self, mock_get_client, adapter):
        """Test execution of tool that doesn't need target."""
        # Setup mock client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create tool call for searchsploit (doesn't need target)
        tool_call = MCPToolCall(
            tool="searchsploit_query", parameters={"query": "apache 2.4"}
        )

        # Execute
        adapter._execute_tool_via_mcp(tool_call)

        # Verify target was not added
        actual_call = mock_client.call_tool.call_args[0][0]
        assert "target" not in actual_call.parameters
        assert actual_call.parameters["query"] == "apache 2.4"
