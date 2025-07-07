import time
import requests
from langchain.tools import BaseTool
from langchain_core.tools import Tool
from typing import List, Dict, Any

from turtleapp.settings import settings
from turtleapp.src.utils.log_handler import logger
import sys

# Configuration with environment variable support

URL = f"{settings.qbittorrent.host}/api/v2"
HEADERS = {'Referer': settings.qbittorrent.host}

def api_call(endpoint: str, data: dict = None) -> requests.Response:
    call_data = settings.qbittorrent.credentials.copy()
    if data:
        call_data.update(data)
    return requests.post(f"{URL}{endpoint}", headers=HEADERS, data=call_data)

def get_downloading_torrents() -> List[Dict[str, Any]]:
    response = api_call('/torrents/info?filter=downloading')
    response.raise_for_status()
    torrents = response.json()

    return [{
        "name": t.get('name', ''),
        "content_path": t.get('content_path', ''),
        "progress": t.get('progress', 0.0)
    } for t in torrents]

def search_torrents(query: str) -> List[Dict[str, Any]]:
    response = api_call('/search/start', {'pattern': query, 'plugins': 'all', 'category': 'all'})
    response.raise_for_status()
    search_id = response.json()['id']
    time.sleep(5)
    response = api_call('/search/results', {'search_id': search_id})

    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        return [{'fileName': f'Search started for "{query}" but results API has limitations'}]

def add_torrent(magnet_link: str, save_path: str = None) -> bool:
    data = {'urls': magnet_link}
    if save_path:
        data['savepath'] = save_path

    response = api_call('/torrents/add', data)
    return response.status_code == 200

class TorrentClientTool(BaseTool):
    name: str = "movie_download_client"
    description: str = "Manage torrents: list downloading torrents, search for torrents, add torrents via magnet links"

    def _run(self, operation: str = "list", query: str = None, magnet_link: str = None) -> str:
        try:
            if operation == "list":
                torrents = get_downloading_torrents()
                return f"Found {len(torrents)} downloading torrents: {torrents}"

            elif operation == "search":
                if not query:
                    return "Error: query required for search"
                results = search_torrents(query)
                return f"Found {len(results)} results for '{query}': {results}"

            elif operation == "add":
                if not magnet_link:
                    return "Error: magnet_link required for add"
                success = add_torrent(magnet_link)
                return f"Torrent {'added successfully' if success else 'failed to add'}"

            else:
                return f"Error: Unknown operation '{operation}'. Use: list, search, add"

        except Exception as e:
            logger.error(f"Torrent operation failed: {e}")
            return f"Error: {str(e)}"

torrent_info_tool: Tool = TorrentClientTool()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        results = search_torrents(query)
        print(f"Search results: {results}")
    else:
        print("Usage: python torrent_tools.py 'search query'")
        torrents = get_downloading_torrents()
        print(f"Current downloads: {torrents}")
