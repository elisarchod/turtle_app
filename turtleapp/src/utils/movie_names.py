import os
import re


def clean_movie_filename(filename: str) -> str:
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

