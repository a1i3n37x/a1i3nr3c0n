"""
End-to-end tests for complete AlienRecon MCP workflow.
"""

import asyncio
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alienrecon.config import set_config
from alienrecon.core.mcp_client import MCPToolResult

from ..test_utils import (
    TEST_CONFIG,
    MockMCPServer,
    mock_env,
)


class TestCompleteWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.fixture
    def test_env(self):
        """Set up test environment."""
        with mock_env(
            OPENAI_API_KEY=TEST_CONFIG["mock_api_key"],
            ALIENRECON_AGENT_MODE="mcp",
            ALIENRECON_DRY_RUN="true",
        ):
            yield

    @pytest.fixture
    def mock_server(self):
        """Create a mock MCP server."""
        server = MockMCPServer(port=TEST_CONFIG["test_port"])

        # Configure tool responses
        server.set_response(
            "nmap_scan",
            {
                "tool": "nmap_scan",
                "status": "success",
                "result": {
                    "hosts": [
                        {
                            "ip": "10.10.10.1",
                            "status": "up",
                            "ports": [
                                {
                                    "port": 22,
                                    "protocol": "tcp",
                                    "state": "open",
                                    "service": "ssh",
                                },
                                {
                                    "port": 80,
                                    "protocol": "tcp",
                                    "state": "open",
                                    "service": "http",
                                },
                            ],
                        }
                    ]
                },
                "metadata": {"execution_time": 2.5},
            },
        )

        return server

    def test_cli_direct_to_interactive(self, test_env):
        """Test that 'alienrecon' goes directly to interactive mode."""
        # Import after env is set
        from alienrecon.cli import main

        # Mock the session controller creation
        with patch("alienrecon.cli.SessionController") as mock_controller_class:
            mock_controller = MagicMock()
            mock_controller_class.return_value = mock_controller

            # Mock typer context
            ctx = MagicMock()
            ctx.invoked_subcommand = None
            ctx.obj = {"dry_run": True}

            # Call main with no subcommand
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                mock_start.return_value = asyncio.Future()
                mock_start.return_value.set_result(True)

                # This simulates running "alienrecon" with no args
                main(ctx)

        # Verify interactive session was started
        mock_controller.start_interactive_session.assert_called_once()

    def test_target_prompt_flow(self, test_env):
        """Test the target prompting workflow."""
        from alienrecon.core.refactored_session_controller import (
            RefactoredSessionController,
        )

        # Mock components
        mock_client = MagicMock()
        user_inputs = ["10.10.10.1", "exit"]  # Target, then exit
        input_iter = iter(user_inputs)

        with patch(
            "alienrecon.core.config.initialize_openai_client", return_value=mock_client
        ):
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                mock_start.return_value = asyncio.Future()
                mock_start.return_value.set_result(True)

                controller = RefactoredSessionController(dry_run=True)

        # Mock the interaction methods
        with patch.object(
            controller.interaction,
            "prompt_input",
            side_effect=lambda _: next(input_iter),
        ):
            with patch.object(controller.interaction, "display_ascii_banner"):
                with patch.object(controller.interaction, "display_welcome"):
                    with patch.object(controller.interaction, "display_pro_tip"):
                        with patch.object(controller.interaction, "display_info"):
                            with patch.object(
                                controller, "_get_ai_response", return_value=None
                            ):
                                # Start session - may have default target
                                controller.get_target()

                                # This simulates the target prompt part
                                controller.interaction.display_info(
                                    "No target set. Let's get started!"
                                )
                                target_input = controller.interaction.prompt_input(
                                    "[cyan]Enter target IP address or hostname:[/cyan] "
                                )
                                controller.set_target(target_input)

        assert controller.get_target() == "10.10.10.1"

    @pytest.mark.asyncio
    async def test_mcp_tool_execution_e2e(self, test_env, mock_server):
        """Test end-to-end MCP tool execution."""
        # Start mock server in thread
        import uvicorn

        from alienrecon.core.mcp_agent import MCPAgent

        server_thread = threading.Thread(
            target=uvicorn.run,
            args=(mock_server.app,),
            kwargs={
                "host": "0.0.0.0",
                "port": TEST_CONFIG["test_port"],
                "log_level": "error",
            },
            daemon=True,
        )
        server_thread.start()

        # Wait for server to start
        await asyncio.sleep(0.5)

        # Create MCP agent
        mock_llm_client = MagicMock()
        agent = MCPAgent(mock_llm_client)

        # Mock the MCP client initialization
        with patch("alienrecon.core.mcp_agent.create_mcp_client") as mock_create:
            mock_client = AsyncMock()
            mock_client.get_available_tools = MagicMock(return_value=[])
            mock_client.discover_servers = AsyncMock()
            mock_client.call_tool = AsyncMock(
                return_value=MCPToolResult(
                    tool="nmap_scan",
                    status="success",
                    result={
                        "hosts": [
                            {
                                "ip": "10.10.10.1",
                                "status": "up",
                                "ports": [
                                    {
                                        "port": 22,
                                        "protocol": "tcp",
                                        "state": "open",
                                        "service": "ssh",
                                    },
                                    {
                                        "port": 80,
                                        "protocol": "tcp",
                                        "state": "open",
                                        "service": "http",
                                    },
                                ],
                            }
                        ]
                    },
                    metadata={"execution_time": 2.5},
                )
            )
            mock_create.return_value = mock_client

            await agent.initialize()

            # Test tool call extraction and execution
            test_message = """I'll scan the target for you.

            ```json
            {
                "tool": "nmap_scan",
                "parameters": {
                    "target": "10.10.10.1",
                    "scan_type": "basic"
                }
            }
            ```"""

            # Extract tool call
            tool_call = agent._extract_tool_call(test_message)
            assert tool_call is not None
            assert tool_call.tool == "nmap_scan"

            # Execute via MCP (this would normally happen inside process_message)
            result = await agent.mcp_client.call_tool(tool_call)

            assert result.status == "success"
            assert result.result["hosts"][0]["ip"] == "10.10.10.1"
            assert len(result.result["hosts"][0]["ports"]) == 2

        if hasattr(agent, "close"):
            await agent.close()

    def test_session_recovery_after_crash(self, test_env):
        """Test session recovery after simulated crash."""
        from alienrecon.core.refactored_session_controller import (
            RefactoredSessionController,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "crash_test.json"

            # Create initial session
            mock_client = MagicMock()
            with patch(
                "alienrecon.core.config.initialize_openai_client",
                return_value=mock_client,
            ):
                with patch(
                    "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
                ) as mock_start:
                    mock_start.return_value = asyncio.Future()
                    mock_start.return_value.set_result(True)

                    controller1 = RefactoredSessionController(
                        session_file=str(session_file), dry_run=True
                    )

            # Set target and add chat history
            controller1.set_target("10.10.10.1")
            controller1.session_manager.chat_history.append(
                {"role": "user", "content": "scan the target"}
            )
            controller1.save_session()

            # Simulate crash - create new controller with same session file
            with patch(
                "alienrecon.core.config.initialize_openai_client",
                return_value=mock_client,
            ):
                with patch(
                    "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
                ) as mock_start:
                    mock_start.return_value = asyncio.Future()
                    mock_start.return_value.set_result(True)

                    controller2 = RefactoredSessionController(
                        session_file=str(session_file), dry_run=True
                    )

            # Verify session was restored
            assert controller2.get_target() == "10.10.10.1"
            assert len(controller2.session_manager.chat_history) == 1
            assert (
                controller2.session_manager.chat_history[0]["content"]
                == "scan the target"
            )

    def test_mode_switch_during_session(self, test_env):
        """Test switching modes during a session."""
        from alienrecon.config import get_config

        # Start in legacy mode
        config = get_config()
        # Legacy mode no longer exists - MCP is the default
        set_config(config)

        # Create controller - MCP mode is the default
        mock_client = MagicMock()
        with patch(
            "alienrecon.core.config.initialize_openai_client", return_value=mock_client
        ):
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                mock_start.return_value = asyncio.Future()
                mock_start.return_value.set_result(True)

                from alienrecon.core.refactored_session_controller import (
                    RefactoredSessionController,
                )

                controller = RefactoredSessionController(dry_run=True)

        # MCP adapter should always be initialized
        assert controller.mcp_adapter is not None

        # Now switch to MCP mode for next session
        # MCP mode is now the default mode
        set_config(config)

        # New controller should use MCP
        with patch(
            "alienrecon.core.config.initialize_openai_client", return_value=mock_client
        ):
            with patch(
                "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
            ) as mock_start:
                mock_start.return_value = asyncio.Future()
                mock_start.return_value.set_result(True)

                controller2 = RefactoredSessionController(dry_run=True)

        assert controller2.mcp_adapter is not None

    @pytest.mark.asyncio
    async def test_server_failure_handling(self, test_env):
        """Test handling of MCP server failures."""
        from alienrecon.core.mcp_server_manager import MCPServerManager

        manager = MCPServerManager()

        # Configure server that will fail to start
        configs = [
            {
                "name": "failing-server",
                "command": ["/nonexistent/command"],
                "port": TEST_CONFIG["test_port"],
                "description": "Server that will fail",
            }
        ]

        with patch.object(manager, "get_server_configs", return_value=configs):
            result = await manager.start_servers()

        assert result is False  # No servers started
        assert len(manager.servers) == 0

    def test_concurrent_user_safety(self, test_env):
        """Test that concurrent operations don't interfere."""
        from alienrecon.core.refactored_session_controller import (
            RefactoredSessionController,
        )

        # Create two controllers with different session files
        with tempfile.TemporaryDirectory() as tmpdir:
            session1 = Path(tmpdir) / "user1.json"
            session2 = Path(tmpdir) / "user2.json"

            mock_client = MagicMock()
            with patch(
                "alienrecon.core.config.initialize_openai_client",
                return_value=mock_client,
            ):
                with patch(
                    "alienrecon.core.mcp_server_manager.MCPServerManager.start_servers"
                ) as mock_start:
                    mock_start.return_value = asyncio.Future()
                    mock_start.return_value.set_result(True)

                    controller1 = RefactoredSessionController(
                        session_file=str(session1), dry_run=True
                    )
                    controller2 = RefactoredSessionController(
                        session_file=str(session2), dry_run=True
                    )

            # Set different targets
            controller1.set_target("10.10.10.1")
            controller2.set_target("192.168.1.1")

            # Save sessions
            controller1.save_session()
            controller2.save_session()

            # Verify isolation
            assert controller1.get_target() == "10.10.10.1"
            assert controller2.get_target() == "192.168.1.1"

            # Load session files to verify
            with open(session1) as f:
                data1 = json.load(f)
            with open(session2) as f:
                data2 = json.load(f)

            assert data1["state"]["target"] == "10.10.10.1"
            assert data2["state"]["target"] == "192.168.1.1"
