"""Mock MCP server for testing the NeuroMCP bridge.

This creates a simple MCP server with a few test tools using Streamable HTTP transport.
"""

import logging
from contextlib import asynccontextmanager
from mcp.server import Server
from mcp import types
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("mock-mcp-server")

# Create MCP server
mcp_server = Server("mock-mcp-server")


@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools."""
    logger.info("list_tools called")
    return [
        types.Tool(
            name="echo",
            description="Echo back the provided message",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to echo back"
                    }
                },
                "required": ["message"]
            }
        ),
        types.Tool(
            name="add",
            description="Add two numbers together",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number"
                    }
                },
                "required": ["a", "b"]
            }
        ),
        types.Tool(
            name="greet",
            description="Generate a greeting message",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name to greet"
                    },
                    "style": {
                        "type": "string",
                        "enum": ["formal", "casual", "enthusiastic"],
                        "description": "Greeting style"
                    }
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="current_time",
            description="Get the current time",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent]:
    """Handle tool execution."""
    logger.info(f"Tool called: {name} with args: {arguments}")

    if name == "echo":
        message = arguments.get("message", "")
        return [types.TextContent(type="text", text=f"Echo: {message}")]

    elif name == "add":
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        result = a + b
        return [types.TextContent(type="text", text=f"Result: {result}")]

    elif name == "greet":
        name_arg = arguments.get("name", "stranger")
        style = arguments.get("style", "casual")

        greetings = {
            "formal": f"Good day, {name_arg}. How may I assist you?",
            "casual": f"Hey {name_arg}! What's up?",
            "enthusiastic": f"Hello {name_arg}!!! So great to see you!!! 🎉"
        }
        greeting = greetings.get(style, greetings["casual"])
        return [types.TextContent(type="text", text=greeting)]

    elif name == "current_time":
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return [types.TextContent(type="text", text=f"Current time: {now}")]

    else:
        raise ValueError(f"Unknown tool: {name}")


# Create Streamable HTTP session manager
session_manager = StreamableHTTPSessionManager(mcp_server)


@asynccontextmanager
async def lifespan(app):
    """Manage the session manager lifecycle."""
    logger.info("Starting session manager...")
    async with session_manager.run():
        logger.info("Session manager running")
        yield
    logger.info("Session manager stopped")


class MCPEndpoint:
    """ASGI endpoint for handling MCP requests via Streamable HTTP."""

    async def __call__(self, scope, receive, send):
        """Handle the MCP endpoint as an ASGI app."""
        logger.info(f"{scope['method']} request from {scope.get('client')}")
        await session_manager.handle_request(scope, receive, send)


# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route("/mcp", endpoint=MCPEndpoint(), methods=["GET", "POST", "DELETE"]),
    ],
    lifespan=lifespan
)


def main():
    """Run the mock MCP server."""
    print("\n" + "=" * 60)
    print("Mock MCP Server")
    print("=" * 60)
    print("\nServing MCP tools via Streamable HTTP at:")
    print("  http://localhost:3000/mcp")
    print("\nAvailable tools:")
    print("  - echo: Echo back a message")
    print("  - add: Add two numbers")
    print("  - greet: Generate a greeting")
    print("  - current_time: Get current time")
    print("\n" + "=" * 60 + "\n")

    uvicorn.run(
        app,
        host="localhost",
        port=3000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
