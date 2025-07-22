"""
MCP (Model Context Protocol) client for AlienRecon.

This module provides the interface between AlienRecon and MCP servers,
enabling model-agnostic tool calling.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MCPServerStatus(Enum):
    """Status of an MCP server connection."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class MCPServer:
    """Configuration for an MCP server."""

    name: str
    url: str
    description: str
    tools: list[str]
    status: MCPServerStatus = MCPServerStatus.UNKNOWN
    error_message: Optional[str] = None
    tool_metadata: Optional[dict[str, Any]] = None


class MCPToolCall(BaseModel):
    """Represents a tool call request in MCP format."""

    tool: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class MCPToolResult(BaseModel):
    """Represents a tool execution result from MCP."""

    tool: str
    status: str  # "success" or "error"
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MCPClient:
    """Client for interacting with MCP servers."""

    def __init__(self, servers: Optional[list[MCPServer]] = None):
        """Initialize MCP client with server configurations."""
        self.servers: dict[str, MCPServer] = {}
        self.tool_to_server: dict[str, str] = {}
        self._client: Optional[httpx.AsyncClient] = None

        if servers:
            for server in servers:
                self.register_server(server)

    def register_server(self, server: MCPServer) -> None:
        """Register an MCP server and its tools."""
        self.servers[server.name] = server
        for tool in server.tools:
            self.tool_to_server[tool] = server.name
        logger.info(f"Registered MCP server '{server.name}' with tools: {server.tools}")

    async def discover_servers(self) -> None:
        """Discover and connect to configured MCP servers."""
        tasks = []
        for server in self.servers.values():
            tasks.append(self._check_server_health(server))

        await asyncio.gather(*tasks, return_exceptions=True)

        # After health checks, discover tools from connected servers
        for server in self.servers.values():
            if server.status == MCPServerStatus.CONNECTED:
                await self._discover_server_tools(server)

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized and valid."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _check_server_health(self, server: MCPServer) -> None:
        """Check if an MCP server is reachable and healthy."""
        try:
            client = await self._ensure_client()
            response = await client.get(f"{server.url}/health")
            if response.status_code == 200:
                server.status = MCPServerStatus.CONNECTED
                logger.info(f"MCP server '{server.name}' is healthy")
            else:
                server.status = MCPServerStatus.ERROR
                server.error_message = f"Health check returned {response.status_code}"
        except Exception as e:
            server.status = MCPServerStatus.ERROR
            server.error_message = str(e)
            logger.error(f"Failed to connect to MCP server '{server.name}': {e}")

    async def _discover_server_tools(self, server: MCPServer) -> None:
        """Discover available tools from an MCP server."""
        try:
            client = await self._ensure_client()
            response = await client.get(f"{server.url}/tools")
            if response.status_code == 200:
                data = response.json()
                tool_registry = data.get("tools", {})

                # Clear existing tools for this server
                old_tools = [
                    tool
                    for tool, srv in self.tool_to_server.items()
                    if srv == server.name
                ]
                for tool in old_tools:
                    del self.tool_to_server[tool]

                # Update server tools from registry
                server.tools = list(tool_registry.keys())
                server.tool_metadata = tool_registry  # Store full metadata

                # Update tool-to-server mapping
                for tool in server.tools:
                    self.tool_to_server[tool] = server.name

                logger.info(
                    f"Discovered {len(server.tools)} tools from '{server.name}'"
                )
                logger.debug(f"Tools: {server.tools}")
            else:
                logger.warning(
                    f"Failed to discover tools from '{server.name}': {response.status_code}"
                )
        except Exception as e:
            logger.error(f"Error discovering tools from '{server.name}': {e}")

    async def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute a tool call via the appropriate MCP server."""
        # Find the server that handles this tool
        server_name = self.tool_to_server.get(tool_call.tool)
        if not server_name:
            return MCPToolResult(
                tool=tool_call.tool,
                status="error",
                error=f"No MCP server registered for tool '{tool_call.tool}'",
            )

        server = self.servers.get(server_name)
        if not server:
            return MCPToolResult(
                tool=tool_call.tool,
                status="error",
                error=f"Server '{server_name}' not found",
            )

        if server.status != MCPServerStatus.CONNECTED:
            return MCPToolResult(
                tool=tool_call.tool,
                status="error",
                error=f"Server '{server_name}' is not connected",
            )

        # Make the tool call
        try:
            client = await self._ensure_client()
            response = await client.post(
                f"{server.url}/tools/{tool_call.tool}", json=tool_call.model_dump()
            )

            if response.status_code == 200:
                data = response.json()
                return MCPToolResult(
                    tool=tool_call.tool,
                    status="success",
                    result=data.get("result"),
                    metadata=data.get("metadata", {}),
                )
            else:
                return MCPToolResult(
                    tool=tool_call.tool,
                    status="error",
                    error=f"Server returned {response.status_code}: {response.text}",
                )

        except Exception as e:
            logger.error(f"Error calling tool '{tool_call.tool}': {e}")
            return MCPToolResult(tool=tool_call.tool, status="error", error=str(e))

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get list of all available tools across all servers."""
        tools = []
        for server in self.servers.values():
            if server.status == MCPServerStatus.CONNECTED and server.tool_metadata:
                for tool_name, metadata in server.tool_metadata.items():
                    tools.append(
                        {
                            "name": tool_name,
                            "server": server.name,
                            "category": metadata.get("category", "Uncategorized"),
                            "description": metadata.get("description", ""),
                            "parameters": metadata.get("parameters", {}),
                        }
                    )
        return tools

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Default MCP server configuration for AlienRecon
DEFAULT_MCP_SERVERS = [
    MCPServer(
        name="alienrecon-mcp",
        url="http://localhost:50051",
        description="Unified AlienRecon MCP server with all tools",
        tools=[],  # Tools will be discovered dynamically from the server
    )
]


def create_mcp_client() -> MCPClient:
    """Create an MCP client with default AlienRecon server configurations."""
    return MCPClient(servers=DEFAULT_MCP_SERVERS)
