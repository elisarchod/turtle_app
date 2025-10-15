"""Test fixtures for qBittorrent client tests."""

import pytest

# Mock qBittorrent API responses

MOCK_TORRENT_LIST = [
    {
        "hash": "abc123",
        "name": "Ubuntu 22.04 LTS",
        "size": 3774873600,
        "progress": 0.5,
        "dlspeed": 1048576,
        "upspeed": 524288,
        "eta": 1800,
        "state": "downloading",
        "category": "linux",
        "save_path": "/downloads",
        "num_seeds": 50,
        "num_leechs": 10,
        "ratio": 0.5
    },
    {
        "hash": "def456",
        "name": "Test Movie 1080p",
        "size": 2147483648,
        "progress": 1.0,
        "dlspeed": 0,
        "upspeed": 262144,
        "eta": 8640000,
        "state": "seeding",
        "category": "movies",
        "save_path": "/downloads/movies",
        "num_seeds": 5,
        "num_leechs": 2,
        "ratio": 2.5
    }
]

MOCK_TORRENT_PROPERTIES = {
    "save_path": "/downloads",
    "creation_date": 1609459200,
    "total_uploaded": 1073741824,
    "total_downloaded": 2147483648,
    "time_elapsed": 3600,
    "seeding_time": 1800,
    "share_ratio": 0.5,
    "comment": "Ubuntu official release"
}

MOCK_TORRENT_FILES = [
    {
        "name": "ubuntu-22.04-desktop-amd64.iso",
        "size": 3774873600,
        "progress": 0.5,
        "priority": 1
    }
]

MOCK_SEARCH_RESULTS = {
    "results": [
        {
            "fileName": "Ubuntu 22.04 LTS Desktop",
            "fileUrl": "magnet:?xt=urn:btih:abc123",
            "fileSize": 3774873600,
            "nbSeeders": 100,
            "nbLeechers": 20,
            "siteUrl": "https://ubuntu.com",
            "descrLink": "https://ubuntu.com/download"
        }
    ],
    "status": "Stopped",
    "total": 1
}

MOCK_SEARCH_STATUS = [
    {
        "id": 1,
        "status": "Stopped",
        "total": 1
    }
]

MOCK_PREFERENCES = {
    "save_path": "/downloads",
    "temp_path": "/downloads/temp",
    "dl_limit": 0,
    "up_limit": 0,
    "max_connec": 500,
    "max_connec_per_torrent": 100,
    "listen_port": 6881,
    "upnp": True,
    "dht": True,
    "max_active_downloads": 3,
    "max_active_torrents": 5,
    "max_active_uploads": 3
}


@pytest.fixture
def mock_torrent_list():
    """Mock torrent list response."""
    return MOCK_TORRENT_LIST


@pytest.fixture
def mock_torrent_properties():
    """Mock torrent properties response."""
    return MOCK_TORRENT_PROPERTIES


@pytest.fixture
def mock_torrent_files():
    """Mock torrent files response."""
    return MOCK_TORRENT_FILES


@pytest.fixture
def mock_search_results():
    """Mock search results response."""
    return MOCK_SEARCH_RESULTS


@pytest.fixture
def mock_search_status():
    """Mock search status response."""
    return MOCK_SEARCH_STATUS


@pytest.fixture
def mock_preferences():
    """Mock preferences response."""
    return MOCK_PREFERENCES
