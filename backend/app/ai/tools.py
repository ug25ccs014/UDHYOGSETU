"""Controlled tool definitions for the copilot (spec §11).

Rather than letting a free-running LLM emit arbitrary code / SQL, the copilot
interacts with a fixed set of well-defined, side-effect-scoped tools. The model
requests a tool by name + JSON arguments; the ``ToolCallingService`` validates
against the registry and executes only the known, allow-listed tools.

Each tool declares:
  * name        - unique identifier used by the model in its tool call
  * description - what it does, shown to the model for selection
  * parameters  - JSON Schema describing accepted arguments
  * handler     - async callable(db, args) -> dict result
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


class ToolCallingError(Exception):
    """Raised when a tool call is invalid, unknown, or its arguments are wrong."""


# A handler always receives (db, args) and returns a JSON-serializable dict.
ToolHandler = Callable[[Any, dict], Awaitable[dict]]


class Tool:
    """A single controlled tool the model may invoke."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: ToolHandler,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Holds and looks up the allow-listed tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolCallingError(f"Unknown tool: {name}")
        return tool

    def list(self) -> list[dict[str, Any]]:
        return [t.schema() for t in self._tools.values()]


class ToolCallingService:
    """Validates and executes tool calls from an LLM."""

    def __init__(self, registry: ToolRegistry, db=None):
        self.registry = registry
        self.db = db

    async def execute(self, tool_name: str, args: dict) -> dict:
        try:
            tool = self.registry.get(tool_name)
            validated = self._validate_args(tool, args or {})
            result = await tool.handler(self.db, validated)
            return {"tool": tool_name, "ok": True, "result": result}
        except ToolCallingError as exc:
            return {"tool": tool_name, "ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tool %s failed: %s", tool_name, exc)
            return {"tool": tool_name, "ok": False, "error": f"Tool execution failed: {exc}"}

    def _validate_args(self, tool: Tool, args: dict) -> dict:
        schema = tool.parameters or {}
        props = schema.get("properties", {})
        required = schema.get("required", [])
        missing = [r for r in required if r not in args]
        if missing:
            raise ToolCallingError(f"Missing required arguments for {tool.name}: {missing}")
        unknown = [k for k in args if k not in props]
        if unknown:
            raise ToolCallingError(f"Unknown arguments for {tool.name}: {unknown}")
        return args
