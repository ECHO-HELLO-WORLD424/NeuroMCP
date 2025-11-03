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

        # Check if MCP client is connected
        if not self.mcp_client.is_connected():
            error_msg = "MCP server is not connected. Cannot execute action."
            logger.error(error_msg)
            return False, error_msg

        # Look up the original MCP tool name
        mcp_tool_name = self.tool_registry.get_mcp_tool_name(action.name)

        if not mcp_tool_name:
            error_msg = f"No MCP tool found for action: {action.name}"
            logger.error(error_msg)
            return False, error_msg

        # Parse the action data
        arguments = parse_action_data(action.data)
        logger.debug(f"Parsed arguments: {arguments}")

        # Call the MCP tool with error handling for disconnection
        try:
            success, result = await self.mcp_client.call_tool(mcp_tool_name, arguments)
            return success, result
        except Exception as e:
            error_msg = f"MCP tool call failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

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

    async def _handle_user_commands(self, cancel_scope) -> None:
        """Handle manual user commands for controlling the bridge.

        Args:
            cancel_scope: Trio cancel scope to signal shutdown
        """
        print("\n" + "=" * 60)
        print("MANUAL CONTROL MODE")
        print("=" * 60)
        print("Available commands:")
        print("  r - Register/sync MCP tools as Neuro actions")
        print("  u - Unregister all actions from Neuro")
        print("  s - Show connection status")
        print("  q - Quit the bridge")
        print("=" * 60)
        print()

        while True:
            try:
                # Get user input in a non-blocking way
                command = await trio.to_thread.run_sync(
                    lambda: input("Enter command (r/u/s/q): ").strip().lower()
                )

                if command == 'r':
                    await self._manual_register()
                elif command == 'u':
                    await self._manual_unregister()
                elif command == 's':
                    await self._show_status()
                elif command == 'q':
                    logger.info("User requested quit. Shutting down bridge...")
                    print("\nShutting down bridge...")
                    cancel_scope.cancel()
                    break
                else:
                    print(f"Unknown command: {command}")
                    print("Valid commands: r (register), u (unregister), s (status), q (quit)")

            except Exception as e:
                logger.error(f"Error handling user command: {e}", exc_info=True)
                print(f"Error: {e}")

    async def _manual_register(self) -> None:
        """Manually register/sync MCP tools as Neuro actions."""
        logger.info("Manual registration requested...")
        print("\nRegistering MCP tools as Neuro actions...")

        try:
            # Sync tools from MCP server (updates local list)
            await self._sync_tools()

            # Actually send registration to Neuro server
            await self.neuro_client.register_actions_with_neuro()

            print(f"✓ Successfully registered {len(self.tool_registry.get_all_neuro_actions())} actions")
        except Exception as e:
            logger.error(f"Failed to register tools: {e}", exc_info=True)
            print(f"✗ Failed to register tools: {e}")

    async def _manual_unregister(self) -> None:
        """Manually unregister all actions from Neuro."""
        logger.info("Manual unregistration requested...")
        print("\nUnregistering all actions from Neuro...")

        try:
            await self.neuro_client.unregister_all_actions()
            print("✓ Successfully unregistered all actions")
        except Exception as e:
            logger.error(f"Failed to unregister actions: {e}", exc_info=True)
            print(f"✗ Failed to unregister actions: {e}")

    async def _show_status(self) -> None:
        """Show current connection and registration status."""
        logger.info("Status check requested...")
        print("\n" + "=" * 60)
        print("BRIDGE STATUS")
        print("=" * 60)

        # Check Neuro connection
        neuro_connected = not self.neuro_client.not_connected
        neuro_status = "✓ Connected" if neuro_connected else "✗ Disconnected"
        print(f"Neuro API:  {neuro_status}")

        # Check MCP connection
        mcp_connected = await self.mcp_client.check_health()
        mcp_status = "✓ Connected" if mcp_connected else "✗ Disconnected"
        print(f"MCP Server: {mcp_status}")

        # Show registered actions
        actions = self.tool_registry.get_all_neuro_actions()
        print(f"\nRegistered actions: {len(actions)}")
        if actions:
            for action in actions:
                mcp_tool = self.tool_registry.get_mcp_tool_name(action)
                print(f"  - {action} (MCP: {mcp_tool})")

        print("=" * 60)
        print()

    async def run(self) -> None:
        """Run the bridge.

        This connects to both the MCP server and the Neuro server,
        and provides manual control for tool registration.
        """
        logger.info("Starting NeuroMCP Bridge...")
        logger.info(f"MCP server: {self.mcp_server_url} (Streamable HTTP)")
        logger.info(f"Neuro server: {self.neuro_websocket_url}")

        async with self.mcp_client:
            # Initial sync of tools
            logger.info("Performing initial tool synchronization...")
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

                # Start manual command handler
                nursery.start_soon(self._handle_user_commands, nursery.cancel_scope)

                logger.info("Bridge is running with manual control enabled.")

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
