import asyncio
import json
from urllib.parse import urlparse, urljoin

from fastmcp import Client

def normalize_endpoint(base_url: str, endpoint: str) -> str:
    # if endpoint is absolute, return as-is
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    parsed = urlparse(base_url)
    parts = endpoint.split("/")  # endpoint begins with '/'
    # pattern: /<host>/messages/..., remove the embedded host segment
    if len(parts) > 2 and parts[1] == parsed.hostname:
        endpoint = "/" + "/".join(parts[2:])
    return urljoin(base_url, endpoint)

async def main():
    base = "http://127.0.0.1:8000/sse"
    async with Client(base) as client:
        # client.list_tools() will trigger the handshake; the client library may read an "endpoint" event
        # if your Client exposes the raw endpoint, normalize it; otherwise intercept the endpoint string
        # (example assumes client returns the endpoint string in client._last_endpoint or similar)
        # adapt to your Client API if needed.
        try:
            tools = await client.list_tools()
            print("Tools:", tools)
        except Exception as exc:
            # Inspect the endpoint reported by the library/server if available
            raw_endpoint = getattr(client, "_last_endpoint", None)
            if raw_endpoint:
                fixed = normalize_endpoint(base, raw_endpoint)
                print("Normalized endpoint:", fixed)
                # Optionally retry using fixed endpoint (depends on Client API)
            raise
    
    # async with Client("http://127.0.0.1:8000/sse") as client:
    #     print(await client.list_tools())
    #     result = await client.call_tool("add", {"a": 2, "b": 3})
    #     print("Result:", result)

    print("All connection attempts failed. Check server logs, host/port, and transport scheme.")

if __name__ == "__main__":
    asyncio.run(main())
