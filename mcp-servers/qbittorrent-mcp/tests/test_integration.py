"""Integration tests for qBittorrent client with real qBittorrent instance.

These tests require a running qBittorrent instance with credentials configured.
Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import pytest
from mcp_qbittorrent.clients.qbittorrent_client import QBittorrentClient
from mcp_qbittorrent.config import settings


@pytest.mark.integration
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

            if torrents:
                # Verify structure of first torrent
                torrent = torrents[0]
                assert "hash" in torrent
                assert "name" in torrent
                assert "size" in torrent
                assert "state" in torrent

    @pytest.mark.asyncio
    async def test_get_preferences(self):
        """Test getting preferences from real instance."""
        async with QBittorrentClient(
            base_url=settings.qbittorrent_url,
            username=settings.qbittorrent_username,
            password=settings.qbittorrent_password,
            timeout=settings.request_timeout
        ) as client:
            prefs = await client.get_preferences()
            assert isinstance(prefs, dict)
            assert "save_path" in prefs
            assert "listen_port" in prefs
            assert "dl_limit" in prefs
            assert "up_limit" in prefs

    @pytest.mark.asyncio
    async def test_list_torrents_with_filter(self):
        """Test filtering torrents by status."""
        async with QBittorrentClient(
            base_url=settings.qbittorrent_url,
            username=settings.qbittorrent_username,
            password=settings.qbittorrent_password,
            timeout=settings.request_timeout
        ) as client:
            all_torrents = await client.list_torrents()
            downloading = await client.list_torrents(filter="downloading")
            completed = await client.list_torrents(filter="completed")

            assert isinstance(downloading, list)
            assert isinstance(completed, list)
            # Filter results should be subset of all torrents
            assert len(downloading) + len(completed) <= len(all_torrents)

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
