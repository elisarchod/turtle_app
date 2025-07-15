"""Constants for the turtle app."""

from enum import Enum


class NodeNames(Enum):
    """Node names for the workflow graph."""
    SUPERVISOR = "supervisor"
    MOVIE_RETRIEVER = "movie_retriever"
    TORRENT_MANAGER = "torrent_info"
    LIBRARY_MANAGER = "library_manager"


class ConfigKeys(Enum):
    """Configuration keys for settings."""
    THREAD_ID = "thread_id"
    CONFIGURABLE = "configurable"
    MESSAGES = "messages"


class DefaultValues:
    """Default values for the application."""
    DEFAULT_TEMPERATURE = 0.0
    DEFAULT_SAMPLE_MOVIES = 5


class FileExtensions:
    """Supported file extensions."""
    MOVIE_EXTENSIONS = ('.mkv', '.mp4', '.avi', '.mov', '.wmv')