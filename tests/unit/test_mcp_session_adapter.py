"""
Comprehensive tests for MCPSessionAdapter.

Tests the adapter that bridges MCP agents with the session controller.
"""

from unittest.mock import Mock, patch

import pytest

from alienrecon.core.mcp_client import MCPToolCall, MCPToolResult
from alienrecon.core.mcp_session_adapter import MCPSessionAdapter


class MockAIMessage:
    """Mock AI message for testing."""

    def __init__(self, content, role="assistant"):
        self.content = content
        self.role = role

    def model_dump(self):
        return {"role": self.role, "content": self.content}


class TestMCPSessionAdapter:
    """Test MCPSessionAdapter functionality."""

    @pytest.fixture
    def mock_session_controller(self):
        """Create a mock session controller."""
        controller = Mock()
        controller.dry_run = False
        controller.session_manager = Mock()
        controller.session_manager.chat_history = []
        controller.session_manager.add_open_port = Mock()
        controller.session_manager.add_web_finding = Mock()
        controller.interaction = Mock()
        controller.interaction.console = Mock()
        controller.interaction.console.print = Mock()
        controller.interaction.prompt_input = Mock(return_value="c")
        return controller

    @pytest.fixture
    def adapter(self, mock_session_controller):
        """Create MCPSessionAdapter instance."""
        return MCPSessionAdapter(mock_session_controller)

    def test_initialization(self, adapter, mock_session_controller):
        """Test adapter initialization."""
        assert adapter.session_controller == mock_session_controller
        assert adapter._tool_call_pattern is not None

    def test_extract_tool_call_valid(self, adapter):
        """Test extracting valid tool call from message."""
        content = """I'll scan the target using nmap.

        <tool_call>
        {
            "tool": "nmap_scan",
            "parameters": {
                "target": "192.168.1.1",
                "ports": "1-1000"
            }
        }
        </tool_call>"""

        tool_call = adapter._extract_tool_call(content)
        assert tool_call is not None
        assert tool_call.tool == "nmap_scan"
        assert tool_call.parameters["target"] == "192.168.1.1"
        assert tool_call.parameters["ports"] == "1-1000"

    def test_extract_tool_call_invalid_json(self, adapter):
        """Test extracting tool call with invalid JSON."""
        content = """<tool_call>
        {
            "tool": "nmap_scan",
            "invalid json
        }
        </tool_call>"""

        tool_call = adapter._extract_tool_call(content)
        assert tool_call is None

    def test_extract_tool_call_no_match(self, adapter):
        """Test extracting tool call when no tool call present."""
        content = "Just a regular message without tool calls."
        tool_call = adapter._extract_tool_call(content)
        assert tool_call is None

    def test_process_ai_message_no_tool_call(self, adapter, mock_session_controller):
        """Test processing AI message without tool call."""
        ai_message = MockAIMessage("Hello, how can I help you?")

        result = adapter.process_ai_message(ai_message)

        assert result is False
        assert len(mock_session_controller.session_manager.chat_history) == 1
        assert (
            mock_session_controller.session_manager.chat_history[0]["role"]
            == "assistant"
        )

    @patch("alienrecon.core.mcp_sync_wrapper.get_mcp_sync_client")
    def test_process_ai_message_with_tool_call_confirmed(
        self, mock_get_client, adapter, mock_session_controller
    ):
        """Test processing AI message with tool call that's confirmed."""
        # Setup
        ai_message = MockAIMessage("""I'll scan the target.
        <tool_call>{"tool": "nmap_scan", "parameters": {"target": "192.168.1.1"}}</tool_call>""")

        mock_client = Mock()
        mock_client.call_tool = Mock(
            return_value=MCPToolResult(
                tool="nmap_scan",
                status="success",
                result={"summary": "Found 3 open ports"},
                error=None,
            )
        )
        mock_get_client.return_value = mock_client

        # Execute
        result = adapter.process_ai_message(ai_message)

        # Verify
        assert result is True
        assert len(mock_session_controller.session_manager.chat_history) == 2

        # Check assistant message has tool_calls field
        assistant_msg = mock_session_controller.session_manager.chat_history[0]
        assert "tool_calls" in assistant_msg
        assert assistant_msg["tool_calls"][0]["function"]["name"] == "nmap_scan"

        # Check tool message
        tool_msg = mock_session_controller.session_manager.chat_history[1]
        assert tool_msg["role"] == "tool"
        assert tool_msg["tool_call_id"] == assistant_msg["tool_calls"][0]["id"]

    def test_process_ai_message_with_tool_call_skipped(
        self, adapter, mock_session_controller
    ):
        """Test processing AI message with tool call that's skipped."""
        ai_message = MockAIMessage("""I'll scan the target.
        <tool_call>{"tool": "nmap_scan", "parameters": {"target": "192.168.1.1"}}</tool_call>""")

        mock_session_controller.interaction.prompt_input.return_value = "s"

        result = adapter.process_ai_message(ai_message)

        assert result is True
        # Should have assistant message and skip message
        assert any(
            msg.get("content", "").startswith("User skipped tool")
            for msg in mock_session_controller.session_manager.chat_history
        )

    def test_handle_mcp_tool_result_success(self, adapter, mock_session_controller):
        """Test handling successful tool result."""
        result = MCPToolResult(
            tool="nmap_scan",
            status="success",
            result={
                "summary": {"total_hosts": 1, "hosts_up": 1, "total_open_ports": 3},
                "parsed_data": {
                    "hosts": [
                        {
                            "ports": [
                                {"port": 22, "state": "open", "service": "ssh"},
                                {"port": 80, "state": "open", "service": "http"},
                                {"port": 443, "state": "open", "service": "https"},
                            ]
                        }
                    ]
                },
            },
            error=None,
        )

        adapter._handle_mcp_tool_result(result, "test_tool_id")

        # Verify tool message added
        assert len(mock_session_controller.session_manager.chat_history) == 1
        tool_msg = mock_session_controller.session_manager.chat_history[0]
        assert tool_msg["role"] == "tool"
        assert tool_msg["tool_call_id"] == "test_tool_id"

        # Verify ports were added
        assert mock_session_controller.session_manager.add_open_port.call_count == 3

    def test_handle_mcp_tool_result_failure(self, adapter, mock_session_controller):
        """Test handling failed tool result."""
        result = MCPToolResult(
            tool="nmap_scan", status="error", result=None, error="Permission denied"
        )

        adapter._handle_mcp_tool_result(result, "test_tool_id")

        # Verify error was displayed
        mock_session_controller.interaction.display_error.assert_called_once()

    def test_process_tool_findings_nmap(self, adapter, mock_session_controller):
        """Test processing nmap findings."""
        result = {
            "parsed_data": {
                "hosts": [
                    {
                        "ports": [
                            {"port": 22, "state": "open", "service": "ssh"},
                            {"port": 80, "state": "open", "service": "http"},
                        ]
                    }
                ]
            }
        }

        adapter._process_tool_findings("nmap_scan", result)

        assert mock_session_controller.session_manager.add_open_port.call_count == 2
        mock_session_controller.session_manager.add_open_port.assert_any_call(22, "ssh")
        mock_session_controller.session_manager.add_open_port.assert_any_call(
            80, "http"
        )

    def test_process_tool_findings_ffuf(self, adapter, mock_session_controller):
        """Test processing ffuf findings."""
        result = {
            "url": "http://example.com",
            "found_directories": ["/admin", "/backup", "/config"],
        }

        adapter._process_tool_findings("ffuf_directory_enumeration", result)

        assert mock_session_controller.session_manager.add_web_finding.call_count == 3

    def test_process_tool_findings_nikto(self, adapter, mock_session_controller):
        """Test processing nikto findings."""
        result = {
            "target": "http://example.com",
            "vulnerabilities": [
                {"type": "XSS", "path": "/search"},
                {"type": "SQLi", "path": "/login"},
            ],
        }

        adapter._process_tool_findings("nikto_scan", result)

        mock_session_controller.session_manager.add_web_finding.assert_called_once_with(
            "http://example.com", "vulnerabilities", result["vulnerabilities"]
        )

    def test_dry_run_mode(self, adapter, mock_session_controller):
        """Test tool execution in dry-run mode."""
        mock_session_controller.dry_run = True

        ai_message = MockAIMessage(
            """<tool_call>{"tool": "nmap_scan", "parameters": {"target": "192.168.1.1"}}</tool_call>"""
        )

        result = adapter.process_ai_message(ai_message)

        assert result is True
        # Should display dry-run info
        mock_session_controller.interaction.display_info.assert_any_call(
            "[dim]Dry-run mode: Auto-confirming tool execution[/dim]"
        )
        mock_session_controller.interaction.display_command.assert_called_once()

    def test_get_user_confirmation_edit_parameters(
        self, adapter, mock_session_controller
    ):
        """Test parameter editing in user confirmation."""
        # Mock user inputs: edit, change target, add parameter, confirm
        mock_session_controller.interaction.prompt_input.side_effect = ["e", "c"]
        mock_session_controller.interaction.console.input.side_effect = [
            "10.0.0.1",  # New target
            "",  # Keep ports
            "fast=true",  # Add parameter
            "",  # Done adding
        ]

        tool_call = MCPToolCall(
            tool="nmap_scan", parameters={"target": "192.168.1.1", "ports": "1-1000"}
        )

        choice, updated_tool_call = adapter._get_user_confirmation(tool_call)

        assert choice == "c"
        assert updated_tool_call is not None
        assert updated_tool_call.parameters["target"] == "10.0.0.1"
        assert updated_tool_call.parameters["fast"] is True

    def test_edit_tool_parameters_type_inference(
        self, adapter, mock_session_controller
    ):
        """Test parameter type inference during editing."""
        mock_session_controller.interaction.console.input.side_effect = [
            "8080",  # Integer
            "2.5",  # Float
            "true",  # Boolean
            "80,443,8080",  # List
            "example.com",  # String
            "",  # Done
        ]

        params = {
            "port": 80,
            "timeout": 1.0,
            "verbose": False,
            "ports": [22, 80],
            "host": "localhost",
        }

        updated = adapter._edit_tool_parameters("test_tool", params)

        assert updated["port"] == 8080
        assert updated["timeout"] == 2.5
        assert updated["verbose"] is True
        assert updated["ports"] == ["80", "443", "8080"]
        assert updated["host"] == "example.com"

    def test_get_user_confirmation_quit(self, adapter, mock_session_controller):
        """Test quit option in user confirmation."""
        mock_session_controller.interaction.prompt_input.return_value = "q"

        tool_call = MCPToolCall(tool="test", parameters={})

        with pytest.raises(SystemExit):
            adapter._get_user_confirmation(tool_call)

    def test_add_to_history(self, adapter, mock_session_controller):
        """Test adding message to history."""
        adapter._add_to_history("system", "Test message")

        assert len(mock_session_controller.session_manager.chat_history) == 1
        assert (
            mock_session_controller.session_manager.chat_history[0]["role"] == "system"
        )
        assert (
            mock_session_controller.session_manager.chat_history[0]["content"]
            == "Test message"
        )
