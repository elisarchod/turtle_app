import os
import re


def clean_movie_filename(filename: str) -> str:
    """Extract clean movie title from filename by removing metadata and truncating.

    Strips file extension, special characters, and applies smart truncation:
    1. If filename contains a 4-digit year (after 5+ chars), keep everything up to
       and including the year, discard the rest (quality, codec, release group, etc.)
    2. Otherwise, truncate to first 30 characters maximum

    Examples:
        "Terminator.2.1991.1080p.BluRay.x264-GROUP.mkv" -> "Terminator 2 1991"
        "The.Matrix.1999.REMASTERED.2160p.mkv" -> "The Matrix 1999"
        "Some.Very.Long.Movie.Title.Here.mkv" -> "Some Very Long Movie Title Her"

    Regex explanation: ^(.{5}.*?\d{4}).*|^(.{30}).*
        - (.{5}.*?\d{4}): Capture 5+ chars + shortest match to year (group 1)
        - |: OR operator
        - (.{30}): Capture first 30 chars (group 2)
        - Replacement uses \1\2 to return whichever group matched

    Args:
        filename: Movie filename with or without extension

    Returns:
        Cleaned title string (alphanumeric + spaces only)
    """
    name_without_ext = os.path.splitext(filename)[0]
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', name_without_ext)
    return re.sub(r'^(.{5}.*?\d{4}).*|^(.{30}).*', r'\1\2', clean)


def extract_movie_metadata(filename: str) -> dict:
    """Extract metadata from movie filename.

    Args:
        filename: Movie filename (e.g., "Terminator.2.1991.1080p.BluRay.mkv")

    Returns:
        {
            'title': str,           # Cleaned movie title
            'year': str | None,     # Release year (YYYY)
            'quality': str | None,  # Quality tag (1080p, 720p, 4K, BluRay, etc.)
            'format': str           # File extension (.mkv, .mp4, etc.)
        }
    """
    name_without_ext = os.path.splitext(filename)[0]

    metadata = {
        'title': clean_movie_filename(filename),
        'year': None,
        'quality': None,
        'format': os.path.splitext(filename)[1].lower()
    }

    # Extract year: look for 4-digit year (1900-2099)
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', name_without_ext)
    if year_match:
        metadata['year'] = year_match.group(1)

    # Extract quality: common video quality indicators
    quality_patterns = r'(1080p|720p|2160p|4K|BluRay|BRRip|WEB-DL|WEBRip|HDRip)'
    quality_match = re.search(quality_patterns, name_without_ext, re.IGNORECASE)
    if quality_match:
        metadata['quality'] = quality_match.group(1)

    return metadata

