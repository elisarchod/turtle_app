"""Configuration settings for qBittorrent MCP server."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """qBittorrent MCP server settings."""

    # qBittorrent connection settings (required)
    qbittorrent_url: str = Field(
        ...,
        description="qBittorrent Web API URL"
    )
    qbittorrent_username: str = Field(
        ...,
        description="qBittorrent Web API username"
    )
    qbittorrent_password: str = Field(
        ...,
        description="qBittorrent Web API password"
    )

    # Timeout settings
    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds"
    )

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_prefix = "TURTLEAPP_QB_"
        case_sensitive = False


# Global settings instance
settings = Settings()
