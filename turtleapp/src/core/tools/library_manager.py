import os
from typing import Dict

import smbclient as smb_client
from langchain_core.tools import BaseTool

from turtleapp.settings import settings
from turtleapp.src.core.constants import DefaultValues
from turtleapp.src.utils import clean_movie_filename, handle_service_errors, handle_tool_errors, logger


class FileExtensions:
    """Supported file extensions."""
    MOVIE_EXTENSIONS = ('.mkv', '.mp4', '.avi', '.mov', '.wmv')

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
    description: str = """Scan and catalog the local movie library from SMB network shares.
    
    Use when users ask about:
    - What movies they already own
    - Library size and statistics
    - File format distribution
    - Movie collection organization
    
    Input: No parameters needed (scans entire configured library)
    Returns: Complete library catalog with statistics
    
    Provides information about:
    - Total number of movies found
    - File format breakdown (MKV, MP4, AVI, etc.)
    - Sample movie titles from collection
    - Library organization insights
    
    Note: Scans configured SMB shares for supported video formats (.mkv, .mp4, .avi, .mov, .wmv)
    """

    @handle_tool_errors(default_return="Library scan failed")
    def _run(self, tool_input: str = "") -> str:
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


library_manager_tool = LibraryManagerTool()

if __name__ == "__main__":
    movies = scan_smb_movie_library()
    logger.info(f"Found {len(movies)} movies:")
    for movie, path in movies.items():
        logger.info(f"  {movie} - {path}")

