import requests
import time
from langchain_core.tools import Tool
from langchain.tools import BaseTool
from typing import List, Dict, Any

from turtleapp.settings import settings
from turtleapp.src.utils import logger
from turtleapp.src.utils.error_handler import handle_tool_errors, handle_service_errors

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
    
    # Simplify torrent info for LLM consumption
    for torrent in torrents:
        torrent['progress_percent'] = round(torrent.get('progress', 0) * 100, 2)
    
    return torrents

@handle_service_errors(service_name="TorrentAPI", default_return=[])
def search_torrents(query: str) -> List[Dict[str, Any]]:
    response = api_call('/search/start', {'pattern': query, 'plugins': 'all', 'category': 'all'})
    response.raise_for_status()
    search_id = response.json()['id']
    
    time.sleep(5)  # Wait for search to complete
    
    response = api_call('/search/results', {'search_id': search_id})
    
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        return []

class TorrentClientTool(BaseTool):
    name: str = "torrent_client"
    description: str = "Check torrent downloads and search for movies. Returns simple status information."
    
    @handle_tool_errors(default_return="Torrent service unavailable")
    def _run(self, query: str) -> str:
        # Simple approach: if query contains specific search terms, search; otherwise list downloads
        if any(word in query.lower() for word in ['search for', 'find', 'look for']):
            # Extract search term after the search phrase
            search_term = query.lower()
            for phrase in ['search for', 'find', 'look for']:
                if phrase in search_term:
                    search_term = search_term.split(phrase, 1)[1].strip()
                    break
            
            if not search_term:
                return "Please specify what to search for"
            
            results = search_torrents(search_term)
            
            if not results:
                return f"No torrents found for '{search_term}'"
            
            # Return simple list of first 5 results
            result = f"Found torrents for '{search_term}':\n"
            for i, item in enumerate(results[:5], 1):
                result += f"{i}. {item.get('fileName', 'Unknown')}\n"
            
            if len(results) > 5:
                result += f"... and {len(results) - 5} more available"
            
            return result
        
        else:
            # List current downloads
            torrents = get_torrents(filter_downloading=True)
            
            if not torrents:
                return "No active downloads"
            
            result = f"Currently downloading {len(torrents)} items:\n"
            for t in torrents:
                status = "downloading" if t['progress_percent'] < 100 else "completed"
                result += f"- {t['name']} ({status})\n"
            
            return result

torrent_info_tool: Tool = TorrentClientTool()

if __name__ == "__main__":
    # Simple test
    tool = TorrentClientTool()
    print(tool._run("check downloads"))
    print(tool._run("search for terminator"))
