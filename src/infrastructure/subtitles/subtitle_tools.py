"""Subtitle search and download tools for OpenSubtitles.com."""

import re
from pathlib import Path
from typing import ClassVar

from langchain_core.tools import BaseTool
from pydantic import Field

from infrastructure.subtitles.subtitle_manager import SubtitleManager
from infrastructure.config.settings import settings
from core.utils import handle_tool_errors, logger

_LANGUAGE_MAP: dict[str, str] = {"english": "en", "hebrew": "he", "en": "en", "he": "he"}


def _parse_subtitle_query(query: str) -> tuple[str, int | None, str | None]:
    """Parse query string to extract title, year (optional), and language (optional)."""
    year_match = re.search(r'\b(19|20)\d{2}\b', query)
    year = int(year_match.group()) if year_match else None

    language = None
    for lang_key, lang_code in _LANGUAGE_MAP.items():
        if lang_key in query.lower():
            language = lang_code
            break

    title = query
    if year_match:
        title = title.replace(year_match.group(), "").strip()
    if language:
        for lang_key in _LANGUAGE_MAP:
            title = re.sub(rf'\b{lang_key}\b', '', title, flags=re.IGNORECASE).strip()

    return re.sub(r'\s+', ' ', title).strip(), year, language


class SubtitleSearchTool(BaseTool):
    """Tool for searching subtitles on OpenSubtitles.com."""

    name: str = "search_subtitles"
    description: str = (
        "Search for subtitles on OpenSubtitles.com by movie title. "
        "Input: movie title with optional year and language (e.g. 'Inception 2010 Hebrew'). "
        "Returns top 5 results with quality metrics. Default languages: English and Hebrew."
    )
    manager: SubtitleManager = Field(default_factory=SubtitleManager)

    model_config = {"arbitrary_types_allowed": True}

    @handle_tool_errors(default_return="Subtitle search failed")
    def _run(self, query: str) -> str:
        """Search subtitles and format top 5 results."""
        title, year, language = _parse_subtitle_query(query)
        languages = [language] if language else settings.opensubtitles.default_languages

        results = self.manager.search_subtitles(query=title, languages=languages, year=year)
        if not results:
            return f"No subtitles found for '{title}'" + (f" ({year})" if year else "")

        header = f"Found {len(results)} subtitle(s) for '{title}'" + (f" ({year})" if year else "") + ":\n\n"
        lines = []
        for i, subtitle in enumerate(results[:5], 1):
            file_id = subtitle.get("file_id")
            if not file_id:
                continue
            info = self.manager._format_subtitle_info(subtitle)
            title_line = subtitle.get("title", title)
            year_line = f"   Year: {subtitle['year']}\n" if subtitle.get("year") else ""
            lines.append(f"{i}. File ID: {file_id}\n   {info}\n   Title: {title_line}\n{year_line}")

        return header + "\n".join(lines)


class SubtitleDownloadTool(BaseTool):
    """Tool for downloading subtitles from OpenSubtitles.com."""

    name: str = "download_subtitle"
    description: str = (
        "Download a subtitle file from OpenSubtitles.com. "
        "Input format: 'file_id|movie_path' (e.g. '12345678|/smb/movies/Inception.2010.mkv'). "
        "Saves subtitle as .srt next to the movie file."
    )
    manager: SubtitleManager = Field(default_factory=SubtitleManager)

    model_config = {"arbitrary_types_allowed": True}

    @handle_tool_errors(default_return="Subtitle download failed")
    def _run(self, input_str: str) -> str:
        """Download subtitle by file_id and save next to movie file."""
        parts = input_str.split("|", 1)
        if len(parts) != 2:
            return "Invalid input format. Expected: 'file_id|movie_path'"

        try:
            file_id = int(parts[0].strip())
        except ValueError:
            return f"Invalid file_id: {parts[0]}"

        movie_path = parts[1].strip()
        save_path = _build_subtitle_path(movie_path)
        success = self.manager.download_subtitle(file_id, save_path)

        return f"Subtitle downloaded to: {save_path}" if success else f"Failed to download subtitle (file_id: {file_id})"


def _build_subtitle_path(movie_path: str) -> str:
    """Derive .srt path from movie file path, placed in the same directory."""
    p = Path(movie_path)
    year_match = re.search(r'\b(19|20)\d{2}\b', p.stem)
    if year_match:
        clean = re.sub(r'\b(19|20)\d{2}\b', '', p.stem).strip(' .-_')
        name = f"{clean}.{year_match.group()}.srt"
    else:
        name = f"{p.stem}.srt"
    return str(p.parent / name)


# Module-level instances (lazy auth — no network call until first tool use)
subtitle_search_tool = SubtitleSearchTool()
subtitle_download_tool = SubtitleDownloadTool()
