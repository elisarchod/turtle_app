"""Integration tests for qBittorrent client with real qBittorrent instance.

These tests require a running qBittorrent instance with credentials configured.
Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import pytest
import requests

from mcp_qbittorrent.clients.qbittorrent_client import QBittorrentClient
from mcp_qbittorrent.config import settings
from mcp_qbittorrent.utils import logger

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def skip_if_no_qbittorrent():
    """Skip tests if qBittorrent is not accessible."""
    try:
        response = requests.get(settings.qbittorrent_url, timeout=2)
        if response.status_code not in [200, 401, 403]:
            pytest.skip("qBittorrent not available")
    except Exception:
        pytest.skip("qBittorrent not accessible")


class TestQBittorrentIntegration:
    """Integration tests with real qBittorrent instance."""

    @pytest.mark.asyncio
    async def test_authentication(self):
        """Test authentication with real qBittorrent instance."""
        async with QBittorrentClient(
            base_url=settings.qbittorrent_url,
            username=settings.qbittorrent_username,
            password=settings.qbittorrent_password,
            timeout=settings.request_timeout
        ) as client:
            assert client.session is not None

    @pytest.mark.asyncio
    async def test_list_torrents(self):
        """Test listing torrents from real instance."""
        async with QBittorrentClient(
            base_url=settings.qbittorrent_url,
            username=settings.qbittorrent_username,
            password=settings.qbittorrent_password,
            timeout=settings.request_timeout
        ) as client:
            torrents = await client.list_torrents()
            assert isinstance(torrents, list)
            torrent = torrents[0]
            logger.info(torrent)
            assert "hash" in torrent
            assert "name" in torrent
            assert "size" in torrent
            assert "state" in torrent


    @pytest.mark.asyncio
    async def test_get_torrent_info(self):
        """Test getting detailed info for a torrent."""
        async with QBittorrentClient(
            base_url=settings.qbittorrent_url,
            username=settings.qbittorrent_username,
            password=settings.qbittorrent_password,
            timeout=settings.request_timeout
        ) as client:
            torrents = await client.list_torrents()

            if torrents:
                # Get info for first torrent
                torrent_hash = torrents[0]["hash"]
                info = await client.get_torrent_info(torrent_hash)

                assert isinstance(info, dict)
                assert "save_path" in info
                assert "files" in info
                assert isinstance(info["files"], list)
