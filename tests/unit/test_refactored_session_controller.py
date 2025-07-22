"""
Comprehensive tests for RefactoredSessionController.

Tests the central orchestrator that manages state and AI interactions.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from alienrecon.config import Config
from alienrecon.core.refactored_session_controller import RefactoredSessionController


class TestRefactoredSessionController:
    """Test RefactoredSessionController functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.openai_api_key = "test-key"
        config.model = "gpt-4"
        config.data_dir = Path("/tmp/alienrecon_test")
        config.sessions_dir = Path("/tmp/alienrecon_test/sessions")
        config.cache_dir = Path("/tmp/alienrecon_test/cache")
        config.mcp_server_url = "http://localhost:50051"
        return config

    @pytest.fixture
    @patch("alienrecon.core.mcp_server_manager.MCPServerManager")
    @patch("alienrecon.core.agent_factory.AgentFactory.create_agent")
    def controller(self, mock_create_agent, mock_server_manager_class, mock_config):
        """Create controller instance."""
        # Mock server manager
        mock_server_manager = Mock()
        mock_server_manager.start_servers.return_value = True
        mock_server_manager_class.return_value = mock_server_manager

        # Mock agent
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent

        controller = RefactoredSessionController(mock_config)
        controller.agent = mock_agent

        return controller

    def test_initialization(self, controller, mock_config):
        """Test controller initialization."""
        assert controller.config == mock_config
        assert controller.session_manager is not None
        assert controller.interaction is not None
        assert controller.orchestrator is not None
        assert controller.dry_run is False

    def test_set_target(self, controller):
        """Test setting target."""
        controller.set_target("192.168.1.1")

        assert controller.session_manager.target_info["ip"] == "192.168.1.1"
        assert controller.session_manager.target_info["domain"] is None

    def test_set_target_with_domain(self, controller):
        """Test setting target with domain."""
        controller.set_target("example.com")

        assert controller.session_manager.target_info["ip"] is None
        assert controller.session_manager.target_info["domain"] == "example.com"

    def test_display_session_status(self, controller):
        """Test displaying session status."""
        # Add some test data
        controller.session_manager.target_info = {"ip": "192.168.1.1"}
        controller.session_manager.add_open_port(22, "ssh")
        controller.session_manager.add_open_port(80, "http")

        # Should not raise exception
        controller.display_session_status()

        # Verify display methods were called
        controller.interaction.display_session_status.assert_called_once()

    @patch("alienrecon.core.agent_factory.get_agent")
    def test_start_interactive_session(self, mock_get_agent, controller):
        """Test starting interactive session."""
        # Mock user inputs
        controller.interaction.prompt_input.side_effect = ["help", "exit"]

        # Mock agent responses
        mock_agent = Mock()
        mock_response = Mock()
        mock_response.content = "I can help you with reconnaissance."
        mock_agent.send_message.return_value = mock_response
        mock_get_agent.return_value = mock_agent

        # Run session
        controller.start_interactive_session()

        # Verify agent was used
        assert mock_agent.send_message.call_count >= 1

    def test_handle_user_command_exit(self, controller):
        """Test handling exit command."""
        should_continue = controller._handle_user_command("exit")
        assert should_continue is False

    def test_handle_user_command_save(self, controller):
        """Test handling save command."""
        should_continue = controller._handle_user_command("save")

        assert should_continue is True
        controller.session_manager.save_state.assert_called_once()

    def test_handle_user_command_status(self, controller):
        """Test handling status command."""
        should_continue = controller._handle_user_command("status")

        assert should_continue is True
        controller.interaction.display_session_status.assert_called()

    def test_handle_user_command_clear(self, controller):
        """Test handling clear command."""
        # Add some history
        controller.session_manager.chat_history = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "response"},
        ]

        should_continue = controller._handle_user_command("clear")

        assert should_continue is True
        assert len(controller.session_manager.chat_history) == 0

    def test_handle_user_command_help(self, controller):
        """Test handling help command."""
        should_continue = controller._handle_user_command("help")

        assert should_continue is True
        controller.interaction.display_help.assert_called_once()

    def test_save_session(self, controller):
        """Test saving session."""
        controller.save_session()

        controller.session_manager.save_state.assert_called_once()
        controller.interaction.display_success.assert_called()

    def test_load_session(self, controller):
        """Test loading session."""
        # Mock session data
        controller.session_manager.load_state.return_value = True

        controller.load_session()

        controller.session_manager.load_state.assert_called_once()
        controller.interaction.display_success.assert_called()

    def test_load_session_no_session(self, controller):
        """Test loading when no session exists."""
        controller.session_manager.load_state.return_value = False

        controller.load_session()

        controller.interaction.display_warning.assert_called()

    def test_clear_session(self, controller):
        """Test clearing session."""
        # Add test data
        controller.session_manager.chat_history = [{"role": "user", "content": "test"}]
        controller.session_manager.target_info = {"ip": "192.168.1.1"}

        controller.clear_session()

        # Verify session was cleared
        assert len(controller.session_manager.chat_history) == 0
        assert controller.session_manager.target_info["ip"] is None
        controller.interaction.display_success.assert_called()

    def test_generate_report(self, controller):
        """Test report generation."""
        with patch(
            "alienrecon.core.report_generator.ReportGenerator"
        ) as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate.return_value = "# Report\n\nTest report content"
            mock_generator_class.return_value = mock_generator

            controller.generate_report()

            mock_generator.generate.assert_called_once()
            controller.interaction.display_report.assert_called_once()

    def test_initialize_ctf_mission(self, controller):
        """Test CTF mission initialization."""
        with (
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.exists", return_value=False),
        ):
            controller.initialize_ctf_mission("htb", "box_name")

            # Verify CTF context was set
            assert controller.session_manager.ctf_context is not None
            assert controller.session_manager.ctf_context["platform"] == "htb"
            assert (
                controller.session_manager.ctf_context["box_identifier"] == "box_name"
            )

    def test_process_with_mcp(self, controller):
        """Test processing with MCP adapter."""
        # Create MCP adapter
        with patch(
            "alienrecon.core.mcp_session_adapter.MCPSessionAdapter"
        ) as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.process_ai_message.return_value = True
            mock_adapter_class.return_value = mock_adapter

            controller.mcp_adapter = mock_adapter

            # Mock AI message
            mock_message = Mock()
            mock_message.content = "Test message"

            # Process message
            tool_processed = controller._process_with_mcp(mock_message)

            assert tool_processed is True
            mock_adapter.process_ai_message.assert_called_once_with(mock_message)

    def test_set_dry_run_mode(self, controller):
        """Test setting dry-run mode."""
        controller.set_dry_run(True)

        assert controller.dry_run is True
        assert controller.orchestrator.dry_run is True
        controller.interaction.display_info.assert_called()

    def test_cleanup(self, controller):
        """Test cleanup on exit."""
        with patch(
            "alienrecon.core.mcp_server_manager.get_server_manager"
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            controller.cleanup()

            mock_manager.stop_servers.assert_called_once()
            controller.session_manager.save_state.assert_called_once()
