"""CLI entry point for NeuroMCP bridge."""

import sys
import argparse
import logging

import trio

from neuro_mcp.bridge import main


def cli() -> None:
    """Command-line interface for NeuroMCP."""
    parser = argparse.ArgumentParser(
        description="NeuroMCP: Translation layer between Neuro-API and MCP protocol",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--mcp-url",
        default="http://127.0.0.1:3000/mcp",
        help="URL of the MCP server endpoint",
    )

    parser.add_argument(
        "--neuro-url",
        default="ws://localhost:8000",
        help="WebSocket URL of the Neuro server",
    )

    parser.add_argument(
        "--game-name",
        default="NeuroMCP",
        help="Name of the game/application",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else (logging.INFO if args.verbose else logging.WARNING)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Always show INFO for the main bridge
    logging.getLogger("neuro_mcp").setLevel(logging.INFO)

    print("=" * 60)
    print("NeuroMCP Bridge (Client Mode)")
    print("=" * 60)
    print(f"MCP Server: {args.mcp_url}")
    print(f"Neuro Server: {args.neuro_url}")
    print(f"Game Name: {args.game_name}")
    print("=" * 60)
    print()

    try:
        trio.run(main, args.mcp_url, args.neuro_url, args.game_name)
    except KeyboardInterrupt:
        print("\nBridge stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
