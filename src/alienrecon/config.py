"""
Configuration management for AlienRecon.

Handles environment variables, feature flags, and runtime configuration.
"""

import os
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    """AlienRecon configuration."""

    # API keys
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")

    # Model configuration
    model: str = Field(default="gpt-4", description="Default model to use")

    # MCP server URL
    mcp_server_url: str = Field(
        default="http://localhost:50051", description="URL for unified MCP server"
    )

    # Directory paths
    data_dir: str = Field(
        default=os.path.expanduser("~/.alienrecon/data"),
        description="Data directory path",
    )
    cache_dir: str = Field(
        default=os.path.expanduser("~/.alienrecon/cache"),
        description="Cache directory path",
    )
    sessions_dir: str = Field(
        default=os.path.expanduser("~/.alienrecon/sessions"),
        description="Sessions directory path",
    )
    missions_dir: str = Field(
        default="./a37_missions", description="Missions directory path"
    )

    # Development settings
    dev_mode: bool = Field(default=False, description="Development mode flag")
    dry_run: bool = Field(
        default=False, description="Dry-run mode (show commands without execution)"
    )

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("ALIENRECON_MODEL", "gpt-4"),
            mcp_server_url=os.getenv("MCP_SERVER_URL", "http://localhost:50051"),
            data_dir=os.getenv(
                "ALIENRECON_DATA_DIR", os.path.expanduser("~/.alienrecon/data")
            ),
            cache_dir=os.getenv(
                "ALIENRECON_CACHE_DIR", os.path.expanduser("~/.alienrecon/cache")
            ),
            sessions_dir=os.getenv(
                "ALIENRECON_SESSIONS_DIR", os.path.expanduser("~/.alienrecon/sessions")
            ),
            missions_dir=os.getenv("ALIENRECON_MISSIONS_DIR", "./a37_missions"),
            dev_mode=os.getenv("ALIENRECON_DEV_MODE", "false").lower() == "true",
            dry_run=os.getenv("ALIENRECON_DRY_RUN", "false").lower() == "true",
        )


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
