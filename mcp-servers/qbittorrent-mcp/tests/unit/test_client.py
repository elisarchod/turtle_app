"""Unit tests for qBittorrent client with mocked responses."""

import pytest
from aioresponses import aioresponses

from mcp_qbittorrent.clients.qbittorrent_client import (
    QBittorrentClient,
    QBittorrentClientError,
)

BASE_URL = "http://localhost:15080"
USERNAME = "admin"
PASSWORD = "admin"


@pytest.fixture
def client():
    """Create client instance."""
    return QBittorrentClient(BASE_URL, USERNAME, PASSWORD)


class TestAuthentication:
    """Test authentication flow."""

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")
            await client.login()
            await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")
            async with client:
                assert client.session is not None
            assert client.session is None


class TestTorrentOperations:
    """Test torrent operations."""

    @pytest.mark.asyncio
    async def test_list_torrents(self, client, mock_torrent_list):
        """Test listing torrents."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")
            m.get(f"{BASE_URL}/api/v2/torrents/info", status=200, payload=mock_torrent_list)

            async with client:
                torrents = await client.list_torrents()
                assert len(torrents) == 2
                assert torrents[0]["name"] == "Ubuntu 22.04 LTS"

    @pytest.mark.asyncio
    async def test_add_torrent(self, client):
        """Test adding torrent."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.", content_type="text/plain")
            m.post(f"{BASE_URL}/api/v2/torrents/add", status=200, body="Ok.", content_type="text/plain")

            async with client:
                result = await client.add_torrent("magnet:?xt=urn:btih:abc123")
                assert result == "Ok."


class TestSearchOperations:
    """Test search operations."""

    @pytest.mark.asyncio
    async def test_search_torrents(self, client, mock_search_status, mock_search_results):
        """Test searching torrents."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.", content_type="text/plain")
            m.post(
                f"{BASE_URL}/api/v2/search/start",
                status=200,
                payload={"id": 1}
            )
            m.get(
                f"{BASE_URL}/api/v2/search/status?id=1",
                status=200,
                payload=mock_search_status
            )
            m.get(
                f"{BASE_URL}/api/v2/search/results?id=1&limit=100",
                status=200,
                payload=mock_search_results
            )
            m.post(f"{BASE_URL}/api/v2/search/delete", status=200, body="Ok.", content_type="text/plain")

            async with client:
                results = await client.search_torrents("ubuntu")
                assert results["total"] == 1
                assert len(results["results"]) == 1
                assert results["results"][0]["fileName"] == "Ubuntu 22.04 LTS Desktop"


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_api_errors(self, client):
        """Test various API error scenarios."""
        # Test unauthenticated request
        with pytest.raises(QBittorrentClientError, match="Not authenticated"):
            await client.list_torrents()

        # Test API error responses
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")
            m.get(f"{BASE_URL}/api/v2/torrents/info", status=403, body="Forbidden")

            async with client:
                with pytest.raises(QBittorrentClientError, match="Request failed with status 403"):
                    await client.list_torrents()
