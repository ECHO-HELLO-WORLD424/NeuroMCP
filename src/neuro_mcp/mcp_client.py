"""MCP client implementation with web transport (SSE/WebSocket)."""

import logging
import os
from typing import Any
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Tool, Resource

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client that connects to MCP servers via web transport."""

    def __init__(self, server_url: str, transport: str = "sse"):
        """Initialize MCP client.

        Args:
            server_url: URL of the MCP server (e.g., http://localhost:3000/sse)
            transport: Transport type ("sse" or "websocket")
        """
        self.server_url = server_url
        self.transport = transport
        self.session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()
        self._tools: list[Tool] = []
        self._resources: list[Resource] = []

    async def connect(self) -> None:
        """Connect to the MCP server."""
        logger.info(f"Connecting to MCP server at {self.server_url} via {self.transport}")

        if self.transport == "sse":
            # Set NO_PROXY environment variable to bypass proxy for localhost
            # This is needed on systems with system-wide proxy settings
            old_no_proxy = os.environ.get("NO_PROXY", "")
            old_no_proxy_lower = os.environ.get("no_proxy", "")

            # Add localhost to NO_PROXY
            os.environ["NO_PROXY"] = "localhost,127.0.0.1"
            os.environ["no_proxy"] = "localhost,127.0.0.1"

            try:
                # Use SSE transport
                sse_transport = await self._exit_stack.enter_async_context(
                    sse_client(self.server_url)
                )
                read, write = sse_transport
                self.session = await self._exit_stack.enter_async_context(
                    ClientSession(read, write)
                )
            finally:
                # Restore original NO_PROXY values
                if old_no_proxy:
                    os.environ["NO_PROXY"] = old_no_proxy
                else:
                    os.environ.pop("NO_PROXY", None)

                if old_no_proxy_lower:
                    os.environ["no_proxy"] = old_no_proxy_lower
                else:
                    os.environ.pop("no_proxy", None)
        else:
            raise NotImplementedError(f"Transport {self.transport} not yet implemented")

        # Initialize the session
        await self.session.initialize()
        logger.info("MCP session initialized successfully")

        # List available tools and resources
        await self.refresh_capabilities()

    async def refresh_capabilities(self) -> None:
        """Refresh the list of available tools and resources."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        # List tools
        tools_response = await self.session.list_tools()
        self._tools = tools_response.tools
        logger.info(f"Discovered {len(self._tools)} MCP tools")

        # List resources
        try:
            resources_response = await self.session.list_resources()
            self._resources = resources_response.resources
            logger.info(f"Discovered {len(self._resources)} MCP resources")
        except Exception as e:
            logger.warning(f"Could not list resources: {e}")
            self._resources = []

    @property
    def tools(self) -> list[Tool]:
        """Get the list of available tools."""
        return self._tools

    @property
    def resources(self) -> list[Resource]:
        """Get the list of available resources."""
        return self._resources

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> tuple[bool, str]:
        """Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments (optional)

        Returns:
            Tuple of (success, result_message)
        """
        if not self.session:
            return False, "Not connected to MCP server"

        try:
            logger.info(f"Calling MCP tool: {tool_name} with args: {arguments}")
            result = await self.session.call_tool(tool_name, arguments or {})

            # Extract content from result
            if result.content:
                # Concatenate all content items
                messages = []
                for item in result.content:
                    if hasattr(item, "text"):
                        messages.append(item.text)
                    elif hasattr(item, "data"):
                        messages.append(str(item.data))
                    else:
                        messages.append(str(item))

                result_text = "\n".join(messages)
                logger.info(f"Tool {tool_name} succeeded: {result_text[:100]}...")
                return True, result_text
            else:
                return True, "Tool executed successfully (no output)"

        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def read_resource(self, uri: str) -> tuple[bool, str]:
        """Read an MCP resource.

        Args:
            uri: Resource URI

        Returns:
            Tuple of (success, content)
        """
        if not self.session:
            return False, "Not connected to MCP server"

        try:
            logger.info(f"Reading MCP resource: {uri}")
            result = await self.session.read_resource(uri)

            # Extract content from result
            if result.contents:
                messages = []
                for item in result.contents:
                    if hasattr(item, "text"):
                        messages.append(item.text)
                    elif hasattr(item, "blob"):
                        messages.append(f"[Binary data: {len(item.blob)} bytes]")
                    else:
                        messages.append(str(item))

                content = "\n".join(messages)
                return True, content
            else:
                return True, "Resource read successfully (no content)"

        except Exception as e:
            error_msg = f"Resource read failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        logger.info("Disconnecting from MCP server")
        await self._exit_stack.aclose()
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
