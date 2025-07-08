import requests
import time
from langchain_core.tools import Tool
from langchain.tools import BaseTool
from typing import List, Dict, Any

from turtleapp.settings import settings
from turtleapp.src.utils import logger

URL = f"{settings.qbittorrent.host}/api/v2"
HEADERS = {'Referer': settings.qbittorrent.host}

def api_call(endpoint: str, data: dict = None) -> requests.Response:
    if not settings.qbittorrent.host:
        raise ValueError("qBittorrent host not configured")
    
    call_data = settings.qbittorrent.credentials.copy()
    if data:
        call_data.update(data)
    
    response = requests.post(f"{URL}{endpoint}", headers=HEADERS, data=call_data, timeout=30)
    response.raise_for_status()
    return response

def get_torrents(filter_downloading: bool = False) -> List[Dict[str, Any]]:
    response = api_call('/torrents/info')
    torrents = response.json()
    
    if filter_downloading:
        torrents = [t for t in torrents if t.get('state') in ['downloading', 'stalledDL']]
    
    for torrent in torrents:
        torrent['progress_percent'] = round(torrent.get('progress', 0) * 100, 2)
    
    return torrents

def search_torrents(query: str) -> List[Dict[str, Any]]:
    try:
        response = api_call('/search/start', {'pattern': query, 'plugins': 'all', 'category': 'all'})
        response.raise_for_status()
        search_id = response.json()['id']
        
        time.sleep(5)
        
        response = api_call('/search/results', {'search_id': search_id})
        
        if response.status_code == 200:
            return response.json().get('results', [])
        else:
            return [{'fileName': f'Search started for "{query}" but results API has limitations'}]
            
    except Exception as e:
        logger.error(f"Search failed for query '{query}': {str(e)}")
        return [{'fileName': f'Search failed for "{query}": {str(e)}'}]

class TorrentClientTool(BaseTool):
    name: str = "torrent_client"
    description: str = """Manage torrent downloads: list current downloads, search for movies/content, and add new torrents via magnet links. 
    Use 'list' to see downloading torrents, 'search' with a query to find content, or 'add' with a magnet link to start a download."""
    
    def _run(self, operation: str = "list", filter_type: str = "downloading", magnet_link: str = None, search_query: str = None) -> str:
        
        try:
            if operation == "list":
                torrents = get_torrents(filter_type == "downloading")
                
                if not torrents:
                    return f"No torrents found (filter: {filter_type})"
                
                result = f"Found {len(torrents)} torrents (filter: {filter_type}):\n"
                for t in torrents:
                    result += f"- {t['name']} ({t['progress_percent']}%)\n"
                return result

            elif operation == "search":
                if not search_query:
                    return "Error: Search query is required for search operation"
                
                results = search_torrents(search_query)
                
                if not results:
                    return f"No results found for '{search_query}'"
                
                result = f"Found {len(results)} results for '{search_query}':\n"
                for i, item in enumerate(results[:10], 1):
                    result += f"{i}. {item.get('fileName', 'Unknown')}\n"
                    if item.get('size'):
                        result += f"   Size: {item['size']}\n"
                    if item.get('nbFiles'):
                        result += f"   Files: {item['nbFiles']}\n"
                    result += "\n"
                
                if len(results) > 10:
                    result += f"... and {len(results) - 10} more results\n"
                
                return result

            elif operation == "add":
                if not magnet_link:
                    return "Error: Magnet link is required for add operation"
                
                response = api_call('/torrents/add', {'urls': magnet_link})
                return "Torrent added successfully" if response.status_code == 200 else "Failed to add torrent"

            else:
                return f"Error: Unknown operation '{operation}'. Use: list, search, add"
                
        except Exception as e:
            logger.error(f"Torrent operation failed: {str(e)}")
            return f"Error: {str(e)}"

torrent_info_tool: Tool = TorrentClientTool()

if __name__ == "__main__":
    torrents = get_torrents(filter_downloading=True)
    logger.info(f"Downloading torrents: {len(torrents)}")
    
    pirates_torrents = [t for t in torrents if 'pirates' in t['name'].lower()]
    if pirates_torrents:
        logger.info(f"Found {len(pirates_torrents)} pirates torrent(s):")
        for t in pirates_torrents:
            logger.info(f"- {t['name']} ({t['progress_percent']}%)")
    else:
        logger.info("No pirates content found.")
