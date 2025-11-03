"""Main bridge orchestrator connecting MCP and Neuro-API."""

import logging

import trio
from libcomponent.component import ExternalRaiseManager

from neuro_mcp.mcp_client import MCPClient
from neuro_mcp.neuro_client import NeuroMCPClient
from neuro_mcp.translation import (
    mcp_tool_to_neuro_action,
    parse_action_data,
    ToolRegistry,
)
from neuro_api.api import NeuroAction

logger = logging.getLogger(__name__)


class NeuroMCPBridge:
    """Bridge between Neuro-API and MCP protocols.

    This class orchestrates the translation between MCP tools and Neuro actions,
    connecting to a Neuro server as a client and managing MCP client connections.
    """

    def __init__(
        self,
        neuro_websocket_url: str = "ws://localhost:8000",
        game_name: str = "NeuroMCP",
        mcp_server_url: str = "http://localhost:3000/mcp",
    ):
        """Initialize the bridge.

        Args:
            neuro_websocket_url: WebSocket URL of the Neuro server
            game_name: Name of the game/application
            mcp_server_url: URL of the MCP server endpoint
        """
        self.neuro_websocket_url = neuro_websocket_url
        self.game_name = game_name
        self.mcp_server_url = mcp_server_url

        # Initialize components
        self.mcp_client = MCPClient(mcp_server_url)
        self.neuro_client = NeuroMCPClient(game_name, self._handle_neuro_action)
        self.tool_registry = ToolRegistry()

    async def _handle_neuro_action(self, action: NeuroAction) -> tuple[bool, str]:
        """Handle action execution from Neuro side.

        This is called when Neuro requests to execute an action.
        We translate it to an MCP tool call.

        Args:
            action: Neuro action to execute

        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Bridge handling Neuro action: {action.name}")

        # Look up the original MCP tool name
        mcp_tool_name = self.tool_registry.get_mcp_tool_name(action.name)

        if not mcp_tool_name:
            error_msg = f"No MCP tool found for action: {action.name}"
            logger.error(error_msg)
            return False, error_msg

        # Parse the action data
        arguments = parse_action_data(action.data)
        logger.debug(f"Parsed arguments: {arguments}")

        # Call the MCP tool
        success, result = await self.mcp_client.call_tool(mcp_tool_name, arguments)

        return success, result

    async def _sync_tools(self) -> None:
        """Synchronize MCP tools as Neuro actions.

        This discovers all available MCP tools and registers them
        as Neuro actions.
        """
        logger.info("Synchronizing MCP tools to Neuro actions...")

        # Refresh MCP capabilities
        await self.mcp_client.refresh_capabilities()

        # Convert tools to actions
        neuro_actions = []
        self.tool_registry.clear()

        for tool in self.mcp_client.tools:
            try:
                action = mcp_tool_to_neuro_action(tool)
                neuro_actions.append(action)

                # Register the mapping
                self.tool_registry.register(action.name, tool.name)

                logger.info(f"Mapped tool: {tool.name} -> {action.name}")

            except Exception as e:
                logger.error(f"Failed to convert tool {tool.name}: {e}", exc_info=True)

        # Update the Neuro client with the actions
        self.neuro_client.set_actions(neuro_actions)

        logger.info(f"Synchronized {len(neuro_actions)} tools as Neuro actions")

    async def _monitor_connections(self) -> None:
        """Monitor and log connection status."""
        while True:
            await trio.sleep(30)
            connected = "connected" if not self.neuro_client.not_connected else "disconnected"
            logger.info(f"Status: Neuro client {connected}")
            logger.debug(f"Available actions: {self.tool_registry.get_all_neuro_actions()}")

    async def run(self) -> None:
        """Run the bridge.

        This connects to both the MCP server and the Neuro server,
        and synchronizes tools between them.
        """
        logger.info("Starting NeuroMCP Bridge...")
        logger.info(f"MCP server: {self.mcp_server_url} (Streamable HTTP)")
        logger.info(f"Neuro server: {self.neuro_websocket_url}")

        async with self.mcp_client:
            # Synchronize tools
            await self._sync_tools()

            # Connect to Neuro server and run
            async with trio.open_nursery() as nursery:
                # Create event manager for the Neuro client
                event_manager = ExternalRaiseManager(
                    "neuromcp",
                    nursery,
                    "bridge",
                )
                event_manager.add_component(self.neuro_client)

                # Start connection to Neuro server
                nursery.start_soon(
                    self.neuro_client.setup_connection,
                    self.neuro_websocket_url
                )

                # Start monitoring task
                nursery.start_soon(self._monitor_connections)

                logger.info("Bridge is running. Press Ctrl+C to stop.")

    async def refresh_tools(self) -> None:
        """Manually refresh the tool list from MCP server.

        This can be called to update the available tools without restarting.
        """
        logger.info("Manually refreshing tools...")
        await self._sync_tools()


async def main(
    mcp_server_url: str = "http://localhost:3000/mcp",
    neuro_websocket_url: str = "ws://localhost:8000",
    game_name: str = "NeuroMCP",
) -> None:
    """Main entry point for running the bridge.

    Args:
        mcp_server_url: URL of the MCP server endpoint
        neuro_websocket_url: WebSocket URL of the Neuro server
        game_name: Name of the game/application
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run the bridge
    bridge = NeuroMCPBridge(
        neuro_websocket_url=neuro_websocket_url,
        game_name=game_name,
        mcp_server_url=mcp_server_url,
    )

    try:
        await bridge.run()
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user")
    except Exception as e:
        logger.error(f"Bridge failed: {e}", exc_info=True)
        raise
