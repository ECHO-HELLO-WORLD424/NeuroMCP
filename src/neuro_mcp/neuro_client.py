"""Neuro-API client component for the bridge."""

import logging
from typing import Callable, Awaitable

from neuro_api.trio_ws import TrioNeuroAPIComponent
from neuro_api.api import NeuroAction
from neuro_api.command import Action

logger = logging.getLogger(__name__)


class NeuroMCPClient(TrioNeuroAPIComponent):
    """Neuro client that bridges to MCP.

    This component connects to a Neuro server (like ConsoleInteractiveNeuroServer)
    and registers MCP tools as Neuro actions.
    """

    def __init__(
        self,
        game_name: str,
        action_handler: Callable[[NeuroAction], Awaitable[tuple[bool, str]]],
    ):
        """Initialize the Neuro MCP client.

        Args:
            game_name: Name of the game/application
            action_handler: Async function to handle action execution
        """
        super().__init__("NeuroMCPClient", game_name)
        self._action_handler = action_handler
        self._registered_actions: list[Action] = []
        self._action_handlers: dict[str, Callable] = {}

    def set_actions(self, actions: list[Action]) -> None:
        """Set the available actions to register with Neuro.

        Args:
            actions: List of Action objects (converted from MCP tools)
        """
        self._registered_actions = actions
        logger.info(f"Set {len(actions)} available actions")

    async def setup_connection(self, websocket_url: str) -> None:
        """Connect to the Neuro server and register actions.

        Args:
            websocket_url: WebSocket URL of the Neuro server (e.g., ws://localhost:8000)
        """
        logger.info(f"Connecting to Neuro server at {websocket_url}")

        try:
            # Open WebSocket connection
            import trio_websocket

            async with trio_websocket.open_websocket_url(websocket_url) as websocket:
                logger.info("WebSocket connection established")
                self.connect(websocket)
                await self.websocket_connect_successful()

                # Send startup command
                await self.send_startup_command()
                logger.info("Sent startup command")

                # Register all actions
                if self._registered_actions:
                    await self.register_actions_with_neuro()
                else:
                    logger.warning("No actions to register")

                logger.info("Connected and ready")

                # Keep reading messages from the server
                try:
                    while not self.not_connected:
                        await self.read_message()
                except Exception as e:
                    logger.error(f"Error reading messages: {e}", exc_info=True)
                finally:
                    self.connect(None)
                    logger.info("WebSocket connection closed")

        except Exception as e:
            logger.error(f"Failed to connect to Neuro server: {e}", exc_info=True)
            raise

    async def register_actions_with_neuro(self) -> None:
        """Register all MCP tools as Neuro actions."""
        if not self._registered_actions:
            logger.warning("No actions to register")
            return

        logger.info(f"Registering {len(self._registered_actions)} actions with Neuro")

        # Create action handlers for each action
        action_tuples = []
        for action in self._registered_actions:
            # Create a handler that delegates to the bridge's action handler
            handler = self._create_action_handler(action.name)
            self._action_handlers[action.name] = handler
            action_tuples.append((action, handler))

        # Register all actions
        await self.register_neuro_actions(action_tuples)
        logger.info(f"Successfully registered {len(action_tuples)} actions")

    async def unregister_all_actions(self) -> None:
        """Unregister all currently registered actions from Neuro."""
        if not self._registered_actions:
            logger.info("No actions to unregister")
            return

        if self.not_connected:
            logger.warning("Cannot unregister actions: not connected to Neuro server")
            return

        action_names = [action.name for action in self._registered_actions]
        logger.info(f"Unregistering {len(action_names)} actions from Neuro: {action_names}")

        try:
            await self.unregister_actions(action_names)
            logger.info("Successfully unregistered all actions")

            # Clear local tracking
            self._registered_actions = []
            self._action_handlers = {}
        except Exception as e:
            logger.error(f"Failed to unregister actions: {e}", exc_info=True)
            raise

    def _create_action_handler(
        self, action_name: str
    ) -> Callable[[NeuroAction], Awaitable[tuple[bool, str | None]]]:
        """Create an action handler for a specific action.

        Args:
            action_name: Name of the action

        Returns:
            Async handler function
        """

        async def handler(neuro_action: NeuroAction) -> tuple[bool, str | None]:
            """Handle action execution."""
            logger.info(f"Executing action: {action_name}")
            try:
                success, message = await self._action_handler(neuro_action)
                logger.info(f"Action {action_name} completed: success={success}")
                return success, message
            except Exception as e:
                error_msg = f"Action execution failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return False, error_msg

        return handler

    def bind_handlers(self) -> None:
        """Bind event handlers for the component."""
        # No external event handlers needed
        pass

    async def send_context_update(self, message: str, silent: bool = True) -> None:
        """Send a context update to Neuro.

        Args:
            message: Context message
            silent: Whether to send silently (not shown to user)
        """
        if self.not_connected:
            logger.warning("Cannot send context: not connected to Neuro server")
            return

        try:
            await self.send_context(message, silent)
            logger.debug(f"Sent context update: {message[:50]}...")
        except Exception as e:
            logger.error(f"Failed to send context: {e}")
