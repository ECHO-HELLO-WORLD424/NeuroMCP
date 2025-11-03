"""Test script demonstrating the NeuroMCP bridge.

This script provides instructions and utilities for testing the bridge.
"""

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_step(step_num, description):
    """Print a formatted step."""
    print(f"\n[Step {step_num}] {description}")
    print("-" * 70)


def main():
    """Main test script."""
    print_section("NeuroMCP Bridge Testing Guide")

    print("This guide will walk you through testing the NeuroMCP bridge.")
    print("\nYou will need 3 terminal windows:")
    print("  1. Terminal for Mock MCP Server")
    print("  2. Terminal for NeuroMCP Bridge")
    print("  3. Terminal for Neuro-API Test Client")

    print_section("Setup Instructions")

    print_step(1, "Start the Mock MCP Server")
    print("In Terminal 1, run:")
    print("  cd NeuroMCP/examples")
    print("  python mock_mcp_server.py")
    print("\nThis will start an MCP server at http://localhost:3000/sse")
    print("with 4 test tools: echo, add, greet, current_time")

    input("\nPress Enter when the MCP server is running...")

    print_step(2, "Start the NeuroMCP Bridge")
    print("In Terminal 2, run:")
    print("  cd NeuroMCP")
    print("  python -m neuro_mcp --verbose")
    print("\nOr with debug logging:")
    print("  python -m neuro_mcp --debug")
    print("\nThis will:")
    print("  - Connect to the MCP server at localhost:3000")
    print("  - Discover the 4 MCP tools")
    print("  - Convert them to Neuro actions")
    print("  - Start a Neuro-API server at localhost:8000")

    input("\nPress Enter when the bridge is running...")

    print_step(3, "Connect with Neuro-API Test Client")
    print("In Terminal 3, run:")
    print("  cd Neuro-API")
    print("  python -m neuro_api.server ws://localhost:8000")
    print("\nThis starts an interactive console where you can:")
    print("  - See the registered actions (converted from MCP tools)")
    print("  - Choose actions to execute")
    print("  - See the results")

    print_section("Expected Behavior")

    print("1. MCP Server Output:")
    print("   - Shows 'Serving MCP tools via SSE at http://localhost:3000/sse'")
    print("   - Lists available tools: echo, add, greet, current_time")

    print("\n2. Bridge Output:")
    print("   - Connects to MCP server")
    print("   - Shows 'Discovered 4 MCP tools'")
    print("   - Shows tool mappings (e.g., 'echo' -> 'echo')")
    print("   - Shows 'Synchronized 4 tools as Neuro actions'")
    print("   - Shows 'Starting Neuro-API server on localhost:8000'")

    print("\n3. Neuro Client Output:")
    print("   - Connects to bridge via WebSocket")
    print("   - After sending 'startup' command, shows available actions")
    print("   - You can select actions and provide parameters")
    print("   - Results from MCP tools are displayed")

    print_section("Example Interactions")

    print("When the Neuro console shows available actions, try:")
    print("\n1. Echo Tool:")
    print("   - Select 'echo' action")
    print("   - Provide message: 'Hello from Neuro!'")
    print("   - Expected result: 'Echo: Hello from Neuro!'")

    print("\n2. Add Tool:")
    print("   - Select 'add' action")
    print("   - Provide a: 42, b: 58")
    print("   - Expected result: 'Result: 100'")

    print("\n3. Greet Tool:")
    print("   - Select 'greet' action")
    print("   - Provide name: 'Alice', style: 'enthusiastic'")
    print("   - Expected result: 'Hello Alice!!! So great to see you!!! 🎉'")

    print("\n4. Current Time Tool:")
    print("   - Select 'current_time' action")
    print("   - No parameters needed")
    print("   - Expected result: Current timestamp")

    print_section("Troubleshooting")

    print("If the bridge fails to connect to MCP server:")
    print("  - Check that mock_mcp_server.py is running")
    print("  - Verify http://localhost:3000/sse is accessible")
    print("  - Check for error messages in bridge output")

    print("\nIf Neuro client can't connect:")
    print("  - Check that the bridge is running")
    print("  - Verify ws://localhost:8000 is the correct URL")
    print("  - Check firewall settings")

    print("\nIf actions don't execute:")
    print("  - Check bridge logs for error messages")
    print("  - Verify tool parameters match expected schema")
    print("  - Check MCP server logs for tool execution errors")

    print_section("Manual Testing Steps")

    print("If you prefer to run each component manually:")
    print("\n# Terminal 1: MCP Server")
    print("cd C:\\Dev\\PyCharmProjects\\NeuroMCP\\examples")
    print("python mock_mcp_server.py")

    print("\n# Terminal 2: Bridge")
    print("cd C:\\Dev\\PyCharmProjects\\NeuroMCP")
    print("python -m neuro_mcp --verbose --mcp-url http://localhost:3000/sse")

    print("\n# Terminal 3: Test Client")
    print("cd C:\\Dev\\PyCharmProjects\\Neuro-API")
    print("python -m neuro_api.server ws://localhost:8000")

    print_section("Success Criteria")

    print("The bridge is working correctly if:")
    print("  ✓ MCP server starts and lists 4 tools")
    print("  ✓ Bridge connects to MCP and discovers tools")
    print("  ✓ Bridge converts tools to Neuro actions")
    print("  ✓ Neuro client connects to bridge")
    print("  ✓ Neuro client can see and execute actions")
    print("  ✓ Action results are returned correctly")
    print("  ✓ Multiple actions can be executed in sequence")

    print_section("Next Steps")

    print("Once basic testing is complete, you can:")
    print("  1. Connect to a real MCP server (filesystem, database, etc.)")
    print("  2. Test with more complex tool schemas")
    print("  3. Test with multiple MCP servers simultaneously")
    print("  4. Integrate with a real Neuro AI instance")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
