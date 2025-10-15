"""FastMCP tools for qBittorrent Web API."""

import logging
from typing import Annotated
from pydantic import Field
from fastmcp import FastMCP
from mcp_qbittorrent.clients.qbittorrent_client import QBittorrentClient
from mcp_qbittorrent.models.schemas import (
    TorrentListResponse,
    TorrentInfoResponse,
    TorrentActionResponse,
    SearchResponse,
    PreferencesResponse,
    TorrentFilter,
    TorrentAction
)


logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, qb_client: QBittorrentClient) -> None:
    """Register all qBittorrent tools with the FastMCP server."""

    @mcp.tool()
    async def qb_list_torrents(
        filter: Annotated[
            TorrentFilter | None,
            Field(
                None,
                description="Filter torrents by state. Use 'all' for all torrents, 'downloading' for active downloads, 'completed' for finished torrents, 'paused' for paused torrents, 'seeding' for seeding torrents"
            )
        ] = None,
        category: Annotated[
            str | None,
            Field(
                None,
                description="Filter by category name. Leave empty to see all categories",
                min_length=1,
                max_length=100
            )
        ] = None
    ) -> TorrentListResponse:
        """List all torrents with optional filtering.

        Use this tool when the user wants to see their current torrents, check download status,
        or monitor torrent progress. You can filter by state (downloading/completed/paused/etc.)
        or by category.

        Example uses:
        - "Show me all my torrents"
        - "What's currently downloading?"
        - "List completed torrents"
        - "Show torrents in the Movies category"
        """
        try:
            torrents = await qb_client.list_torrents(filter=filter, category=category)
            return TorrentListResponse(
                success=True,
                count=len(torrents),
                torrents=torrents
            )
        except Exception as e:
            logger.error(f"Error listing torrents: {e}")
            return TorrentListResponse(
                success=False,
                error=f"Failed to list torrents: {str(e)}"
            )

    @mcp.tool()
    async def qb_torrent_info(
        hash: Annotated[
            str,
            Field(
                description="The 40-character SHA-1 hash of the torrent (hexadecimal)",
                pattern=r"^[a-fA-F0-9]{40}$",
                min_length=40,
                max_length=40
            )
        ]
    ) -> TorrentInfoResponse:
        """Get detailed information for a specific torrent.

        Use this tool when the user wants detailed information about a specific torrent,
        including files, download statistics, peers, and trackers.

        Example uses:
        - "Show me details for torrent abc123..."
        - "What files are in this torrent?"
        - "Get info about the Ubuntu download"

        Note: You need the torrent hash. Get it first using qb_list_torrents.
        """
        try:
            info = await qb_client.get_torrent_info(hash=hash)
            return TorrentInfoResponse(
                success=True,
                info=info
            )
        except Exception as e:
            logger.error(f"Error getting torrent info for {hash}: {e}")
            return TorrentInfoResponse(
                success=False,
                error=f"Failed to get torrent info: {str(e)}. Ensure the hash is valid"
            )

    @mcp.tool()
    async def qb_add_torrent(
        url: Annotated[
            str,
            Field(
                description="Torrent URL (http/https) or magnet link (magnet:). Must be a valid torrent source",
                min_length=10,
                pattern=r"^(https?://|magnet:\?)"
            )
        ],
        save_path: Annotated[
            str | None,
            Field(
                None,
                description="Absolute path where torrent files will be saved. Uses qBittorrent default if not specified",
                min_length=1
            )
        ] = None,
        category: Annotated[
            str | None,
            Field(
                None,
                description="Category to organize this torrent (e.g., 'Movies', 'TV Shows', 'Software')",
                min_length=1,
                max_length=100
            )
        ] = None,
        paused: Annotated[
            bool,
            Field(
                False,
                description="If True, add torrent in paused state (won't start downloading immediately)"
            )
        ] = False
    ) -> TorrentActionResponse:
        """Add a torrent by URL or magnet link.

        Use this tool when the user wants to add a new torrent to qBittorrent.
        Supports both .torrent file URLs and magnet links.

        Example uses:
        - "Add this magnet link: magnet:?xt=..."
        - "Download this torrent: https://example.com/file.torrent"
        - "Add Ubuntu torrent to Downloads category"
        - "Add this torrent but don't start it yet"
        """
        try:
            result = await qb_client.add_torrent(
                urls=url,
                savepath=save_path,
                category=category,
                paused=paused
            )
            return TorrentActionResponse(
                success=True,
                message="Torrent added successfully",
                result=result
            )
        except Exception as e:
            logger.error(f"Error adding torrent {url}: {e}")
            return TorrentActionResponse(
                success=False,
                error=f"Failed to add torrent: {str(e)}. Check if URL/magnet is valid"
            )

    @mcp.tool()
    async def qb_control_torrent(
        hash: Annotated[
            str,
            Field(
                description="The 40-character SHA-1 hash of the torrent to control",
                pattern=r"^[a-fA-F0-9]{40}$",
                min_length=40,
                max_length=40
            )
        ],
        action: Annotated[
            TorrentAction,
            Field(
                description="Action to perform: 'pause' (stop downloading), 'resume' (start downloading), 'delete' (remove torrent)"
            )
        ],
        delete_files: Annotated[
            bool,
            Field(
                False,
                description="Only for 'delete' action: If True, also delete downloaded files from disk. If False, only remove from qBittorrent"
            )
        ] = False
    ) -> TorrentActionResponse:
        """Control a torrent: pause, resume, or delete.

        Use this tool when the user wants to manage an existing torrent.

        Example uses:
        - "Pause the Ubuntu download"
        - "Resume torrent abc123..."
        - "Delete this torrent but keep the files"
        - "Remove torrent and delete all files"

        Actions:
        - pause: Temporarily stop downloading/uploading
        - resume: Continue downloading/uploading
        - delete: Remove torrent (optionally delete files too)
        """
        try:
            result = await qb_client.control_torrent(
                hashes=hash,
                action=action,
                delete_files=delete_files
            )
            return TorrentActionResponse(
                success=True,
                message=f"Torrent {action} completed successfully",
                result=result
            )
        except Exception as e:
            logger.error(f"Error controlling torrent {hash} with action {action}: {e}")
            return TorrentActionResponse(
                success=False,
                error=f"Failed to {action} torrent: {str(e)}. Valid actions are: pause, resume, delete"
            )

    @mcp.tool()
    async def qb_search_torrents(
        query: Annotated[
            str,
            Field(
                description="Search terms (e.g., 'Ubuntu 22.04', 'open source software'). Be specific for better results",
                min_length=1,
                max_length=200
            )
        ],
        plugins: Annotated[
            str,
            Field(
                "all",
                description="Search plugins to use. Use 'all' to search all enabled plugins, or specify plugin names"
            )
        ] = "all",
        category: Annotated[
            str,
            Field(
                "all",
                description="Content category filter (all/movies/tv/music/games/anime/software/pictures/books)"
            )
        ] = "all",
        limit: Annotated[
            int,
            Field(
                100,
                description="Maximum number of results to return",
                ge=1,
                le=500
            )
        ] = 100
    ) -> SearchResponse:
        """Search for torrents using qBittorrent's built-in search plugins.

        Use this tool when the user wants to find torrents to download. This searches
        through configured torrent sites and returns results with seeders, size, and links.

        Example uses:
        - "Search for Ubuntu 22.04 torrents"
        - "Find the latest Linux distributions"
        - "Search for open source software"

        Note: qBittorrent must have search plugins installed and enabled.
        Results include name, size, seeders/leechers, and download links.
        """
        try:
            results = await qb_client.search_torrents(
                query=query,
                plugins=plugins,
                category=category,
                limit=limit
            )
            return SearchResponse(
                success=True,
                query=query,
                results=results
            )
        except Exception as e:
            logger.error(f"Error searching torrents with query '{query}': {e}")
            return SearchResponse(
                success=False,
                error=f"Search failed: {str(e)}. Ensure search plugins are installed in qBittorrent"
            )

    @mcp.tool()
    async def qb_get_preferences() -> PreferencesResponse:
        """Get qBittorrent application preferences and settings.

        Use this tool when the user wants to check qBittorrent configuration,
        download/upload limits, default paths, or connection settings.

        Example uses:
        - "What's my download speed limit?"
        - "Where are torrents saved by default?"
        - "Show qBittorrent settings"
        - "What port is qBittorrent using?"

        Returns settings like download path, speed limits, max connections, port, DHT/UPnP status, etc.
        """
        try:
            prefs = await qb_client.get_preferences()
            return PreferencesResponse(
                success=True,
                preferences=prefs
            )
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return PreferencesResponse(
                success=False,
                error=f"Failed to get preferences: {str(e)}"
            )
