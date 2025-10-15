import asyncio
import json
from urllib.parse import urlparse, urljoin
import inspect
import functools
import types
import logging

from fastmcp import Client

# simple logger setup (prints to stdout with timestamps)
logger = logging.getLogger("mcp_inspector")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)


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


def _safe_json(obj):
    try:
        return json.dumps(obj, indent=2, default=str)
    except Exception:
        try:
            return str(obj)
        except Exception:
            return "<unserializable>"


def instrument_client(client, logger=logger):
    """
    Instrument the given client instance to log async method calls and
    their results/exceptions. This works by wrapping coroutine methods
    found on the client's class with logging wrappers bound to the instance.
    """
    seen = set()
    for name in dir(client):
        if name.startswith("_"):
            continue
        if name in seen:
            continue
        seen.add(name)
        # try to detect coroutine methods defined on the class
        cls_attr = getattr(type(client), name, None)
        inst_attr = getattr(client, name, None)
        if callable(inst_attr) and inspect.iscoroutinefunction(cls_attr):
            orig = inst_attr  # bound method
            async def _wrap(*args, __orig=orig, __name=name, **kwargs):
                logger.debug(">>> CALL %s args=%s kwargs=%s", __name, _safe_json(args), _safe_json(kwargs))
                try:
                    result = await __orig(*args, **kwargs)
                    logger.debug("<<< RETURN %s result=%s", __name, _safe_json(result))
                    return result
                except Exception as exc:
                    logger.exception("<<< EXCEPTION %s %s", __name, exc)
                    raise
            # assign wrapper to instance so attribute access uses our wrapper
            setattr(client, name, _wrap)

    # Additionally try to wrap any attribute that looks like a 'send' or 'recv' coroutine
    for name in dir(client):
        if name.startswith("_") or name in seen:
            continue
        try:
            inst_attr = getattr(client, name)
            if callable(inst_attr) and inspect.iscoroutinefunction(inst_attr) and ("send" in name.lower() or "recv" in name.lower() or "receive" in name.lower()):
                orig = inst_attr
                async def _wrap_io(*args, __orig=orig, __name=name, **kwargs):
                    logger.debug(">>> IO %s args=%s kwargs=%s", __name, _safe_json(args), _safe_json(kwargs))
                    try:
                        res = await __orig(*args, **kwargs)
                        logger.debug("<<< IO %s result=%s", __name, _safe_json(res))
                        return res
                    except Exception as exc:
                        logger.exception("<<< IO EXC %s %s", __name, exc)
                        raise
                setattr(client, name, _wrap_io)
        except Exception:
            # be resilient to weird attributes
            continue

    # If the client exposes a last_endpoint-like attribute, log changes (best-effort).
    if hasattr(client, "_last_endpoint"):
        try:
            logger.debug("client initial _last_endpoint=%s", getattr(client, "_last_endpoint"))
        except Exception:
            pass

    return client


async def main(url: str | None = None):
    """
    Run the inspector. If `url` is provided use it as the client base URL.
    This lets tests/run_with_stub.py pass the server endpoint directly.
    """
    base = url or "http://127.0.0.1:8000/sse"
    logger.debug("Inspector will connect to %s", base)

    # open client normally, then instrument the instance so calls are logged
    try:
        async with Client(base) as client:
            instrument_client(client, logger)

            logger.debug("Calling list_tools() to trigger handshake/requests")
            try:
                tools = await client.list_tools()
                logger.debug("list_tools returned: %s", _safe_json(tools))
                print("Tools:", tools)
            except Exception as exc:
                logger.exception("Error calling list_tools(): %s", exc)
                # expose last endpoint if available
                raw_endpoint = getattr(client, "_last_endpoint", None)
                if raw_endpoint:
                    from urllib.parse import urljoin
                    fixed = normalize_endpoint(base, raw_endpoint)
                    logger.debug("Normalized endpoint suggestion: %s", fixed)
                raise
    except Exception:
        logger.exception("Failed to run inspector (connection/handshake failed)")
        raise


if __name__ == "__main__":
    asyncio.run(main())
