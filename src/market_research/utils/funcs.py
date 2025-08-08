import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable


def async_to_sync(async_func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Convert an async function to a sync function that handles running event loops.

    This wrapper automatically handles:
    - No event loop: creates one with asyncio.run()
    - Running event loop: tries nest_asyncio first, then thread pool as fallback
    - Jupyter/IPython compatibility with nested event loops

    Args:
        async_func: The async function to wrap

    Returns:
        A sync version of the async function

    Example:
        @async_to_sync
        async def fetch_data(url: str) -> str:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()

        # Now you can call it synchronously
        data = fetch_data("https://example.com")
    """

    @functools.wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            # Check if there's a running event loop
            loop = asyncio.get_running_loop()
            
            # Try to enable nested event loops for Jupyter compatibility
            try:
                import nest_asyncio
                nest_asyncio.apply()
                # With nest_asyncio, we can run async code directly in Jupyter
                return loop.run_until_complete(async_func(*args, **kwargs))
            except ImportError:
                # nest_asyncio not available, fall back to thread pool approach
                pass

            # If we get here, there's a running loop - use thread pool
            def run_in_thread():
                # Create new loop in thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(async_func(*args, **kwargs))
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(None)

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_thread)
                return future.result()

        except RuntimeError:
            # No event loop running - use asyncio.run
            return asyncio.run(async_func(*args, **kwargs))

    return wrapper
