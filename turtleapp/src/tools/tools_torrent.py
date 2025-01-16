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

from typing import Literal, Tuple, Any, Dict, List
import requests
from langchain.tools import BaseTool
from langchain_core.tools import Tool

IP_ADDRESS = "http://192.168.1.250:15080"
def get_torrents_info() -> List[Dict[str, Any]]:
    url = f"{IP_ADDRESS}/api/v2/torrents/info?filter=downloading"
    headers = {'Referer': IP_ADDRESS}
    data = {'username': 'admin', 'password': 'adminadmin'}

    response = requests.post(url, headers=headers, data=data)
    return response.json()

class TorrentClientTool(BaseTool):
    name: str = "torrent_local_client_tool"
    description: str = "Retrieve information about currently downloading torrents in my local network"

    def _run(self, request_type: Literal["list", "add"] = 'list') -> Tuple[str, List[Dict[str, Any]]]:
        if request_type == 'list':
            print("*"*100)
        torrents = get_torrents_info()
        processed_torrents = []
        for torrent in torrents:
            processed_torrent = {
                "content_path":   torrent.get('content_path', ''),
                "name":           torrent.get('name', ''),
                "progress":       torrent.get('progress', 0.0)
                }
            processed_torrents.append(processed_torrent)
        content = 'Here are the currently downloading torrents in my local network: \n\n'
        return processed_torrents

torrent_info_tool: Tool = TorrentClientTool()

if __name__ == "__main__":
    torrent_info_tool.invoke({
        "name": "torrent_local_client_tool",
        "args": {},
        "id":   "123",
        "type": "tool_call", }
        )
