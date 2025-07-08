from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.tools import Tool
from langchain.tools import BaseTool

from turtleapp.settings import settings
from turtleapp.src.utils import logger

import os
import re
import smbclient as smb_client
import time


def _clean_movie_name(filename):
    name_without_ext = os.path.splitext(filename)[0]
    cleaned_name = re.sub(r'[\._]', ' ', name_without_ext)
    return ' '.join(cleaned_name.split())


def get_movie_library() -> Dict[str, str]:
    movies = {}
    
    try:
        share_path = settings.network_share.path
        if not share_path:
            logger.warning("No network share path configured")
            return movies
        
        for root, dirs, files in os.walk(share_path):
            for file in files:
                if file.lower().endswith(('.mkv', '.mp4', '.avi', '.mov', '.wmv')):
                    file_path = os.path.join(root, file)
                    movie_name = _clean_movie_name(file)
                    movies[movie_name] = file_path
        
        logger.info(f"Found {len(movies)} movies in library")
        return movies
        
    except Exception as e:
        logger.error(f"Failed to scan movie library: {str(e)}")
        return movies


class LibraryManagerTool(BaseTool):
    name: str = "library_manager"
    description: str = "Scans and catalogs the local movie library from network shares"

    def _run(self, force_refresh: bool = False) -> str:
        movies_paths = get_movie_library()
        
        if not movies_paths:
            return "No movies found in library"
        
        total_movies = len(movies_paths)
        file_extensions = {}
        for movie_name, file_path in movies_paths.items():
            ext = os.path.splitext(file_path)[1].lower()
            file_extensions[ext] = file_extensions.get(ext, 0) + 1
        
        result = f"Library scan completed. Found {total_movies} movies.\n"
        result += f"File types: {', '.join([f'{ext}: {count}' for ext, count in file_extensions.items()])}\n"
        result += "Sample movies:\n"
        
        for i, (movie, path) in enumerate(list(movies_paths.items())[:5]):
            result += f"- {movie}\n"
        
        if total_movies > 5:
            result += f"... and {total_movies - 5} more"
        
        return result

library_manager_tool: Tool = LibraryManagerTool()

if __name__ == "__main__":
    movies = get_movie_library()
    logger.info(f"Found {len(movies)} movies:")
    for movie, path in movies.items():
        logger.info(f"  {movie} - {path}")

