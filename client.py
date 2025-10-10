import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import json


async def spell_casting(session):
    result = await session.call_tool("spell_casting_tool")
    return result


async def main():
    params = StdioServerParameters(command="python", args=["server.py"])
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("greet_tool", {"name": "Preetansha"})
            print("Tool response:", result.content)
            
            # a = int(input("Enter the value of a: "))
            # b = int(input("Enter the value of b: "))
            
            # if a>10 or b>10:
            #     print("Invalid input")
            
            # else:
            #     result2 = await session.call_tool("add_tool", {
            #         "a": a, 
            #         "b":b
            #     })
            #     print("Tool response:", result2.content)
                
            spells = await spell_casting(session)
            content = spells.content

            if hasattr(content, "text"):
                # It's a TextContent object
                data = json.loads(content.text)
                print("I am in the if block")
                print(json.dumps(data["json"], indent=2))
            
            elif isinstance(content, dict) and "json" in content:
                # It's a dictionary with a "json" field
                print(json.dumps(content["json"], indent=2))
                print("I am in the else-if block")
                
            else:
                print("I am in the else block")
                print(content)
                
            
            
config = {
    "mcpServers": {
        "server_name": {
            # Remote HTTP/SSE server
            "transport": "http",  # or "sse" 
            "url": "https://api.example.com/mcp",
            "headers": {"Authorization": "Bearer token"},
            "auth": "oauth"  # or bearer token string
        },
        "local_server": {
            # Local stdio server
            "transport": "stdio",
            "command": "python",
            "args": ["./server.py", "--verbose"],
            "env": {"DEBUG": "true"},
            "cwd": "/path/to/server",
        }
    }
}
asyncio.run(main())