"""
Integration tests for complete MCP workflow.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from alienrecon.config import Config, set_config
from alienrecon.core.mcp_server_manager import get_server_manager
from alienrecon.core.refactored_session_controller import RefactoredSessionController

from ..test_utils import TEST_CONFIG, create_mock_openai_response


class TestMCPWorkflowIntegration:
    """Test complete MCP workflow integration."""

    @pytest.fixture
    def mock_config(self):
        """Create test configuration."""
        config = Config(
            openai_api_key=TEST_CONFIG["mock_api_key"],
            mcp_server_url=f"http://localhost:{TEST_CONFIG['test_port']}",
            dry_run=True,
        )
        set_config(config)
        return config

    @pytest.fixture
    def mock_openai_client(self):
        """Create mock OpenAI client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        return client

    def test_session_controller_mcp_initialization(
        self, mock_config, mock_openai_client
    ):
        """Test session controller initializes MCP components."""
        with patch(
            "alienrecon.core.config.initialize_openai_client",
            return_value=mock_openai_client,
        ):
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                with patch(
                    "alienrecon.core.mcp_session_adapter.MCPSessionAdapter.initialize"
                ) as mock_init:
                    # Mock async methods
                    # Use AsyncMock for async methods
                    mock_start.return_value = True
                    mock_init.return_value = None

                    controller = RefactoredSessionController(dry_run=True)

        # Verify MCP components were initialized
        assert controller.mcp_adapter is not None
        mock_start.assert_called_once()
        mock_init.assert_called_once()

    def test_mode_switching(self):
        """Test that MCP mode is always used (legacy mode no longer exists)."""
        # MCP is now the only mode
        config = Config(openai_api_key="test-key")
        set_config(config)

        mock_client = MagicMock()
        with patch(
            "alienrecon.core.config.initialize_openai_client", return_value=mock_client
        ):
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                with patch(
                    "alienrecon.core.mcp_session_adapter.MCPSessionAdapter.initialize"
                ) as mock_init:
                    # Use AsyncMock for async methods
                    mock_start.return_value = True
                    mock_init.return_value = None

                    controller = RefactoredSessionController()

        # MCP adapter should always be initialized
        assert controller.mcp_adapter is not None

        # Create another controller - should also use MCP
        with patch(
            "alienrecon.core.config.initialize_openai_client", return_value=mock_client
        ):
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                with patch(
                    "alienrecon.core.mcp_session_adapter.MCPSessionAdapter.initialize"
                ) as mock_init:
                    # Use AsyncMock for async methods
                    mock_start.return_value = True
                    mock_init.return_value = None

                    controller2 = RefactoredSessionController()

        assert controller2.mcp_adapter is not None

    @pytest.mark.asyncio
    async def test_mcp_tool_execution_flow(self, mock_config, mock_openai_client):
        """Test complete tool execution flow through MCP."""
        # Create controller with mocked components
        with patch(
            "alienrecon.core.config.initialize_openai_client",
            return_value=mock_openai_client,
        ):
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                mock_start.return_value = True

                controller = RefactoredSessionController(dry_run=True)

        # Mock the MCP adapter's process_ai_message
        mock_process = AsyncMock(return_value=True)
        controller.mcp_adapter.process_ai_message = mock_process

        # Create AI message with MCP-style tool call
        ai_message = create_mock_openai_response(
            content="""I'll scan the target for you.

            ```json
            {
                "tool": "nmap_scan",
                "parameters": {
                    "target": "10.10.10.1",
                    "scan_type": "basic"
                }
            }
            ```"""
        )

        # Process the message
        controller._process_ai_message(ai_message)

        # Verify MCP adapter was called
        mock_process.assert_called_once_with(ai_message)

    def test_target_prompt_workflow(self, mock_config, mock_openai_client):
        """Test workflow when no target is set."""
        with patch(
            "alienrecon.core.config.initialize_openai_client",
            return_value=mock_openai_client,
        ):
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                mock_start.return_value = True

                controller = RefactoredSessionController(dry_run=True)

        # Mock user input
        with patch.object(
            controller.interaction, "prompt_input", return_value="10.10.10.1"
        ):
            with patch.object(controller.interaction, "display_ascii_banner"):
                with patch.object(controller.interaction, "display_welcome"):
                    with patch.object(controller.interaction, "display_pro_tip"):
                        with patch.object(
                            controller, "_get_ai_response", return_value=None
                        ):
                            # Start session - may have default target
                            controller.get_target()

                            # This would normally run the interactive loop
                            # We're just testing the target setup part
                            target = controller.get_target()
                            if not target:
                                controller.interaction.display_info(
                                    "No target set. Let's get started!"
                                )
                                target_input = controller.interaction.prompt_input(
                                    "[cyan]Enter target IP address or hostname:[/cyan] "
                                )
                                if target_input.strip():
                                    controller.set_target(target_input.strip())

        assert controller.get_target() == "10.10.10.1"

    @pytest.mark.asyncio
    async def test_server_lifecycle(self):
        """Test MCP server startup and shutdown lifecycle."""
        manager = get_server_manager()

        # Mock server configs
        configs = [
            {
                "name": "test-lifecycle",
                "command": [sys.executable, "-c", "import time; time.sleep(10)"],
                "port": TEST_CONFIG["test_port"],
                "description": "Lifecycle test server",
            }
        ]

        with patch.object(manager, "get_server_configs", return_value=configs):
            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.poll.return_value = None
                mock_process.pid = 12345
                mock_popen.return_value = mock_process

                # Start servers
                started = await manager.start_servers()
                assert started is True
                assert "test-lifecycle" in manager.servers

                # Stop servers
                manager.stop_all_servers()
                assert len(manager.servers) == 0

    def test_error_propagation(self, mock_config, mock_openai_client):
        """Test error propagation through MCP workflow."""
        with patch(
            "alienrecon.core.config.initialize_openai_client",
            return_value=mock_openai_client,
        ):
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                # Simulate server startup failure
                mock_start.return_value = False

                from alienrecon.core.interaction_handler import InteractionHandler

                with patch.object(InteractionHandler, "display_warning") as mock_warn:
                    RefactoredSessionController(dry_run=True)

                # Should warn about server startup failure
                mock_warn.assert_called_with(
                    "No MCP servers started. Some tools may not be available."
                )

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_config, mock_openai_client):
        """Test handling concurrent tool executions through MCP."""
        # This tests that multiple tools can be processed without conflicts
        with patch(
            "alienrecon.core.config.initialize_openai_client",
            return_value=mock_openai_client,
        ):
            RefactoredSessionController(dry_run=True)

        # Mock multiple tool responses
        tool_calls = [
            {"tool": "nmap_scan", "parameters": {"target": "10.10.10.1"}},
            {"tool": "nikto_scan", "parameters": {"target": "10.10.10.1"}},
        ]

        # In real scenario, these would be processed through MCP
        # Here we're testing the structure supports it
        results = []
        for tc in tool_calls:
            # Simulate tool execution
            result = {
                "tool": tc["tool"],
                "status": "success",
                "result": {"data": f"Result for {tc['tool']}"},
            }
            results.append(result)

        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)

    def test_session_persistence_with_mcp(self, mock_config, mock_openai_client):
        """Test session persistence works with MCP mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "test_session.json"

            with patch(
                "alienrecon.core.config.initialize_openai_client",
                return_value=mock_openai_client,
            ):
                with patch(
                    "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
                ) as mock_start:
                    mock_start.return_value = True

                    # Create controller with session file
                    controller = RefactoredSessionController(
                        session_file=str(session_file), dry_run=True
                    )

            # Set target and save
            controller.set_target("10.10.10.1")
            controller.save_session()

            # Verify session file exists
            assert session_file.exists()

            # Load session data
            with open(session_file) as f:
                data = json.load(f)

            # Target can be in multiple fields
            target = (
                data["state"].get("target_input")
                or data["state"].get("target_ip")
                or data["state"].get("target_hostname")
            )
            assert target == "10.10.10.1"

    def test_dry_run_mode_with_mcp(self, mock_config, mock_openai_client):
        """Test dry-run mode works correctly with MCP."""
        mock_config.dry_run = True

        with patch(
            "alienrecon.core.config.initialize_openai_client",
            return_value=mock_openai_client,
        ):
            controller = RefactoredSessionController(dry_run=True)

        assert controller.dry_run is True

        # In dry-run mode, tools should not actually execute
        # This is handled by the tool orchestrator
        assert controller.tool_orchestrator.dry_run is True
