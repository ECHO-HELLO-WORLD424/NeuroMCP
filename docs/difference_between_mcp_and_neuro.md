# Key Differences Between Neuro-API and MCP Protocol

## Fundamental Architecture

  | Aspect         | Neuro-API                             | MCP                              |
  |----------------|---------------------------------------|----------------------------------|
  | Transport      | WebSocket only                        | stdio, Stream HTTP               |
  | Message Format | Custom JSON commands                  | JSON-RPC 2.0                     |
  | Protocol Model | Game-centric, action-based            | LLM-centric, tool/resource-based |
  | Direction      | Bidirectional (server pushes actions) | Request-response                 |

## Core Concepts Mapping

  | Neuro-API                   | MCP Equivalent | Compatibility                                                  |
  |-----------------------------|----------------|----------------------------------------------------------------|
  | Action                      | Tool           | ✅ Similar - both are callable functions                        |
  | actions/force               | No equivalent  | ⚠️ Unique to Neuro - forces AI to choose from constrained set  |
  | context (silent/non-silent) | Resources      | ⚠️ Different - resources are pull-based, context is push-based |
  | startup                     | initialize     | ✅ Similar - session initialization                             |
  | shutdown                    | Not standard   | ⚠️ Game-specific concept                                       |
  | action/result               | Tool result    | ✅ Similar - success/failure responses                          |

## Critical Differences

### Invocation Model (Biggest Challenge)

  - Neuro: Game controls flow via actions/force - "Here are 5 legal moves, choose one NOW"
  - MCP: LLM decides when/if to call tools during reasoning
  - Impact: Need to bridge "forced choice" vs "autonomous decision"

### Schema Restrictions

  - Neuro: Forbidden keywords (no $ref, additionalProperties, allOf, etc.)
  - MCP: Full JSON Schema support
  - Impact: Schema translation/simplification required

### Timing Requirements

  - Neuro: action/result must be sent immediately or AI blocks
  - MCP: Async tool execution with flexible timing
  - Impact: Need synchronous adapter for async tools

### Context Management

  - Neuro: Push-based context with silent flag for AI-only info
  - MCP: Pull-based resources with subscription model
  - Impact: Need to map resource changes to context pushes

  1. ❌ Don't implement: Neuro → MCP direction (Neuro games calling MCP)
    - Not needed for enabling Neuro to use MCP tools
    - Overly complex
  2. ❌ Don't implement: Full schema translation
    - Just strip forbidden keywords
    - Warn if schema is too complex
  3. ❌ Don't implement: MCP prompts
    - Neuro doesn't have equivalent concept
    - Not critical for tool usage
  4. ❌ Don't implement: Neuro's actions/force in MCP
    - Unique to Neuro's game model
    - No MCP equivalent
  5. ❌ Don't implement: Shutdown/graceful commands
    - Game-specific Neuro features
    - Not relevant for MCP tools