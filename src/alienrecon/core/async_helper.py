"""
Helper module for managing async operations in AlienRecon.

This module provides utilities to handle async operations consistently
across the codebase, avoiding event loop conflicts.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Global event loop for the application
_loop: Optional[asyncio.AbstractEventLoop] = None


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get the current event loop or create a new one if needed."""
    global _loop

    try:
        # Try to get the running loop
        loop = asyncio.get_running_loop()
        return loop
    except RuntimeError:
        # No running loop, check if we have a stored one
        if _loop is not None and not _loop.is_closed():
            asyncio.set_event_loop(_loop)
            return _loop

        # Create a new loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        return _loop


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine in a consistent way."""
    loop = get_or_create_event_loop()

    # If we're already in an async context, we can't use run_until_complete
    try:
        # Check if we're in an async context
        asyncio.current_task()
        # We are in an async context, this shouldn't happen
        # but if it does, we need to handle it differently
        logger.warning("run_async called from within an async context")
        # Create a task and wait for it
        task = asyncio.create_task(coro)
        # This will raise an error, but at least we tried
        return loop.run_until_complete(task)
    except RuntimeError:
        # We're not in an async context, safe to run
        return loop.run_until_complete(coro)


async def ensure_async(coro: Coroutine[Any, Any, T]) -> T:
    """Ensure a coroutine runs in an async context."""
    return await coro


def close_event_loop():
    """Close the global event loop if it exists."""
    global _loop
    if _loop is not None and not _loop.is_closed():
        _loop.close()
        _loop = None
