from typing import Any, Dict, List
import smbclient as smb_client
from langchain_core.tools import Tool, BaseTool

from turtleapp.settings import settings
from turtleapp.src.nodes import ToolAgent
from turtleapp.src.utils import logger, handle_tool_errors, handle_service_errors, clean_movie_filename
from turtleapp.src.constants import DefaultValues, FileExtensions

import os



@handle_service_errors(service_name="LibraryManager", default_return={})
def scan_smb_movie_library() -> Dict[str, str]:
    movies = {}
    smb_client.register_session(settings.smb.server,
                                username=settings.smb.username,
                                password=settings.smb.password)

    for root, dirs, files in smb_client.walk(settings.smb.share_path):
        for file in files:
            if file.lower().endswith(FileExtensions.MOVIE_EXTENSIONS):
                file_path = os.path.join(root, file)
                movie_name = clean_movie_filename(file)
                movies[movie_name] = file_path
    
    logger.info(f"Found {len(movies)} movies in library")
    return movies


class LibraryManagerTool(BaseTool):
    name: str = "library_manager"
    description: str = "Scans and catalogs the local movie library from network shares"

    @handle_tool_errors(default_return="Library scan failed")
    def _run(self) -> str:
        movies_paths = scan_smb_movie_library()
        total_movies = len(movies_paths)
        file_extensions = {}
        for movie_name, file_path in movies_paths.items():
            ext = os.path.splitext(file_path)[1].lower()
            file_extensions[ext] = file_extensions.get(ext, 0) + 1

        result = f"Library scan completed. Found {total_movies} movies.\n"
        result += f"File types: {', '.join([f'{ext}: {count}' for ext, count in file_extensions.items()])}\n"
        result += "Sample movies:\n"
        
        for i, (movie, path) in enumerate(list(movies_paths.items())[:DefaultValues.DEFAULT_SAMPLE_MOVIES]):
            result += f"- {movie}\n"
        
        if total_movies > DefaultValues.DEFAULT_SAMPLE_MOVIES:
            result += f"... and {total_movies - DefaultValues.DEFAULT_SAMPLE_MOVIES} more"
        
        return result


library_manager = ToolAgent([LibraryManagerTool()])

if __name__ == "__main__":
    movies = scan_smb_movie_library()
    logger.info(f"Found {len(movies)} movies:")
    for movie, path in movies.items():
        logger.info(f"  {movie} - {path}")

