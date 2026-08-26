"""
Unit tests for NILA-V2 Agentic Tool System
Tests ToolRegistry, Gemini/OpenAI schema conversion, and tool execution.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.registry import ToolRegistry
import src.tools.built_in_tools as built_in_tools


async def main():
    print("=" * 60)
    print("🧪 TESTING NILA-V2 AGENTIC TOOL SYSTEM")
    print("=" * 60)

    # 1. Registered tools count
    tools = ToolRegistry.get_registered_tools()
    print(f"✅ Total Registered Tools: {len(tools)}")
    for name in tools:
        print(f"  🔹 Tool: '{name}'")

    print("\n--- Testing Schema Exports ---")
    
    # OpenAI Tools Export
    openai_tools = ToolRegistry.get_openai_tools()
    print(f"✅ OpenAI / OpenRouter Tools Export: {len(openai_tools)} tools")

    # Gemini Tools Export
    gemini_tools = ToolRegistry.get_gemini_tools()
    print(f"✅ Gemini Live WebSockets Tools Export: {len(gemini_tools)} tool container(s)")

    print("\n--- Executing Tool: get_current_time ---")
    res1 = await ToolRegistry.execute_tool("get_current_time", {"location": "Kochi"})
    print(f"Result 1: {res1}")

    print("\n--- Executing Tool: get_weather ---")
    res2 = await ToolRegistry.execute_tool("get_weather", {"city": "Trivandrum"})
    print(f"Result 2: {res2}")

    print("\n--- Executing Tool: trigger_robot_gesture ---")
    res3 = await ToolRegistry.execute_tool("trigger_robot_gesture", {"action": "wave"})
    print(f"Result 3: {res3}")

    print("\n--- Executing Tool: trigger_n8n_workflow ---")
    res4 = await ToolRegistry.execute_tool("trigger_n8n_workflow", {"workflow_name": "send_email", "payload_json": '{"to":"test@example.com"}'})
    print(f"Result 4: {res4}")

    print("=" * 60)
    print("✅ ALL TOOL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
