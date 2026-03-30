"""Centralized prompt management for the turtle-app multi-agent system."""

from .supervisor import SUPERVISOR_PROMPT
from .agents import (
    AGENT_BASE_PROMPT,
    MOVIE_RETRIEVER_PROMPT,
    TORRENT_AGENT_PROMPT,
    SUBTITLE_MANAGER_PROMPT
)

__all__ = [
    "SUPERVISOR_PROMPT",
    "AGENT_BASE_PROMPT",
    "MOVIE_RETRIEVER_PROMPT",
    "TORRENT_AGENT_PROMPT",
    "SUBTITLE_MANAGER_PROMPT"
]
