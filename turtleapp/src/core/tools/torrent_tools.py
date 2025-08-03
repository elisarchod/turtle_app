import time
from typing import Any, Dict, List

import requests
from langchain_core.tools import BaseTool

from turtleapp.settings import settings
from turtleapp.src.utils import clean_movie_filename, handle_service_errors, handle_tool_errors

API_TIMEOUT = 30
SEARCH_DELAY = 5
MAX_SEARCH_RESULTS = 5

URL = f"{settings.qbittorrent.host}/api/v2"
HEADERS = {'Referer': settings.qbittorrent.host}

@handle_service_errors(service_name="TorrentAPI", default_return=None)
def api_call(endpoint: str, data: dict = None) -> requests.Response:
    if not settings.qbittorrent.host:
        raise ValueError("qBittorrent host not configured")
    
    call_data = settings.qbittorrent.credentials.copy()
    if data:
        call_data.update(data)
    
    response = requests.post(f"{URL}{endpoint}", headers=HEADERS, data=call_data, timeout=API_TIMEOUT)
    response.raise_for_status()
    return response

@handle_service_errors(service_name="TorrentAPI", default_return=[])
def get_torrents(only_downloading: bool = False) -> List[Dict[str, Any]]:
    response = api_call('/torrents/info')
    torrents = response.json()

    if only_downloading:
        torrents = [torrent for torrent in torrents if torrent.get('progress') != 1]

    for torrent in torrents:
        torrent['progress_percent'] = round(torrent.get('progress', 0) * 100, 2)
        torrent['name'] = clean_movie_filename(torrent.get('name', 'Unknown'))
    return torrents

@handle_service_errors(service_name="TorrentAPI", default_return=[])
def search_torrents(search_query: str) -> List[Dict[str, Any]]:
    response = api_call('/search/start', {'pattern': search_query, 'plugins': 'all', 'category': 'movies'})
    response.raise_for_status()
    search_id = response.json()['id']

    time.sleep(SEARCH_DELAY)
    results_response = api_call('/search/results', {'search_id': search_id})
    return results_response.json().get('results', []) if results_response else []

class TorrentDownloadsTool(BaseTool):
    name: str = "movie_download_status"
    description: str = """Check status of active movie downloads in download client.
    
    Use when users ask about:
    - Current download progress
    - Download speeds and ETA
    - Completed downloads
    - Download queue status
    
    Input: Optional filter (leave empty for all downloads)
    Returns: List of downloads with progress, speed, and status info
    
    Status information includes:
    - Download progress percentage
    - Download/upload speeds
    - Time remaining (ETA)
    - File sizes and completion status
    """
    
    @handle_tool_errors(default_return="Torrent service unavailable")
    def _run(self, query: str = "") -> str:
        torrents = get_torrents(only_downloading=True)
        
        if not torrents:
            return "No active downloads"
        
        return self._format_download_status(torrents)
    
    def _format_download_status(self, torrents: List[Dict[str, Any]]) -> str:
        result = f"Currently downloading {len(torrents)} items:\n"
        for torrent in torrents:
            status = "downloading" if torrent['progress_percent'] < 100 else "completed"
            result += f"- {torrent['name']} ({status})\n"
        return result



class TorrentSearchTool(BaseTool):
    name: str = "movie_search"
    description: str = """Search for movie files across multiple sources and sites.
    
    Use when users want to:
    - Find downloadable movies for specific titles
    - Check movie availability
    - Get movie quality and source information
    
    Input: Movie title (include year if known for better results)
    Returns: List of available movies with quality, size, and source info
    
    Best practices:
    - Include movie year when possible: "Movie Title 2023"
    - Search returns quality info (720p, 1080p, 4K)
    - Prefer well-sourced files for reliable downloads
    """
    
    @handle_tool_errors(default_return="Torrent service unavailable")
    def _run(self, search_term: str) -> str:
        if not search_term.strip():
            return "Please specify what to search for"
        
        results = search_torrents(search_term)
        
        if not results:
            return f"No torrents found for '{search_term}'"
        
        return self._format_search_results(search_term, results)
    
    def _format_search_results(self, search_term: str, results: List[Dict[str, Any]]) -> str:
        result = f"Found torrents for '{search_term}':\n"
        for i, item in enumerate(results[:MAX_SEARCH_RESULTS], 1):
            result += f"{i}. {item.get('fileName', 'Unknown')}\n"
        
        if len(results) > MAX_SEARCH_RESULTS:
            result += f"... and {len(results) - MAX_SEARCH_RESULTS} more available"
        
        return result


torrent_search_tool = TorrentSearchTool()
torrent_download_tool = TorrentDownloadsTool()

if __name__ == "__main__":
    downloads_tool = TorrentDownloadsTool()
    search_tool = TorrentSearchTool()
    print("Downloads:", downloads_tool._run(""))
    print("Search:", search_tool._run("terminator"))

    search_query = 'terminator'
    endpoint = '/search/status'
    call_data = settings.qbittorrent.credentials.copy()
    call_data.update()

    search_id = requests.post(f"{URL}/search/start", headers=HEADERS, data={**call_data, **{'pattern': search_query, 'plugins': 'all', 'category': 'movies'}}, timeout=API_TIMEOUT).json()
    requests.post(f"{URL}/search/stop", headers=HEADERS, data={**call_data, **search_id}, timeout=API_TIMEOUT).json()
    requests.get(f"{URL}/search/status", headers=HEADERS, data=call_data, timeout=API_TIMEOUT).json()

