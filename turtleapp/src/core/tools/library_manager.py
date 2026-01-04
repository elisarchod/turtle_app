import os
import re
import difflib
from typing import Dict, List, Tuple

import smbclient as smb_client
from langchain_core.tools import BaseTool

from turtleapp.settings import settings
from turtleapp.src.core.constants import DefaultValues
from turtleapp.src.utils import clean_movie_filename, extract_movie_metadata, handle_service_errors, handle_tool_errors, logger


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
    description: str = """Scan and search your local movie library from SMB shares.

Use when users ask about:
- Specific movies ("Do I have Inception?", "Is Terminator 2 in my library?")
- General library info ("What movies do I own?", "Show my collection")
- File format filtering (only if explicitly requested: "Show me MKV files")

The tool intelligently parses your request and performs server-side filtering
to minimize token usage. Supports fuzzy matching for typos and variations.
File format information is used internally to help match movies, not as a primary filter.

Input: User's natural language query
Output: Relevant movies or library statistics (formatted for minimal tokens)
"""

    def _parse_user_intent(self, message: str) -> Tuple[str, str, str]:
        """Parse user message to extract search intent.
        
        Args:
            message: User's natural language query
            
        Returns:
            Tuple of (search_query, file_format, intent_type)
            - search_query: Extracted search keywords (empty if none)
            - file_format: Detected file format hint (mkv, mp4, etc.) or empty (used for matching, not filtering)
            - intent_type: "specific_search" or "general_scan"
        """
        message_lower = message.lower()
        search_query = ""
        file_format = ""
        intent_type = "general_scan"
        
        # Detect file format hints (for matching assistance, not filtering)
        # Only treat as explicit filter if user says "only", "just", "show me X files"
        format_patterns = {
            'mkv': r'\b(mkv|\.mkv)\b',
            'mp4': r'\b(mp4|\.mp4)\b',
            'avi': r'\b(avi|\.avi)\b',
            'mov': r'\b(mov|\.mov)\b',
            'wmv': r'\b(wmv|\.wmv)\b'
        }
        
        # Check for explicit format filter requests ("show me X files", "only X", "just X files")
        explicit_filter_patterns = [
            r'show\s+me\s+\w+\s+files',
            r'only\s+\w+',
            r'just\s+\w+\s+files',
            r'\w+\s+files\s+only'
        ]
        is_explicit_filter = any(re.search(pattern, message_lower) for pattern in explicit_filter_patterns)
        
        # Extract format hint (for matching assistance)
        for fmt, pattern in format_patterns.items():
            if re.search(pattern, message_lower):
                file_format = fmt
                # Only set as filter intent if explicitly requested
                if is_explicit_filter:
                    intent_type = "format_filter"
                break
        
        # Extract search keywords (remove common stop words and format mentions if not explicit filter)
        stop_words = {'do', 'i', 'have', 'show', 'me', 'my', 'what', 'movies', 'files', 
                     'the', 'a', 'an', 'is', 'in', 'my', 'library', 'collection', 'only', 'just'}
        words = re.findall(r'\b[a-zA-Z0-9]+\b', message_lower)
        # Remove format from keywords unless it's part of explicit filter
        keywords = [w for w in words if w not in stop_words and (w != file_format or is_explicit_filter)]
        
        if keywords:
            search_query = ' '.join(keywords)
            if intent_type == "general_scan":
                intent_type = "specific_search"
        
        return (search_query, file_format, intent_type)
    
    def _filter_by_extension(self, movies: Dict[str, str], format: str) -> Dict[str, str]:
        """Filter movies dictionary by file extension.
        
        Args:
            movies: Dictionary of movie_name -> file_path
            format: File extension to filter by (mkv, mp4, etc.)
            
        Returns:
            Filtered dictionary with only matching file extensions
        """
        if not format:
            return movies
        
        filtered = {}
        for movie_name, file_path in movies.items():
            ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            if ext == format:
                filtered[movie_name] = file_path
        return filtered
    
    def _search_movies(self, movies: Dict[str, str], query: str, limit: int = 20, format_hint: str = "") -> List[Tuple[str, str, float]]:
        """Search movies with fuzzy matching.
        
        Uses progressive fallback strategy:
        1. Exact substring match (score: 1.0)
        2. All keywords present (score: 0.9)
        3. Fuzzy similarity using difflib (threshold: 0.6)
        4. Partial keyword match (score: 0.5 * match_ratio)
        
        Format hint can boost scores for matching file extensions (helps with matching, not filtering).
        
        Args:
            movies: Dictionary of movie_name -> file_path
            query: Search query string
            limit: Maximum number of results to return
            format_hint: Optional file format hint to boost matching scores
            
        Returns:
            List of (movie_name, path, score) tuples sorted by relevance
        """
        if not query:
            return [(name, path, 1.0) for name, path in list(movies.items())[:limit]]
        
        query_lower = query.lower()
        query_words = query_lower.split()
        results = []
        
        for movie_name, file_path in movies.items():
            movie_lower = movie_name.lower()
            score = 0.0
            
            # Strategy 1: Exact substring match
            if query_lower in movie_lower:
                score = 1.0
            # Strategy 2: All keywords present
            elif all(word in movie_lower for word in query_words):
                score = 0.9
            # Strategy 3: Fuzzy similarity
            else:
                similarity = difflib.SequenceMatcher(None, query_lower, movie_lower).ratio()
                if similarity >= 0.6:
                    score = similarity
                # Strategy 4: Partial keyword match
                else:
                    matched_words = sum(1 for word in query_words if word in movie_lower)
                    if matched_words > 0:
                        score = 0.5 * (matched_words / len(query_words))
            
            # Boost score if format hint matches file extension (helps with matching)
            if format_hint and score > 0:
                file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
                if file_ext == format_hint:
                    score = min(1.0, score * 1.1)  # Small boost for format match
            
            if score > 0:
                results.append((movie_name, file_path, score))
        
        # Sort by score (descending) and limit results
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:limit]
    
    def _format_output(self, all_movies: Dict[str, str], results: List[Tuple[str, str, float]], 
                      query: str, intent: str) -> str:
        """Format output based on result count (tiered strategy).
        
        Tier 1 (1-5 specific results): Detailed listing with metadata
        Tier 2 (6-20 results): Summarized with top matches + count
        Tier 3 (general scan / 20+ results): Statistics + 5 samples
        
        Args:
            all_movies: Complete dictionary of all movies
            results: List of (movie_name, path, score) tuples
            query: Original search query
            intent: Intent type from parsing
            
        Returns:
            Formatted output string
        """
        result_count = len(results)
        total_movies = len(all_movies)
        
        # Tier 1: 1-5 specific results - detailed listing
        if result_count <= 5 and intent in ("specific_search", "format_filter"):
            output = f"Found {result_count} movie{'s' if result_count != 1 else ''}"
            if query:
                output += f" matching '{query}'"
            if result_count > 0:
                output += ":\n\n"
                for movie_name, file_path, score in results:
                    metadata = extract_movie_metadata(os.path.basename(file_path))
                    output += f"{movie_name}"
                    if metadata.get('year'):
                        output += f" ({metadata['year']})"
                    if metadata.get('quality'):
                        output += f" [{metadata['quality']}]"
                    output += f"\nFormat: {metadata['format']} | Path: {file_path}\n\n"
            else:
                output += ".\n"
            return output.strip()
        
        # Tier 2: 6-20 results - summarized
        elif result_count <= 20 and intent in ("specific_search", "format_filter"):
            output = f"Found {result_count} movies"
            if query:
                output += f" matching '{query}'"
            output += ". Top matches:\n\n"
            for movie_name, file_path, score in results[:5]:
                metadata = extract_movie_metadata(os.path.basename(file_path))
                output += f"- {movie_name}"
                if metadata.get('year'):
                    output += f" ({metadata['year']})"
                output += f"\n"
            if result_count > 5:
                output += f"\n... and {result_count - 5} more"
            return output.strip()
        
        # Tier 3: General scan or 20+ results - statistics
        else:
            file_extensions = {}
            for movie_name, file_path in all_movies.items():
                ext = os.path.splitext(file_path)[1].lower()
                file_extensions[ext] = file_extensions.get(ext, 0) + 1

        result = f"Library scan completed. Found {total_movies} movies.\n"
        result += f"File types: {', '.join([f'{ext}: {count}' for ext, count in file_extensions.items()])}\n"
        result += "Sample movies:\n"
        
            sample_movies = list(all_movies.items())[:DefaultValues.DEFAULT_SAMPLE_MOVIES]
            for movie, path in sample_movies:
            result += f"- {movie}\n"
        
        if total_movies > DefaultValues.DEFAULT_SAMPLE_MOVIES:
            result += f"... and {total_movies - DefaultValues.DEFAULT_SAMPLE_MOVIES} more"
        
        return result

    @handle_tool_errors(default_return="Library scan failed")
    def _run(self, user_message: str = "") -> str:
        """Enhanced with smart search and filtering.

        Args:
            user_message: Full user query (e.g., "Do I have Inception?", "show mkv files")

        Returns:
            Formatted results based on query type and result count
        """
        # Parse user intent
        search_query, file_format, intent_type = self._parse_user_intent(user_message)

        # Scan SMB library (full scan)
        all_movies = scan_smb_movie_library()

        # Only filter by format if explicitly requested (format_filter intent)
        # Otherwise, use format as a hint for matching
        if intent_type == "format_filter" and file_format:
            filtered_movies = self._filter_by_extension(all_movies, file_format)
        else:
            filtered_movies = all_movies

        # Search with fuzzy matching if query detected
        # Pass format_hint to boost matching scores (not for filtering)
        if search_query:
            search_results = self._search_movies(filtered_movies, search_query, limit=20, format_hint=file_format)
        else:
            search_results = [(name, path, 1.0) for name, path in list(filtered_movies.items())[:20]]

        # Format output based on result count (tiered strategy)
        return self._format_output(all_movies, search_results, search_query, intent_type)


library_manager_tool = LibraryManagerTool()

if __name__ == "__main__":
    movies = scan_smb_movie_library()
    logger.info(f"Found {len(movies)} movies:")
    for movie, path in movies.items():
        logger.info(f"  {movie} - {path}")

