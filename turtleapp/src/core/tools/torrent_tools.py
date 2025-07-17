import requests
import time
from langchain_core.tools import BaseTool
from typing import List, Dict, Any

from turtleapp.settings import settings
from turtleapp.src.nodes import ToolAgent
from turtleapp.src.utils import handle_tool_errors, handle_service_errors

URL = f"{settings.qbittorrent.host}/api/v2"
HEADERS = {'Referer': settings.qbittorrent.host}

@handle_service_errors(service_name="TorrentAPI", default_return=None)
def api_call(endpoint: str, data: dict = None) -> requests.Response:
    if not settings.qbittorrent.host:
        raise ValueError("qBittorrent host not configured")
    
    call_data = settings.qbittorrent.credentials.copy()
    if data:
        call_data.update(data)
    
    response = requests.post(f"{URL}{endpoint}", headers=HEADERS, data=call_data, timeout=30)
    response.raise_for_status()
    return response

@handle_service_errors(service_name="TorrentAPI", default_return=[])
def get_torrents(filter_downloading: bool = False) -> List[Dict[str, Any]]:
    response = api_call('/torrents/info')
    torrents = response.json()
    
    if filter_downloading:
        torrents = [t for t in torrents if t.get('state') in ['downloading', 'stalledDL']]

    for torrent in torrents:
        torrent['progress_percent'] = round(torrent.get('progress', 0) * 100, 2)
    
    return torrents

@handle_service_errors(service_name="TorrentAPI", default_return=[])
def search_torrents(query: str) -> List[Dict[str, Any]]:
    response = api_call('/search/start', {'pattern': query, 'plugins': 'all', 'category': 'all'})
    response.raise_for_status()
    search_id = response.json()['id']

    time.sleep(5)

    response = api_call('/search/results', {'search_id': search_id})
    
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        return []

class TorrentDownloadsTool(BaseTool):
    name: str = "torrent_downloads"
    description: str = "Check current torrent downloads and their status."
    
    @handle_tool_errors(default_return="Torrent service unavailable")
    def _run(self, query: str = "") -> str:
        torrents = get_torrents(filter_downloading=True)
        
        if not torrents:
            return "No active downloads"
        
        result = f"Currently downloading {len(torrents)} items:\n"
        for t in torrents:
            status = "downloading" if t['progress_percent'] < 100 else "completed"
            result += f"- {t['name']} ({status})\n"
        
        return result



class TorrentSearchTool(BaseTool):
    name: str = "torrent_search"
    description: str = "Search for movie torrents by title or keyword."
    
    @handle_tool_errors(default_return="Torrent service unavailable")
    def _run(self, search_term: str) -> str:
        if not search_term.strip():
            return "Please specify what to search for"
        
        results = search_torrents(search_term)
        
        if not results:
            return f"No torrents found for '{search_term}'"
        
        result = f"Found torrents for '{search_term}':\n"
        for i, item in enumerate(results[:5], 1):
            result += f"{i}. {item.get('fileName', 'Unknown')}\n"
        
        if len(results) > 5:
            result += f"... and {len(results) - 5} more available"
        
        return result

torrent_agent = ToolAgent([TorrentDownloadsTool(), TorrentSearchTool()],
                          name="torrent_manager_agent")

if __name__ == "__main__":
    downloads_tool = TorrentDownloadsTool()
    search_tool = TorrentSearchTool()
    print("Downloads:", downloads_tool._run(""))
    print("Search:", search_tool._run("terminator"))
