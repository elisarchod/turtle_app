"""Pydantic models for qBittorrent API responses."""

from typing import Optional, List, Literal, Any
from pydantic import BaseModel, ConfigDict, Field


class TorrentInfo(BaseModel):
    """Torrent information for list view."""
    model_config = ConfigDict(populate_by_name=True)

    hash: str
    name: str
    size: int
    progress: float
    dlspeed: int
    upspeed: int
    eta: int
    state: str
    category: str = ""
    save_path: str
    num_seeds: int
    num_leechs: int
    ratio: float


class TorrentProperties(BaseModel):
    """Detailed torrent properties."""
    model_config = ConfigDict(populate_by_name=True)

    save_path: str
    creation_date: int
    total_uploaded: int
    total_downloaded: int
    time_elapsed: int
    seeding_time: int
    share_ratio: float
    comment: str = ""


class TorrentFile(BaseModel):
    """Individual file within a torrent."""

    name: str
    size: int
    progress: float
    priority: int


class SearchResult(BaseModel):
    """Individual torrent search result."""

    fileName: str
    fileUrl: str
    fileSize: int
    nbSeeders: int
    nbLeechers: int
    siteUrl: str
    descrLink: Optional[str] = None


class SearchResults(BaseModel):
    """Container for search results."""

    results: List[SearchResult]
    status: str
    total: int


class Preferences(BaseModel):
    """qBittorrent application preferences."""

    save_path: str
    temp_path: str = ""
    dl_limit: int
    up_limit: int
    max_connec: int
    max_connec_per_torrent: int
    listen_port: int
    upnp: bool
    dht: bool
    max_active_downloads: int
    max_active_torrents: int
    max_active_uploads: int


# MCP Tool Response Models

class TorrentListResponse(BaseModel):
    """Response for listing torrents."""
    success: bool = Field(description="Whether the operation succeeded")
    count: Optional[int] = Field(None, description="Number of torrents returned")
    torrents: Optional[List[Any]] = Field(None, description="List of torrent objects with details")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class TorrentInfoResponse(BaseModel):
    """Response for getting torrent info."""
    success: bool = Field(description="Whether the operation succeeded")
    info: Optional[Any] = Field(None, description="Detailed torrent information including files")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class TorrentActionResponse(BaseModel):
    """Response for torrent actions (add, control)."""
    success: bool = Field(description="Whether the operation succeeded")
    message: Optional[str] = Field(None, description="Success message")
    result: Optional[Any] = Field(None, description="API response from qBittorrent")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class SearchResponse(BaseModel):
    """Response for torrent search."""
    success: bool = Field(description="Whether the operation succeeded")
    query: Optional[str] = Field(None, description="The search query used")
    results: Optional[Any] = Field(None, description="Search results with torrent details")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class PreferencesResponse(BaseModel):
    """Response for getting preferences."""
    success: bool = Field(description="Whether the operation succeeded")
    preferences: Optional[Any] = Field(None, description="qBittorrent application settings")
    error: Optional[str] = Field(None, description="Error message if operation failed")


# Type aliases for better LLM understanding
TorrentFilter = Literal["all", "downloading", "completed", "paused", "active", "inactive", "resumed", "seeding", "stalled"]
TorrentAction = Literal["pause", "resume", "delete"]
