import os
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
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent / "data_pipeline" / "data", description="Root directory for all data files")
    raw_dir: Path = Field(default_factory=lambda: Path(__file__).parent / "data_pipeline" / "data" / "raw", description="Directory for unprocessed data files")
    processed_dir: Path = Field(default_factory=lambda: Path(__file__).parent / "data_pipeline" / "data" / "processed", description="Directory for processed/cleaned data files")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)


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


class QBittorrentSettings(BaseAppSettings):
    host: Optional[str] = Field(alias="QBITTORRENT_HOST", description="qBittorrent Web UI host (e.g., http://localhost:8080)")
    username: Optional[str] = Field(alias="QBITTORRENT_USER", description="qBittorrent Web UI username")
    password: Optional[str] = Field(alias="QBITTORRENT_PASSWORD", description="qBittorrent Web UI password")
    
    @property
    def credentials(self) -> dict[str, str]:
        if self.username and self.password:
            return {
                'username': self.username,
                'password': self.password
            }
        return {}


class Settings(BaseAppSettings):
    supervisor_model: str = Field(alias="SUPERVISOR_MODEL", default="o3-2025-04-16", description="Model to use for supervisor agent")
    agent_model: str = Field(alias="AGENT_MODEL", default="o3-mini-2025-01-31", description="Model to use for regular agents")
    
    pinecone: PineconeSettings = Field(default_factory=PineconeSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    claude: ClaudeSettings = Field(default_factory=ClaudeSettings)
    langchain: LangChainSettings = Field(default_factory=LangChainSettings)
    
    data: DataSettings = Field(default_factory=DataSettings)
    smb: SMBSettings = Field(default_factory=SMBSettings)
    qbittorrent: QBittorrentSettings = Field(default_factory=QBittorrentSettings)


settings = Settings()
