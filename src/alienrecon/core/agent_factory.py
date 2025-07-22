"""
Factory for creating MCP agents.

This module provides a factory for creating MCP-based agents.
"""

import logging
from typing import Any, Optional, Protocol

from ..config import get_config
from .mcp_agent import MCPAgent

logger = logging.getLogger(__name__)


class AgentProtocol(Protocol):
    """Protocol defining the agent interface."""

    async def process_message(
        self, user_message: str, chat_history: list
    ) -> tuple[str, Optional[Any]]:
        """Process a user message and return response with optional tool result."""
        ...

    async def initialize(self) -> None:
        """Initialize the agent."""
        ...

    async def close(self) -> None:
        """Clean up agent resources."""
        ...


class AgentFactory:
    """Factory for creating agents based on configuration."""

    @staticmethod
    def create_agent(llm_client: Any) -> AgentProtocol:
        """Create MCP agent."""
        config = get_config()
        logger.info("Creating MCP-based agent")
        return MCPAgent(llm_client, config)

    @staticmethod
    async def create_and_initialize_agent(llm_client: Any) -> AgentProtocol:
        """Create and initialize an agent."""
        agent = AgentFactory.create_agent(llm_client)
        await agent.initialize()
        return agent
