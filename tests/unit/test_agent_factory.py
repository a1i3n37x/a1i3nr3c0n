"""Tests for the agent factory module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alienrecon.config import Config, set_config
from alienrecon.core.agent_factory import AgentFactory
from alienrecon.core.mcp_agent import MCPAgent


class TestAgentFactory:
    """Test agent factory functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create test configuration."""
        config = Config(openai_api_key="test-key", model="gpt-4")
        set_config(config)
        return config

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return MagicMock()

    def test_create_agent_returns_mcp_agent(self, mock_config, mock_llm_client):
        """Test that create_agent returns an MCP agent."""
        agent = AgentFactory.create_agent(mock_llm_client)

        assert isinstance(agent, MCPAgent)
        assert agent.llm_client == mock_llm_client
        assert agent.config == mock_config

    def test_agent_implements_protocol(self, mock_config, mock_llm_client):
        """Test that created agent implements AgentProtocol."""
        agent = AgentFactory.create_agent(mock_llm_client)

        # Check that agent has required methods
        assert hasattr(agent, "process_message")
        assert hasattr(agent, "initialize")
        assert hasattr(agent, "close")

        # Can't check isinstance with Protocol unless it's @runtime_checkable
        # Just verify the agent is the right type
        assert isinstance(agent, MCPAgent)

    @pytest.mark.asyncio
    async def test_create_and_initialize_agent(self, mock_config, mock_llm_client):
        """Test create_and_initialize_agent method."""
        # Mock the agent initialization
        with patch("alienrecon.core.mcp_agent.create_mcp_client") as mock_create:
            mock_client = AsyncMock()
            mock_client.get_available_tools = MagicMock(return_value=[])
            mock_client.discover_servers = AsyncMock()
            mock_create.return_value = mock_client

            agent = await AgentFactory.create_and_initialize_agent(mock_llm_client)

        assert isinstance(agent, MCPAgent)
        assert agent.mcp_client is not None
        mock_client.discover_servers.assert_awaited_once()

    def test_logging_on_agent_creation(self, mock_config, mock_llm_client, caplog):
        """Test that agent creation is logged."""
        import logging

        caplog.set_level(logging.INFO)

        AgentFactory.create_agent(mock_llm_client)

        assert "Creating MCP-based agent" in caplog.text

    @pytest.mark.asyncio
    async def test_agent_cleanup(self, mock_config, mock_llm_client):
        """Test that agent can be properly cleaned up."""
        # Create agent
        with patch("alienrecon.core.mcp_agent.create_mcp_client") as mock_create:
            mock_client = AsyncMock()
            mock_client.get_available_tools = MagicMock(return_value=[])
            mock_client.discover_servers = AsyncMock()
            mock_client.close = AsyncMock()
            mock_create.return_value = mock_client

            agent = await AgentFactory.create_and_initialize_agent(mock_llm_client)

            # Clean up
            await agent.close()

        # Verify cleanup was called
        mock_client.close.assert_awaited_once()
