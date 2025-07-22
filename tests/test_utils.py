"""
Test utilities and helpers for AlienRecon testing.
"""

import asyncio
import logging
import os
import subprocess
import sys
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure src is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class MockMCPServer:
    """Mock MCP server for testing."""

    def __init__(self, port: int = 50051):
        self.port = port
        self.app = FastAPI()
        self.call_count = {}
        self.responses = {}
        self._setup_routes()

    def _setup_routes(self):
        """Set up basic MCP server routes."""

        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "service": "mock-mcp-server"}

        @self.app.post("/tools/{tool_name}")
        async def execute_tool(tool_name: str, request: dict):
            self.call_count[tool_name] = self.call_count.get(tool_name, 0) + 1

            # Return configured response or default
            if tool_name in self.responses:
                return self.responses[tool_name]

            # Default responses
            return {
                "tool": tool_name,
                "status": "success",
                "result": {"message": f"Mock result for {tool_name}"},
                "metadata": {"execution_time": 0.1},
            }

    def set_response(self, tool_name: str, response: dict):
        """Configure response for a specific tool."""
        self.responses[tool_name] = response

    def get_client(self) -> TestClient:
        """Get test client for this server."""
        return TestClient(self.app)


class MockProcess:
    """Mock subprocess for testing."""

    def __init__(self, returncode: int = 0):
        self.pid = 12345
        self.returncode = returncode
        self._terminated = False
        self._killed = False

    def poll(self):
        """Check if process is running."""
        if self._terminated or self._killed:
            return self.returncode
        return None

    def terminate(self):
        """Terminate the process."""
        self._terminated = True

    def kill(self):
        """Kill the process."""
        self._killed = True

    def wait(self, timeout=None):
        """Wait for process to finish."""
        if not self._terminated and not self._killed:
            raise subprocess.TimeoutExpired("mock", timeout)


class AsyncContextManager:
    """Helper for async context management in tests."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@contextmanager
def mock_env(**kwargs):
    """Temporarily set environment variables."""
    old_env = {}
    for key, value in kwargs.items():
        old_env[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(value)

    try:
        yield
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@asynccontextmanager
async def async_timeout(seconds: float):
    """Async timeout context manager."""
    task = asyncio.current_task()

    def timeout_callback():
        if task:
            task.cancel()

    handle = asyncio.get_event_loop().call_later(seconds, timeout_callback)

    try:
        yield
    finally:
        handle.cancel()


# OpenAI response mocking removed - using MCP-based testing now


def create_test_session(target: Optional[str] = None) -> dict[str, Any]:
    """Create a test session data structure."""
    return {
        "target": target,
        "chat_history": [],
        "discovered_services": {},
        "web_findings": {},
        "credentials": [],
        "notes": [],
        "current_plan": None,
        "ctf_context": None,
    }


class LogCapture:
    """Capture log messages during tests."""

    def __init__(self, logger_name: str = "alienrecon"):
        self.logger_name = logger_name
        self.records = []
        self.handler = None

    def __enter__(self):
        logger = logging.getLogger(self.logger_name)
        self.handler = logging.Handler()
        self.handler.emit = lambda record: self.records.append(record)
        logger.addHandler(self.handler)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger = logging.getLogger(self.logger_name)
        if self.handler:
            logger.removeHandler(self.handler)

    def get_messages(self, level: Optional[int] = None) -> list[str]:
        """Get captured log messages."""
        if level is None:
            return [record.getMessage() for record in self.records]
        return [
            record.getMessage() for record in self.records if record.levelno >= level
        ]


def assert_tool_call_valid(tool_call: dict[str, Any], expected_tool: str):
    """Assert that a tool call is valid."""
    assert "tool" in tool_call
    assert tool_call["tool"] == expected_tool
    assert "parameters" in tool_call
    assert isinstance(tool_call["parameters"], dict)


def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Wait for a condition to become true."""
    import time

    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)

    return False


# Test configuration
TEST_CONFIG = {
    "test_target": "10.10.10.1",
    "test_port": 50099,  # Use high port to avoid conflicts
    "test_timeout": 5.0,
    "mock_api_key": "test-api-key-123",
}
