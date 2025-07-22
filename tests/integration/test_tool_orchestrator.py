# tests/integration/test_tool_orchestrator.py
"""Integration tests for tool orchestrator."""

from unittest.mock import Mock, patch

import pytest

from alienrecon.core.exceptions import (
    ToolExecutionError,
    ValidationError,
)
from alienrecon.core.tool_orchestrator import ToolOrchestrator


@pytest.fixture
def orchestrator():
    """Create tool orchestrator with mocked cache."""
    with patch("alienrecon.core.tool_orchestrator.ResultCache") as mock_cache:
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None  # No cache hits by default
        mock_cache.return_value = mock_cache_instance

        orchestrator_instance = ToolOrchestrator(cache=mock_cache_instance)
        return orchestrator_instance


class TestToolOrchestrator:
    """Test tool orchestrator functionality."""

    def test_tool_registration(self, orchestrator):
        """Test tool registration and retrieval."""
        available_tools = orchestrator.get_available_tools()

        # Check that standard tools are registered
        expected_tools = ["nmap", "nikto", "ffuf", "smb", "hydra", "http_fetcher"]
        for tool in expected_tools:
            assert tool in available_tools

        # Test getting specific tool
        nmap_tool = orchestrator.get_tool("nmap")
        assert nmap_tool is not None
        assert nmap_tool.__class__.__name__ == "NmapTool"

    def test_argument_validation(self, orchestrator):
        """Test argument validation for different tools."""
        # Valid arguments
        valid_nmap_args = orchestrator.validate_tool_args(
            "nmap", {"target": "192.168.1.1", "port": "80", "arguments": "-sV"}
        )

        assert valid_nmap_args["target"] == "192.168.1.1"
        assert valid_nmap_args["port"] == 80

        # Invalid target
        with pytest.raises(ValidationError):
            orchestrator.validate_tool_args("nmap", {"target": "invalid..target"})

        # Invalid port
        with pytest.raises(ValidationError):
            orchestrator.validate_tool_args("nmap", {"port": "99999"})

    @pytest.mark.anyio
    @patch("alienrecon.tools.nmap.NmapTool.execute")
    async def test_tool_execution(self, mock_execute, orchestrator):
        """Test tool execution through orchestrator."""
        # Mock successful execution
        mock_execute.return_value = {
            "tool_name": "nmap",
            "status": "success",
            "findings": {
                "hosts": [
                    {
                        "addresses": {"ipv4": "93.184.216.34"},
                        "open_ports": [{"port": 80}],
                    }
                ]
            },
            "scan_summary": "Scan complete",
        }

        result = await orchestrator.execute_tool_async(
            "nmap", {"target": "example.com", "scan_type": "quick"}
        )

        assert result["status"] == "success"
        assert "findings" in result

    @pytest.mark.anyio
    @patch("alienrecon.core.tool_orchestrator.ToolOrchestrator.execute_tool_async")
    async def test_parallel_execution(self, mock_execute_tool_async, orchestrator):
        """Test parallel tool execution."""
        # Mock different outputs for different tools
        mock_execute_tool_async.side_effect = [
            {"tool_name": "nmap", "status": "success"},
            {"tool_name": "nikto", "status": "success"},
        ]

        tool_requests = [
            {"tool": "nmap", "args": {"target": "example.com"}},
            {"tool": "nikto", "args": {"target": "http://example.com"}},
        ]

        results = await orchestrator.execute_tools_parallel(tool_requests)

        assert len(results) == 2
        assert all(isinstance(res, dict) for res in results)

    def test_security_validation(self, orchestrator):
        """Test security validation in tool orchestrator."""
        # Test that dangerous arguments are rejected
        with pytest.raises(ValidationError):
            orchestrator.validate_tool_args("nmap", {"target": "example.com; rm -rf /"})

    @pytest.mark.anyio
    @patch("alienrecon.tools.nmap.NmapTool.execute")
    async def test_caching_behavior(self, mock_execute, orchestrator):
        """Test result caching."""
        mock_execute.return_value = {
            "status": "success",
            "findings": {},
            "scan_summary": "Scan complete",
        }

        # First execution should call the command and cache the result
        result1 = await orchestrator.execute_tool_async(
            "nmap", {"target": "example.com", "scan_type": "quick"}, use_cache=True
        )
        orchestrator.cache.set.assert_called_once()
        mock_execute.assert_called_once()

        # Set up the mock cache to return the result of the first run
        orchestrator.cache.get.return_value = result1

        # Second execution should hit the cache
        result2 = await orchestrator.execute_tool_async(
            "nmap", {"target": "example.com", "scan_type": "quick"}, use_cache=True
        )

        # Should NOT call execute again
        mock_execute.assert_called_once()
        assert result1["status"] == result2["status"]

    def test_tool_registration_custom(self, orchestrator):
        """Test registering custom tools."""
        from alienrecon.core.types import ToolResult
        from alienrecon.tools.base import CommandTool

        class CustomTool(CommandTool):
            name = "custom"
            description = "A custom tool"
            executable_name = "custom_exec"

            def build_command(self, **kwargs) -> list[str]:
                return ["echo", "hello"]

            def parse_output(
                self, stdout: str | None, stderr: str | None, **kwargs
            ) -> ToolResult:
                return {"tool_name": "custom", "status": "success", "findings": {}}

        orchestrator.register_tool("custom", CustomTool)

        assert "custom" in orchestrator.get_available_tools()
        custom_tool = orchestrator.get_tool("custom")
        assert custom_tool is not None
        assert custom_tool.name == "custom"

    @pytest.mark.anyio
    async def test_error_handling(self, orchestrator):
        """Test error handling in tool execution."""
        # Test with non-existent tool
        with pytest.raises(ToolExecutionError, match="Tool not found"):
            await orchestrator.execute_tool_async("nonexistent", {})

        # Test with invalid arguments, which should now raise a ValidationError
        with pytest.raises(ValidationError):
            await orchestrator.execute_tool_async("nmap", {"target": ""})

    def test_tool_info(self, orchestrator):
        """Test getting tool information."""
        nmap_info = orchestrator.get_tool_info("nmap")

        assert nmap_info is not None
        assert nmap_info["name"] == "nmap"

        # Test non-existent tool should return None
        assert orchestrator.get_tool_info("nonexistent") is None
