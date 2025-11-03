"""
Test Neuro Server for MCP translation layer development. Based on ConsoleInteractiveNeuroServer from Neuro-API.
"""

import logging
import traceback

import trio
from trio_websocket import WebSocketConnection

from neuro_api.server import TrioNeuroServerClient, AbstractTrioNeuroServer
from neuro_api.command import Action

logging.basicConfig(level=logging.INFO, format='[ %(levelname)s | PID=%(process)d | %(name)s ]: %(message)s')
logger = logging.getLogger(__name__)


class NeuroTestServer(AbstractTrioNeuroServer):
    """
    Console-based test server for development.

    This server allows you to manually test the integration
    by providing console input when Neuro would normally make AI decisions.
    """

    __slots__ = ("console_command_lock",)

    def __init__(self) -> None:
        super().__init__()
        self.console_command_lock = trio.Lock()
        logger.info("Neuro Test Server initialized")

    def add_context(
        self,
        game_title: str | None,
        message: str,
        reply_if_not_busy: bool,
    ) -> None:
        """
        Display context information from the client.
        """
        print(f"\n{'='*60}")
        print(f"[CONTEXT from {game_title}]")
        print(f"Message: {message}")
        print(f"Reply if not busy: {reply_if_not_busy}")
        print(f"{'='*60}\n")

    @staticmethod
    def show_help() -> None:
        """Display available console commands."""
        print("\n" + "="*60)
        print("AVAILABLE COMMANDS:")
        print("="*60)
        print("  send <action_name> [json_data]  - Send action to client")
        print("  list                            - Show available actions")
        print("  help                            - Show this help")
        print("  <enter>                         - Wait for more messages")
        print("="*60 + "\n")

    @staticmethod
    def list_client_actions(client: TrioNeuroServerClient) -> None:
        """Display all registered actions for a client."""
        print(f"\n{'='*60}")
        print(f"Game: {client.game_title}")
        print(f"{'='*60}")
        if client.actions:
            print("Available actions:")
            for action_name, action in client.actions.items():
                print(f"  • {action_name}")
                print(f"    {action.description}")
                if action.schema:
                    print(f"    Schema: {action.schema}")
        else:
            print("  No actions registered yet")
        print(f"{'='*60}\n")

    @staticmethod
    def ask_action_json(action: Action) -> str | None:
        """Prompt for optional JSON data for an action."""
        json_blob: str | None = None
        if action.schema is not None:
            print(f"\nAction: {action.name}")
            print(f"Description: {action.description}")
            print(f"Schema: {action.schema}\n")
            response = input("Provide JSON data? (y/N) > ").strip().lower()
            if response == 'y':
                json_blob = input("JSON data > ").strip()
        return json_blob

    async def console_input_command(
        self,
        client: TrioNeuroServerClient,
    ) -> None:
        """Handle console input for sending commands to the client."""
        async with self.console_command_lock:
            while True:
                try:
                    await trio.sleep(0.1)
                    command = input("\n> ").strip()

                    if not command:
                        break

                    parts = command.split(maxsplit=1)
                    if not parts:
                        continue

                    cmd = parts[0].lower()

                    if cmd == "help":
                        self.show_help()
                    elif cmd == "list":
                        self.list_client_actions(client)
                    elif cmd == "send" and len(parts) >= 1:
                        # Parse: send <action_name> [json_data]
                        action_parts = parts[1].split(maxsplit=1) if len(parts) > 1 else []
                        if not action_parts:
                            print("ERROR: Please specify an action name")
                            print("Usage: send <action_name> [json_data]")
                            continue

                        action_name = action_parts[0]
                        json_data = action_parts[1] if len(action_parts) > 1 else None

                        action = client.get_action(action_name)
                        if action is None:
                            print(f"ERROR: Action '{action_name}' not available")
                            print("Use 'list' to see available actions")
                            continue

                        # If no JSON provided and action has schema, ask
                        if json_data is None and action.schema:
                            json_data = self.ask_action_json(action)

                        print(f"\nSending action '{action_name}'...")
                        success, message = await client.submit_action(
                            action_name,
                            json_data,
                        )

                        if success:
                            print(f"✓ Action completed successfully")
                            if message:
                                print(f"  Result: {message}")
                        else:
                            print(f"✗ Action failed")
                            if message:
                                print(f"  Error: {message}")
                    else:
                        print("Invalid command. Type 'help' for available commands.")
                except EOFError:
                    print("\nEOF received, exiting console input")
                    break
                except KeyboardInterrupt:
                    print("\nInterrupted, exiting console input")
                    break
                except Exception as exc:
                    logger.error(f"Error processing command: {exc}")
                    traceback.print_exc()

    def start_console_input_command(
        self,
        client: TrioNeuroServerClient,
    ) -> None:
        """Start console input if not already active."""
        if self.console_command_lock.locked():
            return
        self.handler_nursery.start_soon(self.console_input_command, client)

    async def handle_client_connection(
        self,
        websocket: WebSocketConnection,
    ) -> None:
        """Handle a client connection with console interaction."""
        remote = websocket.remote
        if not isinstance(remote, str):
            remote = f"{remote.address}:{remote.port}"

        print(f"\n{'='*60}")
        print(f"CLIENT CONNECTED: {remote}")
        print(f"{'='*60}\n")

        try:
            async with websocket:
                client = TrioNeuroServerClient(websocket, self)
                self.clients[remote] = client

                print("Waiting for client to register actions...")
                print("(Commands will be available after action registration)\n")

                while True:
                    # Wait for messages, timeout after 8 seconds to allow console input
                    with trio.move_on_after(8):
                        await client.read_message()
                        continue

                    # Timeout - offer console interaction
                    self.start_console_input_command(client)

        except Exception:
            logger.error("Error in client connection:")
            traceback.print_exc()
            raise
        finally:
            print(f"\n{'='*60}")
            print(f"CLIENT DISCONNECTED: {remote}")
            print(f"{'='*60}\n")

    async def choose_force_action(
        self,
        game_title: str | None,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        actions: tuple[Action, ...],
    ) -> tuple[str, str | None]:
        """
        Prompt console operator to choose an action.

        This is called when the client uses send_force_action.
        """
        print(f"\n{'='*60}")
        print(f"[FORCE ACTION REQUEST from {game_title}]")
        print(f"{'='*60}")
        if state:
            print(f"State:\n{state}\n")
        print(f"Query: {query}")
        print(f"Ephemeral: {ephemeral_context}")
        print(f"\nAvailable actions:")

        action_str = "\n".join(
            f"  {idx + 1}. {action.name}\n     {action.description}"
            for idx, action in enumerate(actions)
        )
        print(action_str)
        print(f"{'='*60}\n")

        # Get user selection
        while True:
            try:
                choice = input("Select action (number) > ").strip()
                action_idx = int(choice) - 1
                if 0 <= action_idx < len(actions):
                    action = actions[action_idx]
                    break
                else:
                    print(f"Invalid choice. Please enter 1-{len(actions)}")
            except ValueError:
                print("Invalid input. Please enter a number")
            except KeyboardInterrupt:
                print("\nDefaulting to first action")
                action = actions[0]
                break

        # Handle checkpoint for other tasks
        await trio.lowlevel.checkpoint()

        # Get JSON data if needed
        json_blob = self.ask_action_json(action)

        print(f"\n✓ Selected: {action.name}")
        return action.name, json_blob


async def run_test_server(host: str = "localhost", port: int = 8000) -> None:
    """Run the test server."""
    server = NeuroTestServer()

    print("="*60)
    print("MOCK NEURO SERVER")
    print("="*60)
    print(f"Starting server on ws://{host}:{port}")
    print("\nThis server simulates the Neuro AI system for testing.")
    print("You can manually send commands to test your integration.")
    print("\nWaiting for client connections...")
    print("="*60 + "\n")

    try:
        await server.run(host, port)
    except Exception as e:
        logger.error(f"Server error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        trio.run(run_test_server)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as error:
        logger.error(f"Server error: {error}")
        traceback.print_exc()
