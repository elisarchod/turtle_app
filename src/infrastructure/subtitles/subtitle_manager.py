"""OpenSubtitles.com REST API v1 client using httpx."""

import re
from pathlib import Path

import httpx

from infrastructure.config.settings import settings
from core.utils import handle_service_errors, logger

_BASE_URL = "https://api.opensubtitles.com/api/v1"


class SubtitleManager:
    """Wrapper around OpenSubtitles.com REST API v1 for subtitle search and download."""

    def __init__(self):
        self._token: str | None = None
        self._client = httpx.Client(
            base_url=_BASE_URL,
            headers={
                "Api-Key": settings.opensubtitles.api_key,
                "Content-Type": "application/json",
                "User-Agent": "TurtleApp/1.0",
            },
            timeout=15,
        )

    def _ensure_authenticated(self) -> None:
        """Login and cache JWT token."""
        if self._token:
            return
        resp = self._client.post(
            "/login",
            json={
                "username": settings.opensubtitles.username,
                "password": settings.opensubtitles.password,
            },
        )
        resp.raise_for_status()
        self._token = resp.json()["token"]
        self._client.headers["Authorization"] = f"Bearer {self._token}"
        logger.info("OpenSubtitles authentication successful")

    @handle_service_errors("OpenSubtitles", default_return=[])
    def search_subtitles(
        self,
        query: str,
        languages: list[str] | None = None,
        year: int | None = None,
    ) -> list[dict]:
        """Search subtitles and return top results sorted by download count."""
        self._ensure_authenticated()

        if languages is None:
            languages = settings.opensubtitles.default_languages

        params: dict = {"query": query, "languages": ",".join(languages)}
        if year:
            params["year"] = year

        resp = self._client.get("/subtitles", params=params)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        results = []
        for item in data:
            attrs = item.get("attributes", {})
            files = attrs.get("files", [])
            file_id = files[0].get("file_id") if files else None
            feature = attrs.get("feature_details") or {}

            if year:
                release_year = self._extract_year(attrs.get("release", ""))
                if release_year and release_year != year:
                    continue

            results.append({
                "file_id": file_id,
                "language": attrs.get("language"),
                "downloads": attrs.get("download_count", 0),
                "rating": attrs.get("ratings", 0),
                "release": attrs.get("release", ""),
                "format": attrs.get("format", ""),
                "title": feature.get("title", query),
                "year": feature.get("year"),
            })

        results.sort(key=lambda x: x["downloads"], reverse=True)
        return results

    @handle_service_errors("OpenSubtitles", default_return=False)
    def download_subtitle(self, file_id: int, save_path: str) -> bool:
        """Download subtitle file by file_id and save to save_path."""
        self._ensure_authenticated()

        resp = self._client.post("/download", json={"file_id": file_id})
        resp.raise_for_status()
        link = resp.json().get("link")

        if not link:
            logger.error(f"No download link returned for file_id {file_id}")
            return False

        content = httpx.get(link, timeout=30).content

        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

        logger.info(f"Subtitle saved to {save_path}")
        return True

    def _extract_year(self, release_string: str) -> int | None:
        """Extract year from release string (e.g., 'Inception.2010.1080p' -> 2010)."""
        match = re.search(r'\b(19|20)\d{2}\b', release_string)
        return int(match.group()) if match else None

    def _format_subtitle_info(self, subtitle_data: dict) -> str:
        """Format subtitle metadata as a pipe-separated string for display."""
        parts = [
            f"Language: {subtitle_data.get('language', 'Unknown')}",
            f"Downloads: {subtitle_data.get('downloads', 0):,}",
        ]
        if subtitle_data.get("rating"):
            parts.append(f"Rating: {subtitle_data['rating']}/10")
        if subtitle_data.get("release"):
            parts.append(f"Release: {subtitle_data['release']}")
        if subtitle_data.get("format"):
            parts.append(f"Format: {subtitle_data['format']}")
        return " | ".join(parts)
