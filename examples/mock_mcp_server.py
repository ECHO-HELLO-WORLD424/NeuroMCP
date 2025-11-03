"""Mock MCP server for testing the NeuroMCP bridge.

This creates a simple MCP server with a few test tools using SSE transport.
"""

import logging
from mcp.server import Server
from mcp import types
from mcp.server.sse import SseServerTransport
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


# Create SSE transport
sse = SseServerTransport("/messages")


async def handle_sse_endpoint(request):
    """Handle the SSE endpoint for streaming."""
    logger.info(f"SSE connection request from {request.client}")

    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (read_stream, write_stream):
        logger.info("SSE connection established, running MCP server")
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )


class MessagesEndpoint:
    """ASGI endpoint for handling POST messages."""

    async def __call__(self, scope, receive, send):
        """Handle the messages endpoint as an ASGI app."""
        logger.info(f"POST message from {scope.get('client')}")
        await sse.handle_post_message(scope, receive, send)


# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse_endpoint),
        Route("/messages", endpoint=MessagesEndpoint(), methods=["POST"]),
    ]
)


def main():
    """Run the mock MCP server."""
    print("\n" + "=" * 60)
    print("Mock MCP Server")
    print("=" * 60)
    print("\nServing MCP tools via SSE at:")
    print("  http://localhost:3000/sse")
    print("\nAvailable tools:")
    print("  - echo: Echo back a message")
    print("  - add: Add two numbers")
    print("  - greet: Generate a greeting")
    print("  - current_time: Get current time")
    print("\n" + "=" * 60 + "\n")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=3000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
