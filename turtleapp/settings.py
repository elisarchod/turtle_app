from typing import Optional
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv(override=True)


class BaseAppSettings(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class PineconeSettings(BaseAppSettings):
    api_key: str = Field(alias="PINECONE_API_KEY", description="Pinecone API key for vector database access")
    environment: str = Field(default="us-east-1", description="Pinecone cloud environment region")
    index_name: str = Field(alias="INDEX_NAME", default="movie-recommender-sample-200", description="Pinecone index for storing movie embeddings")


class OpenAISettings(BaseAppSettings):
    api_key: str = Field(alias="OPENAI_API_KEY", description="OpenAI API key for embeddings and completions")
    embedding_model: str = Field(alias="EMBEDDINGS_MODEL", default="text-embedding-3-large", description="OpenAI model for generating text embeddings")


class ClaudeSettings(BaseAppSettings):
    api_key: str = Field(alias="CLAUDE_API", description="Claude API key for Anthropic's Claude model")


class LangChainSettings(BaseAppSettings):
    tracing_v2: bool = Field(alias="LANGCHAIN_TRACING_V2", default=True, description="Enable LangChain tracing v2")
    endpoint: str = Field(alias="LANGCHAIN_ENDPOINT", default="https://api.smith.langchain.com", description="LangChain endpoint")
    api_key: str = Field(alias="LANGCHAIN_API_KEY", description="LangChain API key")
    project: str = Field(alias="LANGCHAIN_PROJECT", default="local_turtle_app", description="LangChain project name")
    langsmith_api_key: str = Field(alias="LANGSMITH_API_KEY", description="LangSmith API key")


class DataSettings(BaseAppSettings):
    movie_plots_path: Path = Field(
        default=Path("turtleapp/data_pipeline/data/processed/wiki_movie_plots_cleaned.csv"), 
        description="Path to the cleaned movie plots CSV file"
    )


class SMBSettings(BaseAppSettings):
    server: Optional[str] = Field(alias="SAMBA_SERVER", description="SMB server IP or hostname")
    share_path: Optional[str] = Field(alias="SAMBA_SHARE_PATH", description="SMB share path (e.g., /movies)")
    username: Optional[str] = Field(alias="SAMBA_USER", description="SMB authentication username")
    password: Optional[str] = Field(alias="SAMBA_PASSWORD", description="SMB authentication password")
    
    @property
    def credentials(self) -> dict[str, str]:
        if self.username and self.password:
            return {
                'user': self.username,
                'password': self.password
            }
        return {}


class MCPSettings(BaseAppSettings):
    """MCP server configuration (HTTP transport)."""
    qbittorrent_url: str = Field(
        alias="TURTLEAPP_MCP_QBITTORRENT_URL",
        default="http://mcp-qbittorrent:8000/mcp",
        description="HTTP URL for qBittorrent MCP server"
    )


class Settings(BaseAppSettings):
    supervisor_model: str = Field(alias="SUPERVISOR_MODEL", default="claude-3-5-sonnet-20241022", description="Model to use for supervisor agent")
    agent_model: str = Field(alias="AGENT_MODEL", default="claude-3-5-haiku-20241022", description="Model to use for regular agents")
    
    pinecone: PineconeSettings = Field(default_factory=PineconeSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    claude: ClaudeSettings = Field(default_factory=ClaudeSettings)
    langchain: LangChainSettings = Field(default_factory=LangChainSettings)
    
    data: DataSettings = Field(default_factory=DataSettings)
    smb: SMBSettings = Field(default_factory=SMBSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)


settings = Settings()
