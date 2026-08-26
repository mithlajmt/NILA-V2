"""
NILA-V2 Tool Registry
Modular registry for defining AI function-calling tools.
Supports schema export for Google Gemini Live (google-genai SDK) and OpenAI / OpenRouter formats.
"""

import asyncio
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central Manager for NILA-V2 Agentic Tools.
    Manages function registration, schema conversion, and safe execution dispatch.
    """

    _registry: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        func: Optional[Callable] = None,
    ):
        """
        Register a tool function with specified metadata schema.
        """
        def decorator(f: Callable):
            cls._registry[name] = {
                "name": name,
                "description": description,
                "parameters": parameters or {"type": "OBJECT", "properties": {}},
                "func": f,
            }
            logger.info(f"🛠️ Registered agentic tool: '{name}' - {description}")
            return f

        if func is not None:
            return decorator(func)
        return decorator

    @classmethod
    def get_registered_tools(cls) -> Dict[str, Dict[str, Any]]:
        """Return raw registry dictionary"""
        return cls._registry

    @classmethod
    def get_gemini_tools(cls) -> List[Any]:
        """
        Convert registered tool schemas into google.genai.types.Tool objects.
        Compatible with Google Gemini Live WebSockets API (LiveConnectConfig).
        """
        try:
            from google.genai import types
        except ImportError:
            logger.warning("⚠️ 'google-genai' SDK not installed; skipping Gemini tool conversion.")
            return []

        declarations = []
        for name, tool_info in cls._registry.items():
            param_schema = tool_info["parameters"]
            
            # Build Gemini Schema parameters object
            properties = {}
            required = param_schema.get("required", [])

            for prop_name, prop_data in param_schema.get("properties", {}).items():
                p_type = prop_data.get("type", "STRING").upper()
                gemini_type = getattr(types.Type, p_type, types.Type.STRING)
                properties[prop_name] = types.Schema(
                    type=gemini_type,
                    description=prop_data.get("description", ""),
                )

            parameters_schema = types.Schema(
                type=types.Type.OBJECT,
                properties=properties,
                required=required if required else None,
            )

            declaration = types.FunctionDeclaration(
                name=name,
                description=tool_info["description"],
                parameters=parameters_schema,
            )
            declarations.append(declaration)

        if declarations:
            return [types.Tool(function_declarations=declarations)]
        return []

    @classmethod
    def get_openai_tools(cls) -> List[Dict[str, Any]]:
        """
        Convert registered tool schemas into standard OpenAI / OpenRouter tool objects.
        """
        tools = []
        for name, tool_info in cls._registry.items():
            param_schema = tool_info["parameters"]
            properties = {}
            for prop_name, prop_data in param_schema.get("properties", {}).items():
                properties[prop_name] = {
                    "type": prop_data.get("type", "string").lower(),
                    "description": prop_data.get("description", ""),
                }

            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool_info["description"],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": param_schema.get("required", []),
                    },
                },
            })
        return tools

    @classmethod
    async def execute_tool(cls, name: str, args: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a registered tool by name with arguments.
        Supports both async coroutines and sync functions with exception isolation.
        """
        if name not in cls._registry:
            error_msg = f"❌ Tool '{name}' is not registered in ToolRegistry."
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

        tool_info = cls._registry[name]
        func = tool_info["func"]
        kwargs = args or {}

        logger.info(f"⚡ [TOOL CALL] Executing '{name}' with args: {kwargs}")
        print("\n" + "=" * 60)
        print(f"🛠️ [EXECUTING AGENT TOOL]: {name}({kwargs})")
        print("=" * 60)

        try:
            if inspect.iscoroutinefunction(func):
                result = await func(**kwargs)
            else:
                result = await asyncio.to_thread(func, **kwargs)

            # Format result to string / JSON
            if isinstance(result, (dict, list)):
                result_str = json.dumps(result, ensure_ascii=False)
            else:
                result_str = str(result)

            logger.info(f"✅ [TOOL RESULT] '{name}': {result_str[:120]}")
            print(f"📋 Tool Result: {result_str[:150]}")
            print("=" * 60 + "\n")
            return result_str

        except Exception as e:
            error_msg = f"❌ Error executing tool '{name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})


def register_tool(name: str, description: str, parameters: Optional[Dict[str, Any]] = None):
    """Decorator helper for registering agentic tools"""
    return ToolRegistry.register(name=name, description=description, parameters=parameters)
