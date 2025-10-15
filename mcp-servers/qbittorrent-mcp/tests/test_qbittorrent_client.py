"""Unit tests for qBittorrent client with mocked responses."""

import pytest
from aioresponses import aioresponses

from mcp_qbittorrent.clients.qbittorrent_client import (
    QBittorrentClient,
    AuthenticationError,
    APIError
)
from tests.fixtures import (
    mock_torrent_list,
    mock_torrent_properties,
    mock_torrent_files,
    mock_search_results,
    mock_search_status,
    mock_preferences
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
    async def test_login_failure(self, client):
        """Test failed login."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=403, body="Fails.")
            with pytest.raises(AuthenticationError):
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
    async def test_list_torrents_with_filter(self, client, mock_torrent_list):
        """Test listing torrents with filter."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")
            m.get(
                f"{BASE_URL}/api/v2/torrents/info?filter=downloading",
                status=200,
                payload=[mock_torrent_list[0]]
            )

            async with client:
                torrents = await client.list_torrents(filter="downloading")
                assert len(torrents) == 1
                assert torrents[0]["state"] == "downloading"

    @pytest.mark.asyncio
    async def test_get_torrent_info(self, client, mock_torrent_properties, mock_torrent_files):
        """Test getting torrent info."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")
            m.get(
                f"{BASE_URL}/api/v2/torrents/properties?hash=abc123",
                status=200,
                payload=mock_torrent_properties
            )
            m.get(
                f"{BASE_URL}/api/v2/torrents/files?hash=abc123",
                status=200,
                payload=mock_torrent_files
            )

            async with client:
                info = await client.get_torrent_info("abc123")
                assert info["save_path"] == "/downloads"
                assert "files" in info
                assert len(info["files"]) == 1

    @pytest.mark.asyncio
    async def test_add_torrent(self, client):
        """Test adding torrent."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.", content_type="text/plain")
            m.post(f"{BASE_URL}/api/v2/torrents/add", status=200, body="Ok.", content_type="text/plain")

            async with client:
                result = await client.add_torrent("magnet:?xt=urn:btih:abc123")
                assert result == "Ok."

    @pytest.mark.asyncio
    async def test_add_torrent_with_options(self, client):
        """Test adding torrent with options."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.", content_type="text/plain")
            m.post(f"{BASE_URL}/api/v2/torrents/add", status=200, body="Ok.", content_type="text/plain")

            async with client:
                result = await client.add_torrent(
                    "magnet:?xt=urn:btih:abc123",
                    savepath="/custom",
                    category="test",
                    paused=True
                )
                assert result == "Ok."

    @pytest.mark.asyncio
    async def test_control_torrent_pause(self, client):
        """Test pausing torrent."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.", content_type="text/plain")
            m.post(f"{BASE_URL}/api/v2/torrents/pause", status=200, body="Ok.", content_type="text/plain")

            async with client:
                result = await client.control_torrent("abc123", "pause")
                assert result == "Ok."

    @pytest.mark.asyncio
    async def test_control_torrent_resume(self, client):
        """Test resuming torrent."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.", content_type="text/plain")
            m.post(f"{BASE_URL}/api/v2/torrents/resume", status=200, body="Ok.", content_type="text/plain")

            async with client:
                result = await client.control_torrent("abc123", "resume")
                assert result == "Ok."

    @pytest.mark.asyncio
    async def test_control_torrent_delete(self, client):
        """Test deleting torrent."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.", content_type="text/plain")
            m.post(f"{BASE_URL}/api/v2/torrents/delete", status=200, body="Ok.", content_type="text/plain")

            async with client:
                result = await client.control_torrent("abc123", "delete", delete_files=True)
                assert result == "Ok."

    @pytest.mark.asyncio
    async def test_control_torrent_invalid_action(self, client):
        """Test invalid action."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")

            async with client:
                with pytest.raises(APIError, match="Invalid action"):
                    await client.control_torrent("abc123", "invalid")


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


class TestPreferences:
    """Test preferences operations."""

    @pytest.mark.asyncio
    async def test_get_preferences(self, client, mock_preferences):
        """Test getting preferences."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")
            m.get(f"{BASE_URL}/api/v2/app/preferences", status=200, payload=mock_preferences)

            async with client:
                prefs = await client.get_preferences()
                assert prefs["save_path"] == "/downloads"
                assert prefs["listen_port"] == 6881


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_request_without_login(self, client):
        """Test making request without login."""
        with pytest.raises(AuthenticationError, match="Not authenticated"):
            await client.list_torrents()

    @pytest.mark.asyncio
    async def test_api_error_403(self, client):
        """Test 403 authentication error."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")
            m.get(f"{BASE_URL}/api/v2/torrents/info", status=403, body="Forbidden")

            async with client:
                with pytest.raises(AuthenticationError, match="Token expired"):
                    await client.list_torrents()

    @pytest.mark.asyncio
    async def test_api_error_500(self, client):
        """Test 500 server error."""
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/v2/auth/login", status=200, body="Ok.")
            m.get(f"{BASE_URL}/api/v2/torrents/info", status=500, body="Server Error")

            async with client:
                with pytest.raises(APIError, match="API error: 500"):
                    await client.list_torrents()
