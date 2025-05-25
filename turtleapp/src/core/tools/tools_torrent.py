"""
example for qbitoorent sucket

curl -i --header 'Referer: http://192.168.1.250:15080' --data 'username=admin&password=adminadmin' http://192.168.1.250:15080/api/v2/auth/login


 get downloads
# curl -i --header 'Referer: http://192.168.1.250:15080' --data 'username=admin&password=adminadmin' http://192.168.1.250:15080/api/v2/torrents/info?filter=downloading

example for qbitoorent sucket

curl -i --header 'Referer: http://192.168.1.250:15080' --data 'username=admin&password=adminadmin' http://192.168.1.250:15080/api/v2/auth/login


 get downloads
# curl -i --header 'Referer: http://192.168.1.250:15080' --data 'username=admin&password=adminadmin' http://192.168.1.250:15080/api/v2/torrents/info?filter=downloading


"""

import time
from typing import Literal, Tuple, Any, Dict, List
import requests
from langchain.tools import BaseTool
from langchain_core.tools import Tool
from typing import List, Dict, Any
import requests
from turtleapp.src.utils.log_handler import logger

IP_ADDRESS = "http://192.168.1.250:15080"
CREDENTIALS = {'username': 'admin', 'password': 'adminadmin'}
URL = f"{IP_ADDRESS}/api/v2"

#
# >> > from qbittorrentapi import Client >> > client = Client(host='localhost:8080',
#                                                             username='admin',
#                                                             password='adminadmin') >> > search_job = client.search_start(
#     pattern='Ubuntu',
#     plugins='all',
#     category='all') >> > client.search_stop(search_id=search_job.id) >> >  # or
# >> > search_job.stop()

url = f"{URL}/search/start"
url = f"{URL}/torrents/info?filter=downloading"
headers = {'Referer': IP_ADDRESS}
requests.post(url, headers=headers, data=CREDENTIALS)#.json()




def get_torrents_info(call: str) -> List[Dict[str, Any]]:
    url = f"{URL}{call}"
    headers = {'Referer': IP_ADDRESS}
    response = requests.post(url, headers=headers, data=CREDENTIALS)
    response.raise_for_status()  # Ensure HTTP errors are raised
    return response.json()

def beutify_torrent_details(torrent_details):
    return {
        "content_path": torrent_details.get('content_path', ''),
        "name": torrent_details.get('name', ''),
        "progress": torrent_details.get('progress', 0.0)}

def get_torrnts_info() -> List[Dict[str, Any]]:
    torrents = get_torrents_info('/torrents/info?filter=downloading')
    processed_torrents = list(map(beutify_torrent_details, torrents))
    return processed_torrents

def search_torrents(query: str) -> List[Dict[str, Any]]:
    headers = {'Referer': IP_ADDRESS}
    response_start = requests.post(f"{URL}/search/start", headers=headers, data=CREDENTIALS)
    response_start.raise_for_status() 
    time.sleep(30)
    response_results = requests.post(f"{URL}/search/results", headers=headers, data=CREDENTIALS)
    response_results.raise_for_status()
    return response_results.json()

class TorrentClientTool(BaseTool):
    name: str = "torrent_local_client_tool"
    description: str = "Retrieve information about currently downloading torrents in my local network"

    def _run(self, request_type: Literal["list", "add"] = 'list') -> Tuple[str, List[Dict[str, Any]]]:
        if request_type == 'list':
            logger.info("="*100)
        torrents = get_torrents_info()

        return processed_torrents

torrent_info_tool: Tool = TorrentClientTool()

if __name__ == "__main__":
    torrent_info_tool.invoke({
        "name": "torrent_local_client_tool",
        "args": {},
        "id":   "123",
        "type": "tool_call", }
        )
