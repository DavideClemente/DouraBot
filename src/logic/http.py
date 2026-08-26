import aiohttp

# Async HTTP helpers. These replace blocking `requests.get(...)` calls so a slow
# or hanging HTTP request can never stall the Discord event loop (which would
# drop the gateway connection and make the bot appear dead while still running).
# Every request is bounded by a timeout.


async def fetch_json(url: str, headers: dict = None, timeout: int = 10) -> dict:
    """Async GET returning parsed JSON. Raises on HTTP errors or timeout.

    `content_type=None` keeps parsing lenient (like requests), so APIs that
    return JSON with an unexpected Content-Type still parse.
    """
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            return await response.json(content_type=None)


async def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    """Async GET returning the raw response body (e.g. for image downloads)."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()
