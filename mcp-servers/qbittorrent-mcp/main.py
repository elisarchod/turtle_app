"""Test script for qBittorrent client."""

import asyncio
import logging
from mcp_qbittorrent.clients.qbittorrent_client import QBittorrentClient
from mcp_qbittorrent.config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_client():
    """Test qBittorrent client connection and basic operations."""
    logger.info(f"Connecting to qBittorrent at {settings.qbittorrent_url}")

    async with QBittorrentClient(
        base_url=settings.qbittorrent_url,
        username=settings.qbittorrent_username,
        password=settings.qbittorrent_password,
        timeout=settings.request_timeout
    ) as client:
        torrents = await client.list_torrents()
        logger.info(f"Number of torrents: {len(torrents)}")

        if torrents:
            logger.info(f"First torrent: {torrents[0].get('name', 'Unknown')}")

        prefs = await client.get_preferences()
        logger.info(f"Default save path: {prefs.get('save_path', 'Unknown')}")

        logger.info("✅ Client test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_client())
