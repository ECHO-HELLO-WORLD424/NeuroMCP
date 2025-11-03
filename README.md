# NeuroMCP

<div align="center">
  <img src="./assets/NeuroMCPIcon.png" alt="Logo" width="256" height="256">
  <h3 align="center">Translation layer between Neuro-API and MCP (Model Context Protocol).</h3>
  <p>A MCP translation layer for Neuro-SDK, allow Neuro to use MCP tools</p>
</div>

## Overview

NeuroMCP bridges the gap between the Neuro AI system and MCP servers, allowing the Neuro AI to use MCP tools as if they were native Neuro actions. The bridge operates as a **client** that connects to a Neuro server and translates MCP tools into Neuro-compatible actions.

```
┌─────────────────────────────┐
│   Neuro AI Server           │  ← Neuro test server or real Neuro AI
│   (e.g., test_neuro_server) │
│   Port: 8000                │
└────────────┬────────────────┘
             │
             │ WebSocket (Neuro-API Protocol)
             │
┌────────────▼────────────────┐
│   NeuroMCP Bridge (CLIENT)  │  ← Connects TO Neuro server
│  ┌──────────────────────┐   │
│  │ Neuro Client         │   │  ← Registers actions
│  │ - Connects via WS    │   │
│  │ - Registers actions  │   │
│  │ - Handles execution  │   │
│  └──────────┬───────────┘   │
│             │               │
│  ┌──────────▼───────────┐   │
│  │ Translation Layer    │   │  ← Converts between protocols
│  │ - Schema converter   │   │
│  │ - Result mapper      │   │
│  │ - Name sanitization  │   │
│  └──────────┬───────────┘   │
│             │               │
│  ┌──────────▼───────────┐   │
│  │ MCP Client           │   │  ← Calls MCP tools
│  │ - Stream HTTP        │   │
│  │ - Tool discovery     │   │
│  │ - Tool execution     │   │
│  └──────────────────────┘   │
└─────────────┬───────────────┘
              │
              │ MCP Protocol (Stream HTTP)
              │
┌─────────────▼───────────────┐
│   MCP Server(s)             │
│  - File System              │
│  - Database                 │
│  - Web Search               │
│  - Custom Tools             │
└─────────────────────────────┘
```

## Features

- **MCP Tool → Neuro Action Translation**: Automatically converts MCP tools to Neuro-compatible actions
- **Schema Simplification**: Removes MCP schema features not supported by Neuro-API
- **Stream HTTP Transport**: Supports Stream HTTP for MCP communication (SSE deprecated)
- **Client Mode**: Connects to Neuro server as a client (no port conflicts)
- **Manual Control**: User-driven registration/unregistration of actions
- **Real-time Status**: Check connection status and registered actions on-demand
- **Proxy Bypass**: Automatically bypasses system proxies for localhost connections
- **Logging and Monitoring**: Comprehensive logging for debugging

## Installation
```bash
cd NeuroMCP
uv pip install -e .
```

## Usage

### Basic Usage

**Important:** Start services in this order:

1. **Start a Neuro server** (test server or real Neuro AI):

```bash
# Option A: Use the included test server
cd NeuroMCP/examples
python test_neuro_server.py

# Option B: Use the Neuro-API console server
cd Neuro-API
python -m neuro_api.server
```

2. **Start an MCP server** (e.g., mock server for testing):

```bash
cd NeuroMCP/examples
python mock_mcp_server.py
```

3. **Run the NeuroMCP bridge** (connects to both servers):

```bash
cd NeuroMCP
neuromcp --verbose
```

The bridge will:
- Connect to the MCP server and discover tools
- Convert MCP tools to Neuro actions
- Connect to the Neuro server as a client
- Register the actions with Neuro (initial sync)
- Provide manual control interface for managing actions
- Execute MCP tools when Neuro requests actions

### Manual Control Commands

Once the bridge is running, you can use these commands:

- **`r`** - Register/sync MCP tools as Neuro actions
- **`u`** - Unregister all actions from Neuro
- **`s`** - Show connection status and registered actions
- **`q`** - Quit the bridge

