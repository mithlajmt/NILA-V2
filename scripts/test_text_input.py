#!/usr/bin/env python3
"""
Test script for manual text input (before Telegram integration)
Tests text input handler in isolation
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.operator.text_input_handler import TextInputHandler


async def test_text_handler():
    """Test text input handler"""
    print("🧪 Testing Text Input Handler...")
    print("=" * 60)
    
    # Create handler
    handler = TextInputHandler()
    
    # Test 1: Add text
    print("\n📝 Test 1: Adding text to queue...")
    success = await handler.add_text("Hello robot, this is a test message", source="test")
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    # Test 2: Get text
    print("\n📤 Test 2: Getting text from queue...")
    text = await handler.get_text(timeout=1.0)
    print(f"   Result: {text if text else '❌ None (timeout or empty)'}")
    
    # Test 3: Multiple messages
    print("\n📝 Test 3: Adding multiple messages...")
    messages = [
        "First message",
        "Second message",
        "Third message"
    ]
    for msg in messages:
        await handler.add_text(msg, source="test")
        print(f"   Added: {msg}")
    
    # Test 4: Get all messages
    print("\n📤 Test 4: Getting all messages...")
    for i in range(5):  # Try to get more than we added
        text = await handler.get_text(timeout=0.5)
        if text:
            print(f"   Got: {text}")
        else:
            print(f"   Queue empty after {i} messages")
            break
    
    # Test 5: Statistics
    print("\n📊 Test 5: Statistics...")
    stats = handler.get_stats()
    print(f"   Total received: {stats['total_received']}")
    print(f"   Total processed: {stats['total_processed']}")
    print(f"   Queue size: {stats['queue_size']}")
    
    # Test 6: Empty text handling
    print("\n📝 Test 6: Empty text handling...")
    result = await handler.add_text("", source="test")
    print(f"   Result: {'✅ Rejected (expected)' if not result else '❌ Accepted (unexpected)'}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("\n💡 Next: Test integration with RobotController")


if __name__ == "__main__":
    asyncio.run(test_text_handler())
