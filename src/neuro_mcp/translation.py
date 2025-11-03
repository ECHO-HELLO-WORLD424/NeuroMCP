"""Translation layer between MCP and Neuro-API protocols."""

import re
import logging
from typing import Any

from mcp.types import Tool
from neuro_api.command import Action

logger = logging.getLogger(__name__)

# Forbidden schema keywords in Neuro-API
FORBIDDEN_SCHEMA_KEYS = {
    "$anchor", "$comment", "$defs", "$dynamicAnchor", "$dynamicRef",
    "$id", "$ref", "$schema", "$vocabulary",
    "additionalProperties", "allOf", "anyOf",
    "contentEncoding", "contentMediaType", "contentSchema",
    "dependentRequired", "dependentSchemas", "deprecated",
    "description", "else", "if",
    "maxProperties", "minProperties", "multipleOf",
    "not", "oneOf", "patternProperties",
    "readOnly", "then", "title",
    "unevaluatedItems", "unevaluatedProperties", "writeOnly"
}


def sanitize_action_name(name: str) -> str:
    """Sanitize tool name to match Neuro action name constraints [a-z0-9_-].

    Args:
        name: Original tool name

    Returns:
        Sanitized name with only allowed characters
    """
    # Convert to lowercase
    sanitized = name.lower()

    # Replace invalid characters with underscore
    sanitized = re.sub(r"[^a-z0-9_-]", "_", sanitized)

    # Remove consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    if not sanitized:
        sanitized = "unnamed_action"

    logger.debug(f"Sanitized action name: {name} -> {sanitized}")
    return sanitized


def simplify_schema(schema: dict[str, Any] | None) -> dict[str, Any] | None:
    """Simplify MCP JSON Schema to be compatible with Neuro-API.

    Removes forbidden schema keywords and simplifies complex constructs.

    Args:
        schema: MCP tool input schema

    Returns:
        Simplified schema compatible with Neuro-API, or None if no schema
    """
    if not schema:
        return None

    def _simplify_recursive(obj: Any) -> Any:
        """Recursively remove forbidden keys from schema."""
        if not isinstance(obj, dict):
            return obj

        result = {}
        for key, value in obj.items():
            # Skip forbidden keys
            if key in FORBIDDEN_SCHEMA_KEYS:
                logger.debug(f"Removing forbidden schema key: {key}")
                continue

            # Handle special cases
            if key == "anyOf" or key == "oneOf" or key == "allOf":
                # Try to merge or pick first option
                logger.warning(f"Simplifying {key} by taking first option")
                if isinstance(value, list) and value:
                    # Take first option and merge it
                    first_option = _simplify_recursive(value[0])
                    if isinstance(first_option, dict):
                        result.update(first_option)
                continue

            # Recursively process nested structures
            if isinstance(value, dict):
                result[key] = _simplify_recursive(value)
            elif isinstance(value, list):
                result[key] = [_simplify_recursive(item) for item in value]
            else:
                result[key] = value

        return result

    simplified = _simplify_recursive(schema)

    # Ensure we have at least a basic structure
    if not isinstance(simplified, dict):
        simplified = {"type": "object"}

    logger.debug(f"Simplified schema from {len(str(schema))} to {len(str(simplified))} chars")
    return simplified


def mcp_tool_to_neuro_action(tool: Tool) -> Action:
    """Convert MCP Tool to Neuro Action.

    Args:
        tool: MCP Tool object

    Returns:
        Neuro Action object
    """
    # Sanitize name
    action_name = sanitize_action_name(tool.name)

    # Use description or generate one
    description = tool.description or f"Execute {tool.name}"

    # Simplify schema
    schema = simplify_schema(tool.inputSchema) if tool.inputSchema else None

    action = Action(
        name=action_name,
        description=description,
        schema=schema
    )

    logger.info(f"Converted MCP tool '{tool.name}' to Neuro action '{action_name}'")
    return action


def parse_action_data(data_str: str | None) -> dict[str, Any]:
    """Parse action data string from Neuro to dictionary for MCP.

    Args:
        data_str: JSON-stringified data from Neuro action

    Returns:
        Parsed dictionary of arguments
    """
    if not data_str or data_str == "null":
        return {}

    import json
    try:
        parsed = json.loads(data_str)
        if not isinstance(parsed, dict):
            logger.warning(f"Action data is not a dict: {type(parsed)}")
            return {}
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse action data: {e}")
        return {}


class ToolRegistry:
    """Registry to track mapping between Neuro actions and MCP tools."""

    def __init__(self):
        """Initialize the registry."""
        self._neuro_to_mcp: dict[str, str] = {}
        self._mcp_to_neuro: dict[str, str] = {}

    def register(self, neuro_action_name: str, mcp_tool_name: str) -> None:
        """Register a mapping between Neuro action and MCP tool.

        Args:
            neuro_action_name: Sanitized Neuro action name
            mcp_tool_name: Original MCP tool name
        """
        self._neuro_to_mcp[neuro_action_name] = mcp_tool_name
        self._mcp_to_neuro[mcp_tool_name] = neuro_action_name
        logger.debug(f"Registered mapping: {neuro_action_name} <-> {mcp_tool_name}")

    def get_mcp_tool_name(self, neuro_action_name: str) -> str | None:
        """Get MCP tool name from Neuro action name.

        Args:
            neuro_action_name: Neuro action name

        Returns:
            Original MCP tool name, or None if not found
        """
        return self._neuro_to_mcp.get(neuro_action_name)

    def get_neuro_action_name(self, mcp_tool_name: str) -> str | None:
        """Get Neuro action name from MCP tool name.

        Args:
            mcp_tool_name: MCP tool name

        Returns:
            Sanitized Neuro action name, or None if not found
        """
        return self._mcp_to_neuro.get(mcp_tool_name)

    def clear(self) -> None:
        """Clear all mappings."""
        self._neuro_to_mcp.clear()
        self._mcp_to_neuro.clear()
        logger.debug("Cleared tool registry")

    def get_all_neuro_actions(self) -> list[str]:
        """Get all registered Neuro action names.

        Returns:
            List of Neuro action names
        """
        return list(self._neuro_to_mcp.keys())
