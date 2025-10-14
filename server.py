"""
FastMCP quickstart example.

cd to the `examples/snippets/clients` directory and run:
    uv run server fastmcp_quickstart stdio
"""

from mcp.server.fastmcp import FastMCP

# Create an MCP server
# mcp = FastMCP("Demo")
# mcp = FastMCP("My MCP", host="127.0.0.1", port=3456)
mcp = FastMCP(
    "My MCP",
    host="127.0.0.1",
    port=8000,
    # transport="tcp",  # if you need a different transport
)

# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}"


# Add a prompt
@mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."


if __name__ == "__main__":
    # Ensure the server advertises a canonical SSE endpoint (path-only or absolute)
    # Adjust this value to match where clients should connect.
    public_base = "http://127.0.0.1:8000/sse"

    # Try to set common FastMCP/public attributes if available (safe no-op otherwise)
    for opt in ("public_url", "public_base", "endpoint", "sse_endpoint", "public_endpoint"):
        if hasattr(mcp, opt):
            try:
                setattr(mcp, opt, public_base)
            except Exception:
                pass

    # If the implementation exposes a transport_config dict, set public_base there
    if getattr(mcp, "transport_config", None) is not None and isinstance(mcp.transport_config, dict):
        mcp.transport_config["public_base"] = public_base

    # Run the server (host/port were set on construction above)
    mcp.run("sse")

