from pathlib import Path
from typing import Any, Dict, List

from langchain_core.tools import BaseTool

from turtleapp.settings import SMB_PASSWORD, SMB_SERVER_IP, SMB_SHARE_PATH, SMB_USERNAME
from turtleapp.src.utils.log_handler import logger

import os
import re
# import smbprotocol.exceptions
import smbclient as smb_client

# smb_client.register_session(SMB_SERVER_IP, username=SMB_USERNAME, password=SMB_PASSWORD)
#
#
# smb_client.listdir(SMB_SHARE_PATH)  # Ensure the share is accessible
# [i for i in smb_client.walk(SMB_SHARE_PATH)]
#



def _clean_movie_name(filename):
    name_without_ext = os.path.splitext(filename)[0]
    cleaned_name = re.sub(r'[\._]', ' ', name_without_ext)
    return ' '.join(cleaned_name.split())


def _find_movies_on_share(share_path, server_ip, username, password):
    movie_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}
    movie_dict = {}


    smb_client.register_session(server_ip, username=username, password=password)
    logger.info(f"--> Session established with {server_ip}. Scanning '{share_path}'...")

    for dirpath, _, filenames in smb_client.walk(share_path):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() in movie_extensions:
                clean_name = _clean_movie_name(filename)
                movie_dict[clean_name] = f"{dirpath}\\{filename}"

    logger.info(f"\nScan complete. Found {len(movie_dict)} movies.")
    return movie_dict

def get_movie_library():
    return _find_movies_on_share(share_path=SMB_SHARE_PATH,
                                 server_ip=SMB_SERVER_IP,
                                 username=SMB_USERNAME,
                                 password=SMB_PASSWORD)


class LibraryManagerTool(BaseTool):
    name: str = "library_manager"
    description: str = "Scans and catalogs the local movie library"

    def _run(self) -> List[Dict[str, Any]]:
        """Scan for movies and return results."""
        movies_paths = get_movie_library()
        logger.info(f"Found {len(movies)} movies: {movies}")
        return movies_paths

library_manager_tool = LibraryManagerTool()

if __name__ == "__main__":
    movies = get_movie_library()
    logger.info(f"Found {len(movies)} movies:")
    for movie, path in movies.items():
        logger.info(f"  {movie} - {path}")

