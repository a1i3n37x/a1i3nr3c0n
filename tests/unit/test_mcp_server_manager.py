"""
Comprehensive unit tests for MCP Server Manager.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest

from alienrecon.core.mcp_server_manager import (
    MCPServerManager,
    MCPServerProcess,
    get_server_manager,
)
from tests.test_utils import MockProcess


class TestMCPServerProcess:
    """Test MCPServerProcess class."""

    def test_server_process_initialization(self):
        """Test creating a server process configuration."""
        process = MCPServerProcess(
            name="test-server", command=["python", "server.py"], port=50051
        )

        assert process.name == "test-server"
        assert process.command == ["python", "server.py"]
        assert process.port == 50051
        assert process.process is None
        assert process.log_file is None

    def test_start_success(self):
        """Test successful server start."""
        process = MCPServerProcess(
            name="test-server", command=["echo", "test"], port=50051
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            mock_process = MockProcess()

            with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
                result = process.start(log_dir)

            assert result is True
            assert process.process == mock_process
            assert process.log_file == log_dir / "test-server.log"

            # Verify Popen was called correctly
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            assert args[0] == ["echo", "test"]

    def test_start_immediate_exit(self):
        """Test handling server that exits immediately."""
        process = MCPServerProcess(name="failing-server", command=["false"], port=50051)

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            mock_process = MockProcess(returncode=1)
            mock_process._terminated = True  # Simulate immediate exit

            with patch("subprocess.Popen", return_value=mock_process):
                with patch("time.sleep"):  # Skip the wait
                    result = process.start(log_dir)

            assert result is False

    def test_start_exception(self):
        """Test handling exceptions during start."""
        process = MCPServerProcess(
            name="error-server", command=["nonexistent"], port=50051
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            with patch(
                "subprocess.Popen", side_effect=FileNotFoundError("Command not found")
            ):
                result = process.start(log_dir)

            assert result is False

    def test_stop_running_process(self):
        """Test stopping a running process."""
        process = MCPServerProcess(
            name="test-server", command=["python", "server.py"], port=50051
        )

        # Set up mock process
        mock_process = MockProcess()
        process.process = mock_process

        with patch("os.killpg") as mock_killpg:
            with patch("os.getpgid", return_value=12345):
                process.stop()

        if sys.platform != "win32":
            mock_killpg.assert_called_once_with(12345, subprocess.signal.SIGTERM)
        else:
            mock_process.terminate.assert_called_once()

    def test_stop_no_process(self):
        """Test stopping when no process exists."""
        process = MCPServerProcess(
            name="test-server", command=["python", "server.py"], port=50051
        )

        # Should not raise exception
        process.stop()

    def test_is_running(self):
        """Test checking if process is running."""
        process = MCPServerProcess(
            name="test-server", command=["python", "server.py"], port=50051
        )

        # No process
        assert process.is_running() is False

        # Running process
        mock_process = MockProcess()
        process.process = mock_process
        assert process.is_running() is True

        # Terminated process
        mock_process._terminated = True
        assert process.is_running() is False


class TestMCPServerManager:
    """Test MCP Server Manager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a test manager instance."""
        return MCPServerManager()

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.servers == {}
        assert manager.log_dir.name == "mcp_logs"
        assert manager.log_dir.parent.name == ".alienrecon"

    def test_get_server_configs_embedded(self, manager):
        """Test getting server configurations with embedded test server."""
        # Mock the test server file existence
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            configs = manager.get_server_configs()

        assert len(configs) >= 1

        # Check embedded test server
        test_server = configs[0]
        assert test_server["name"] == "embedded-test"
        assert test_server["port"] == 50051
        assert "test_mcp_server.py" in test_server["command"][1]

    def test_get_server_configs_custom_servers(self, manager):
        """Test discovering custom MCP servers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock server directories
            mcp_dir = Path(tmpdir) / "mcp_servers"
            mcp_dir.mkdir()

            server1_dir = mcp_dir / "server1"
            server1_dir.mkdir()
            (server1_dir / "server.py").touch()

            server2_dir = mcp_dir / "server2"
            server2_dir.mkdir()
            (server2_dir / "server.py").touch()

            # Patch the path calculation
            with patch(
                "pathlib.Path.parent",
                new_callable=lambda: MagicMock(
                    parent=MagicMock(parent=MagicMock(parent=Path(tmpdir)))
                ),
            ):
                with patch.object(Path, "exists", return_value=True):
                    with patch.object(
                        Path, "iterdir", return_value=[server1_dir, server2_dir]
                    ):
                        with patch.object(Path, "is_dir", return_value=True):
                            configs = manager.get_server_configs()

            # Should have embedded + 2 custom servers
            assert len(configs) >= 3

    @pytest.mark.asyncio
    async def test_start_servers_success(self, manager):
        """Test successful server startup."""
        # Mock server configs
        configs = [
            {
                "name": "test1",
                "command": ["echo", "server1"],
                "port": 50051,
                "description": "Test server 1",
            },
            {
                "name": "test2",
                "command": ["echo", "server2"],
                "port": 50052,
                "description": "Test server 2",
            },
        ]

        with patch.object(manager, "get_server_configs", return_value=configs):
            with patch.object(MCPServerProcess, "start", return_value=True):
                with patch.object(manager, "_wait_for_server", return_value=True):
                    result = await manager.start_servers()

        assert result is True
        assert len(manager.servers) == 2
        assert "test1" in manager.servers
        assert "test2" in manager.servers

    @pytest.mark.asyncio
    async def test_start_servers_partial_failure(self, manager):
        """Test handling partial server startup failure."""
        configs = [
            {
                "name": "good-server",
                "command": ["echo", "good"],
                "port": 50051,
                "description": "Good server",
            },
            {
                "name": "bad-server",
                "command": ["false"],
                "port": 50052,
                "description": "Bad server",
            },
        ]

        # Mock different results for each server
        start_results = [True, False]

        with patch.object(manager, "get_server_configs", return_value=configs):
            with patch.object(MCPServerProcess, "start", side_effect=start_results):
                with patch.object(manager, "_wait_for_server", return_value=True):
                    result = await manager.start_servers()

        assert result is True  # At least one server started
        assert len(manager.servers) == 1
        assert "good-server" in manager.servers
        assert "bad-server" not in manager.servers

    @pytest.mark.asyncio
    async def test_start_servers_all_fail(self, manager):
        """Test when all servers fail to start."""
        configs = [
            {
                "name": "fail1",
                "command": ["false"],
                "port": 50051,
                "description": "Failing server 1",
            }
        ]

        with patch.object(manager, "get_server_configs", return_value=configs):
            with patch.object(MCPServerProcess, "start", return_value=False):
                result = await manager.start_servers()

        assert result is False
        assert len(manager.servers) == 0

    @pytest.mark.asyncio
    async def test_wait_for_server_success(self, manager):
        """Test waiting for server to be ready."""
        # Mock successful health check
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await manager._wait_for_server(50051, timeout=1.0)

        assert result is True
        mock_client.get.assert_called_with("http://localhost:50051/health", timeout=1.0)

    @pytest.mark.asyncio
    async def test_wait_for_server_timeout(self, manager):
        """Test server readiness timeout."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Use very short timeout for test
            result = await manager._wait_for_server(50051, timeout=0.1)

        assert result is False

    def test_stop_all_servers(self, manager):
        """Test stopping all servers."""
        # Create mock servers
        server1 = MCPServerProcess("server1", ["cmd1"], 50051)
        server2 = MCPServerProcess("server2", ["cmd2"], 50052)

        server1.stop = Mock()
        server2.stop = Mock()

        manager.servers = {"server1": server1, "server2": server2}

        manager.stop_all_servers()

        server1.stop.assert_called_once()
        server2.stop.assert_called_once()
        assert len(manager.servers) == 0

    def test_get_running_servers(self, manager):
        """Test getting list of running servers."""
        # Create mock servers
        server1 = MCPServerProcess("running", ["cmd1"], 50051)
        server2 = MCPServerProcess("stopped", ["cmd2"], 50052)

        server1.is_running = Mock(return_value=True)
        server2.is_running = Mock(return_value=False)

        manager.servers = {"running": server1, "stopped": server2}

        running = manager.get_running_servers()

        assert running == ["running"]

    def test_check_server_logs(self, manager):
        """Test checking server logs."""
        # Create mock server with log file
        server = MCPServerProcess("test-server", ["cmd"], 50051)
        server.log_file = Path("/tmp/test.log")

        manager.servers["test-server"] = server

        # Mock log file content
        log_content = "\n".join([f"Log line {i}" for i in range(30)])

        with patch("builtins.open", mock_open(read_data=log_content)):
            with patch.object(Path, "exists", return_value=True):
                logs = manager.check_server_logs("test-server")

        # Should return last 20 lines
        assert logs is not None
        assert "Log line 29" in logs
        assert "Log line 10" in logs
        assert "Log line 9" not in logs  # Before last 20

    def test_check_server_logs_no_file(self, manager):
        """Test checking logs when file doesn't exist."""
        server = MCPServerProcess("test-server", ["cmd"], 50051)
        manager.servers["test-server"] = server

        logs = manager.check_server_logs("test-server")
        assert logs is None

    def test_check_server_logs_unknown_server(self, manager):
        """Test checking logs for unknown server."""
        logs = manager.check_server_logs("unknown-server")
        assert logs is None

    def test_singleton_manager(self):
        """Test get_server_manager returns singleton."""
        manager1 = get_server_manager()
        manager2 = get_server_manager()

        assert manager1 is manager2

    def test_atexit_registration(self):
        """Test that cleanup is registered on exit."""
        with patch("atexit.register") as mock_register:
            manager = MCPServerManager()

        mock_register.assert_called_once_with(manager.stop_all_servers)