**Example workflow:**
1. Start the bridge (automatically registers tools on startup)
2. If MCP server disconnects, press `u` to unregister actions
3. When MCP server is back online, press `r` to re-register tools
4. Press `s` anytime to check connection status
5. Press `q` to cleanly shut down the bridge

### Command Line Options

```bash
neuromcp --help
```

Options:
- `--mcp-url`: URL of the MCP server MCP endpoint (default: `http://127.0.0.1:3000/mcp`)
- `--neuro-url`: WebSocket URL of the Neuro server (default: `ws://localhost:8000`)
- `--game-name`: Name of the game/application (default: `NeuroMCP`)
- `--debug`: Enable debug logging
- `--verbose`: Enable verbose logging

### Programmatic Usage

```python
import trio
from neuro_mcp import NeuroMCPBridge

async def main():
    bridge = NeuroMCPBridge(
        neuro_websocket_url="ws://localhost:8000",
        game_name="NeuroMCP",
        mcp_server_url="http://localhost:3000/mcp",
    )
    await bridge.run()

trio.run(main)
```

## Testing

### Quick Test (3 Terminals Required)

#### Terminal 1: Neuro Test Server
```bash
cd NeuroMCP/examples
python test_neuro_server.py
```

Expected output:
```
[INFO] Starting websocket server on ws://localhost:8000.
```

#### Terminal 2: Mock MCP Server
```bash
cd NeuroMCP/examples
python mock_mcp_server.py
```

Expected output:
```terminaloutput
============================================================
Mock MCP Server
============================================================

Serving MCP tools via Streamable HTTP at:
  http://localhost:3000/mcp

Available tools:
  - echo: Echo back a message
  - add: Add two numbers
  - greet: Generate a greeting
  - current_time: Get current time
```

#### Terminal 3: NeuroMCP Bridge
```bash
cd NeuroMCP
python -m neuro_mcp --verbose
```

Expected output:
```terminaloutput
============================================================
NeuroMCP Bridge (Client Mode)
============================================================
MCP Server: http://localhost:3000/mcp
Neuro Server: ws://localhost:8000
Game Name: NeuroMCP
============================================================
...
2025-11-03 12:50:50,202 - neuro_mcp.translation - INFO - Converted MCP tool 'echo' to Neuro action 'echo'
2025-11-03 12:50:50,202 - neuro_mcp.bridge - INFO - Mapped tool: echo -> echo
2025-11-03 12:50:50,202 - neuro_mcp.translation - INFO - Converted MCP tool 'add' to Neuro action 'add'
2025-11-03 12:50:50,202 - neuro_mcp.bridge - INFO - Mapped tool: add -> add
2025-11-03 12:50:50,202 - neuro_mcp.translation - INFO - Converted MCP tool 'greet' to Neuro action 'greet'
2025-11-03 12:50:50,202 - neuro_mcp.bridge - INFO - Mapped tool: greet -> greet
2025-11-03 12:50:50,202 - neuro_mcp.translation - INFO - Converted MCP tool 'current_time' to Neuro action 'current_time'
2025-11-03 12:50:50,202 - neuro_mcp.bridge - INFO - Mapped tool: current_time -> current_time
2025-11-03 12:50:50,202 - neuro_mcp.neuro_client - INFO - Set 4 available actions
2025-11-03 12:50:50,202 - neuro_mcp.bridge - INFO - Synchronized 4 tools as Neuro actions
2025-11-03 12:50:50,202 - neuro_mcp.bridge - INFO - Bridge is running with manual control enabled.

============================================================
MANUAL CONTROL MODE
============================================================
Available commands:
  r - Register/sync MCP tools as Neuro actions
  u - Unregister all actions from Neuro
  s - Show connection status
  q - Quit the bridge
============================================================

Enter command (r/u/s/q):
```

You can now use the manual control commands to manage action registration.

### Interacting with Tools

