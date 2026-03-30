"""Standardized error handling utilities."""

import functools
from typing import Any, Callable, TypeVar
from core.utils.log_handler import logger

T = TypeVar('T')


def handle_tool_errors(
    default_return: str = "An error occurred while processing your request.",
    log_error: bool = True
) -> Callable[[Callable[..., T]], Callable[..., T | str]]:
    """
    Decorator for standardized error handling in tools.

    Args:
        default_return: Default message to return on error
        log_error: Whether to log the error

    Returns:
        Decorated function that handles errors consistently
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T | str]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T | str:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.exception(f"Error in {func.__name__}: {e}")
                return f"{default_return} Details: {str(e)}"
        return wrapper
    return decorator


def handle_service_errors(
    service_name: str,
    default_return: Any = None,
    log_error: bool = True
) -> Callable[[Callable[..., T]], Callable[..., T | Any]]:
    """
    Decorator for standardized error handling in service functions.

    Args:
        service_name: Name of the service for logging
        default_return: Default value to return on error
        log_error: Whether to log the error

    Returns:
        Decorated function that handles errors consistently
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T | Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.exception(f"{service_name} error in {func.__name__}: {e}")
                return default_return
        return wrapper
    return decorator
