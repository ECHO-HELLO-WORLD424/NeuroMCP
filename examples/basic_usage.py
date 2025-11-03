"""Basic usage example for NeuroMCP bridge."""

import logging
import trio

from neuro_mcp.bridge import NeuroMCPBridge


async def run_basic_bridge():
    """Run a basic bridge example."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create the bridge
    # This assumes:
    # 1. An MCP server is running at http://localhost:3000/sse
    # 2. A Neuro test server is running at ws://localhost:8000
    bridge = NeuroMCPBridge(
        neuro_websocket_url="ws://localhost:8000",
        game_name="NeuroMCP",
        mcp_server_url="http://localhost:3000/sse",
        mcp_transport="sse",
    )

    print("\n" + "=" * 60)
    print("NeuroMCP Bridge - Basic Example (Client Mode)")
    print("=" * 60)
    print("\nStarting bridge...")
    print("\nTo test this bridge:")
    print("1. Start the MCP server:")
    print("   cd examples && python mock_mcp_server.py")
    print("2. Start the Neuro test server:")
    print("   cd ../Neuro-API && python -m neuro_api.server")
    print("3. Run this bridge (it will connect to both)")
    print("\n" + "=" * 60 + "\n")

    try:
        await bridge.run()
    except KeyboardInterrupt:
        print("\nBridge stopped")


if __name__ == "__main__":
    trio.run(run_basic_bridge)
