"""qBittorrent Web API client."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import aiohttp


logger = logging.getLogger(__name__)


class QBittorrentClientError(Exception):
    """Base exception for qBittorrent client errors."""


class AuthenticationError(QBittorrentClientError):
    """Raised when authentication fails."""


class APIError(QBittorrentClientError):
    """Raised when API request fails."""


class QBittorrentClient:
    """Async client for qBittorrent Web API."""

    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def login(self) -> None:
        """Authenticate with qBittorrent Web API."""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        async with self.session.post(
            f"{self.base_url}/api/v2/auth/login",
            data={"username": self.username, "password": self.password}
        ) as resp:
            if resp.status != 200 or await resp.text() != "Ok.":
                raise AuthenticationError(f"Authentication failed: {resp.status}")

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        """Make authenticated API request."""
        if not self.session:
            raise AuthenticationError("Not authenticated")

        async with self.session.request(method, f"{self.base_url}{endpoint}", data=data, params=params) as resp:
            if resp.status == 403:
                raise AuthenticationError("Token expired")
            if resp.status >= 400:
                raise APIError(f"API error: {resp.status}")
            return await resp.json() if "json" in resp.headers.get("Content-Type", "") else await resp.text()

    async def list_torrents(self, filter: Optional[str] = None, category: Optional[str] = None) -> List[Dict]:
        """List torrents with optional filtering."""
        params = {k: v for k, v in {"filter": filter, "category": category}.items() if v}
        return await self._request("GET", "/api/v2/torrents/info", params=params)

    async def get_torrent_info(self, hash: str) -> Dict:
        """Get detailed info for a specific torrent (properties + files)."""
        props, files = await asyncio.gather(
            self._request("GET", "/api/v2/torrents/properties", params={"hash": hash}),
            self._request("GET", "/api/v2/torrents/files", params={"hash": hash})
        )
        props["files"] = files
        return props

    async def add_torrent(self, urls: str, savepath: Optional[str] = None, category: Optional[str] = None, paused: bool = False) -> str:
        """Add torrent by URL or magnet link."""
        data = {"urls": urls}
        if savepath: data["savepath"] = savepath
        if category: data["category"] = category
        if paused: data["paused"] = "true"
        return await self._request("POST", "/api/v2/torrents/add", data=data)

    async def control_torrent(self, hashes: str, action: str, delete_files: bool = False) -> str:
        """Control torrent: pause, resume, or delete."""
        endpoints = {"pause": "/api/v2/torrents/pause", "resume": "/api/v2/torrents/resume", "delete": "/api/v2/torrents/delete"}
        if action not in endpoints:
            raise APIError(f"Invalid action: {action}")
        data = {"hashes": hashes}
        if action == "delete":
            data["deleteFiles"] = "true" if delete_files else "false"
        return await self._request("POST", endpoints[action], data=data)

    async def search_torrents(self, query: str, plugins: str = "all", category: str = "all", limit: int = 100) -> Dict:
        """Search for torrents and return results."""
        job = await self._request("POST", "/api/v2/search/start", data={"pattern": query, "plugins": plugins, "category": category})
        search_id = job.get("id")

        # Poll for completion
        for _ in range(30):
            await asyncio.sleep(1)
            status = await self._request("GET", "/api/v2/search/status", params={"id": search_id})
            if status[0]["status"] == "Stopped":
                break

        results = await self._request("GET", "/api/v2/search/results", params={"id": search_id, "limit": limit})
        await self._request("POST", "/api/v2/search/delete", data={"id": search_id})
        return results

    async def get_preferences(self) -> Dict:
        """Get qBittorrent application preferences."""
        return await self._request("GET", "/api/v2/app/preferences")