In **Terminal 1** (Neuro test server), you should now see:
```terminaloutput
============================================================
CLIENT CONNECTED: ::1:55904
============================================================

Waiting for client to register actions...
(Commands will be available after action registration)


> list

============================================================
Game: NeuroMCP
============================================================
Available actions:
  • echo
    Echo back the provided message
    Schema: {'type': 'object', 'properties': {'message': {'type': 'string'}}, 'required': ['message']}
  • add
    Add two numbers together
    Schema: {'type': 'object', 'properties': {'a': {'type': 'number'}, 'b': {'type': 'number'}}, 'required': ['a', 'b']}
  • greet
    Generate a greeting message
    Schema: {'type': 'object', 'properties': {'name': {'type': 'string'}, 'style': {'type': 'string', 'enum': ['formal', 'casual', 'enthusiastic']}}, 'required': ['name']}
  • current_time
    Get the current time
    Schema: {'type': 'object', 'properties': {}}
============================================================
```

Try executing the tools:

```terminaloutput
> send greet {"name": "Neuro", "style": "casual"} 

Sending action 'greet'...

============================================================
[CONTEXT from NeuroMCP]
Message: Hey Neuro! What's up?
Reply if not busy: False
============================================================

✓ Action completed successfully
  Result: Hey Neuro! What's up?
```

### With Real MCP Servers

To use with production MCP servers:

1. Install and start an MCP server (Tested: playwright-mcp)
2. Run the bridge:
   ```bash
   neuromcp --mcp-url http://your-mcp-server:port/mcp
   ```
3. Start the test server and send commands

## Architecture

### Components

1. **MCP Client** (`mcp_client.py`): Connects to MCP servers via Stream HTTP transport
2. **Translation Layer** (`translation.py`): Converts between MCP and Neuro formats
3. **Neuro Client** (`neuro_client.py`): Implements the Neuro-API client protocol
4. **Bridge** (`bridge.py`): Orchestrates the entire translation process

### Client Mode

The bridge operates as a **Neuro client**. This means:
- It **connects TO** a Neuro server (like the test server or real Neuro AI)
- It **registers** MCP tools as Neuro actions
- It **handles** action execution requests from Neuro

### Translation Details

#### Tool to Action Mapping

- **Name Sanitization**: MCP tool names are converted to `[a-z0-9_-]` format
- **Schema Simplification**: Removes forbidden JSON Schema keywords
- **Description Preservation**: Tool descriptions are passed through to Neuro

#### Limitations

The following MCP/JSON Schema features are **not supported** (removed during translation):

- Schema references (`$ref`, `$defs`)
- Composition keywords (`allOf`, `anyOf`, `oneOf`)
- Advanced validation (`additionalProperties`, `patternProperties`)
- Meta keywords (`$schema`, `$id`, `description`, `title`)

## Troubleshooting

### Bridge Connects Then Immediately Disconnects

**Symptom:** WebSocket connection closes right after connecting

**Solutions:**
- Make sure Neuro server and MCP server are running BEFORE starting bridge
- Check Neuro server logs for errors

### MCP Server Disconnected

**Symptom:** MCP server stops or disconnects while bridge is running

**Solutions:**
1. Press `s` to check connection status
2. Press `u` to unregister all actions from Neuro (prevents failed action calls)
3. Restart the MCP server
4. Press `r` to re-register actions once MCP is back online

### Actions Not Appearing in Neuro

**Symptom:** Actions don't show up after starting the bridge

**Solutions:**
- **Wait a few seconds for sync to complete**
- Press `s` to verify connection status
- Press `r` to manually trigger registration
- Check bridge logs for errors during tool conversion

## Development

### Project Structure

```terminaloutput
NeuroMCP/
├── src/neuro_mcp/
│   ├── __init__.py          # Package exports
│   ├── __main__.py          # CLI entry point
│   ├── bridge.py            # Main orchestrator 
│   ├── mcp_client.py        # MCP client 
│   ├── neuro_client.py      # Neuro-API client 
│   └── translation.py       # Translation layer 
├── examples/
│   ├── basic_usage.py       # Example script
│   ├── mock_mcp_server.py   # Test MCP server with 4 tools
│   └── test_neuro_server.py # Test Neuro server
├── pyproject.toml           # Project configuration
└── README.md
```

## License

MIT

## Credits

- Original Neuro-SDK: https://github.com/VedalAI/neuro-game-sdk
- Python implementation of Neuro-SDK: https://github.com/CoolCat467/Neuro-API
- MCP: https://modelcontextprotocol.io/
