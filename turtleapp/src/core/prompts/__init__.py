"""
Centralized prompt management for the turtle-app multi-agent system.

This module provides a robust, path-independent approach to managing prompts
by storing them as Python constants rather than external files.
"""

from .supervisor import SUPERVISOR_PROMPT
from .agents import (
    AGENT_BASE_PROMPT,
    MOVIE_RETRIEVER_PROMPT
)

__all__ = [
    "SUPERVISOR_PROMPT",
    "AGENT_BASE_PROMPT",
    "MOVIE_RETRIEVER_PROMPT"
]