import os
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.tools import BaseTool

from turtleapp.config.settings import CREDENTIALS, SERVER, SHARE
from turtleapp.src.utils.log_handler import logger




# Movie file extensions
MOVIE_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}

def scan_samba_directory(conn, share: str, path: str) -> List[Dict[str, Any]]:
    movies = []
    
    files = conn.listPath(share, path or "/")
    
    for file_info in files:
        if file_info.filename in ['.', '..']:
            continue
        
        file_path = f"{path}/{file_info.filename}" if path else file_info.filename
        
        if file_info.isDirectory:
            try:
                movies.extend(scan_samba_directory(conn, share, file_path))
            except:
                pass  # Skip inaccessible directories
        elif is_movie_file(file_info.filename):
            movies.append({
                'name': Path(file_info.filename).stem,
                'path': f"smb://{conn.remote_name}/{share}/{file_path}".replace('//', '/')
            })
        
    return movies

def is_movie_file(filename: str) -> bool:
    """Check if a file is a movie based on its extension."""
    return Path(filename).suffix.lower() in MOVIE_EXTENSIONS

def get_movies() -> List[Dict[str, Any]]:
    if not SERVER or not SHARE:
        return [{'name': 'Error', 'path': 'Missing SAMBA_SERVER or SAMBA_SHARE environment variables'}]
    
    try:
        from smb.SMBConnection import SMBConnection
        
        conn = SMBConnection(CREDENTIALS['user'], CREDENTIALS['password'], "client", SERVER, use_ntlm_v2=True)
        if not conn.connect(SERVER, 445):
            return [{'name': 'Error', 'path': 'Failed to connect to Samba server'}]
        
        movies = scan_samba_directory(conn, SHARE, "")
        conn.close()
        
        return sorted(movies, key=lambda x: x['name'].lower())
        
    except Exception as e:
        logger.error(f"Samba scan failed: {e}")
        return [{'name': 'Error', 'path': f'Error: {str(e)[:50]}'}]

class MovieScannerTool(BaseTool):
    
    name: str = "movie_scanner"
    description: str = "list of available movies"

    def _run(self) -> List[Dict[str, Any]]:
        """Scan for movies and return results."""
        movies = get_movies()
        logger.info(f"Found {len(movies)} movies: {movies}")
        return movies

movie_scanner_tool = MovieScannerTool()

if __name__ == "__main__":
    movies = get_movies()
    print(f"Scanning Samba server: {SERVER}")
    print(f"Found {len(movies)} movies:")
    
    for movie in movies:
        print(f"  {movie['name']} - {movie['path']}") 