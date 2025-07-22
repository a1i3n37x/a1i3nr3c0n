"""
Synchronous wrapper for MCP operations.

This module provides a synchronous interface to the async MCP client,
handling all event loop management internally.
"""

import asyncio
import logging
import threading
from typing import Optional

from .mcp_client import MCPClient, MCPToolCall, MCPToolResult, create_mcp_client

logger = logging.getLogger(__name__)


class MCPSyncWrapper:
    """Synchronous wrapper around the async MCP client."""

    def __init__(self):
        """Initialize the sync wrapper."""
        self._client: Optional[MCPClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._initialized = False

    def _ensure_event_loop(self):
        """Ensure we have a running event loop in a separate thread."""
        if self._loop is None or self._loop.is_closed():
            # Create new event loop in a separate thread
            self._loop = asyncio.new_event_loop()

            def run_loop():
                asyncio.set_event_loop(self._loop)
                self._loop.run_forever()

            self._thread = threading.Thread(target=run_loop, daemon=True)
            self._thread.start()

            # Give the loop time to start
            import time

            time.sleep(0.1)

    def initialize(self):
        """Initialize the MCP client synchronously."""
        if self._initialized:
            return

        self._ensure_event_loop()

        # Create and initialize client
        future = asyncio.run_coroutine_threadsafe(self._async_initialize(), self._loop)
        future.result()  # Wait for completion
        self._initialized = True

    async def _async_initialize(self):
        """Async initialization logic."""
        self._client = create_mcp_client()
        await self._client.discover_servers()

    def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """Call a tool synchronously."""
        if not self._initialized:
            self.initialize()

        self._ensure_event_loop()

        # Run the async call in the event loop thread
        future = asyncio.run_coroutine_threadsafe(
            self._client.call_tool(tool_call), self._loop
        )

        try:
            return future.result(timeout=30)  # 30 second timeout
        except Exception as e:
            logger.error(f"Error calling tool '{tool_call.tool}': {e}")
            return MCPToolResult(tool=tool_call.tool, status="error", error=str(e))

    def close(self):
        """Close the client and clean up resources."""
        if self._client and self._loop and not self._loop.is_closed():
            # Close the client
            future = asyncio.run_coroutine_threadsafe(self._client.close(), self._loop)
            try:
                future.result(timeout=5)
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}")

            # Stop the event loop
            self._loop.call_soon_threadsafe(self._loop.stop)

            # Wait for thread to finish
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)

        self._initialized = False


# Global instance for the application
_mcp_sync_client: Optional[MCPSyncWrapper] = None


def get_mcp_sync_client() -> MCPSyncWrapper:
    """Get or create the global MCP sync client."""
    global _mcp_sync_client
    if _mcp_sync_client is None:
        _mcp_sync_client = MCPSyncWrapper()
        _mcp_sync_client.initialize()
    return _mcp_sync_client
