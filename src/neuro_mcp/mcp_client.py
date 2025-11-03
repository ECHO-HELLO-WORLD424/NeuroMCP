"""MCP client implementation with Streamable HTTP transport."""

import logging
import os
from typing import Any
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool, Resource

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client that connects to MCP servers via Streamable HTTP transport."""

    def __init__(self, server_url: str):
        """Initialize MCP client.

        Args:
            server_url: URL of the MCP server endpoint (e.g., http://localhost:3000/mcp)
        """
        self.server_url = server_url
        self.session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()
        self._tools: list[Tool] = []
        self._resources: list[Resource] = []
        self._connected: bool = False

    async def connect(self) -> None:
        """Connect to the MCP server using Streamable HTTP transport."""
        logger.info(f"Connecting to MCP server at {self.server_url} via Streamable HTTP")

        # Set NO_PROXY environment variable to bypass proxy for localhost
        # This is needed on systems with system-wide proxy settings
        old_no_proxy = os.environ.get("NO_PROXY", "")
        old_no_proxy_lower = os.environ.get("no_proxy", "")

        # Add localhost to NO_PROXY
        os.environ["NO_PROXY"] = "localhost,127.0.0.1"
        os.environ["no_proxy"] = "localhost,127.0.0.1"

        try:
            # Use Streamable HTTP transport
            # Note: streamablehttp_client is decorated with @asynccontextmanager
            streamable_transport = await self._exit_stack.enter_async_context(
                streamablehttp_client(self.server_url)
            )
            read, write, get_session_id = streamable_transport

            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            # Initialize the session
            await self.session.initialize()
            logger.info("MCP session initialized successfully")

            # Log session ID if available
            session_id = get_session_id()
            if session_id:
                logger.info(f"Session ID: {session_id}")

            # List available tools and resources
            await self.refresh_capabilities()

            # Mark as connected
            self._connected = True
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

    def is_connected(self) -> bool:
        """Check if the client is connected to the MCP server.

        Returns:
            True if connected, False otherwise
        """
        return self._connected and self.session is not None

    async def check_health(self) -> bool:
        """Check if the connection to the MCP server is still alive.

        Attempts to list tools to verify connection health.

        This method is safe to call and will never raise exceptions.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            # Try to list tools with a short timeout
            await self.session.list_tools()
            return True
        except Exception as e:
            # Log at debug level to avoid spam, only info on first detection
            if self._connected:
                logger.info(f"MCP connection lost: {type(e).__name__}")
            logger.debug(f"Health check failed: {e}")
            self._connected = False
            return False

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

            # Check if this is a connection error
            error_str = str(e).lower()
            if any(term in error_str for term in ["connection", "broken", "closed", "timeout", "unreachable"]):
                logger.error("Connection error detected, marking as disconnected")
                self._connected = False

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
        """Disconnect from the MCP server.

        This method is safe to call and will suppress any exceptions
        that occur during cleanup of broken connections.
        """
        logger.info("Disconnecting from MCP server")
        self._connected = False

        try:
            await self._exit_stack.aclose()
        except Exception as e:
            # Suppress exceptions during cleanup of broken connections
            logger.debug(f"Exception during disconnect (expected for broken connections): {e}")

        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
