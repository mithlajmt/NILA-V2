#!/usr/bin/env python3
"""
Complete Phase 1 Testing Script
Tests all components step by step
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_test(name):
    print(f"\n🧪 Test: {name}")

def print_success(msg):
    print(f"   ✅ {msg}")

def print_error(msg):
    print(f"   ❌ {msg}")

def print_info(msg):
    print(f"   ℹ️  {msg}")

async def test_1_text_handler():
    """Test 1: Text Input Handler"""
    print_test("Text Input Handler (Isolated)")
    
    try:
        from src.services.operator.text_input_handler import TextInputHandler
        
        handler = TextInputHandler()
        print_success("Handler created")
        
        # Test add
        success = await handler.add_text("Test message", source="test")
        if success:
            print_success("Text added to queue")
        else:
            print_error("Failed to add text")
            return False
        
        # Test get
        text = await handler.get_text(timeout=1.0)
        if text == "Test message":
            print_success("Text retrieved from queue")
        else:
            print_error(f"Expected 'Test message', got: {text}")
            return False
        
        # Test stats
        stats = handler.get_stats()
        if stats['total_received'] > 0:
            print_success(f"Statistics working (received: {stats['total_received']})")
        else:
            print_error("Statistics not working")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_2_status_reporter():
    """Test 2: Status Reporter"""
    print_test("Status Reporter")
    
    try:
        from src.services.operator.status_reporter import StatusReporter
        
        reporter = StatusReporter(robot_controller=None)
        print_success("Reporter created")
        
        status = reporter.get_status()
        if status and len(status) > 0:
            print_success("Status generated")
            print_info(f"Status length: {len(status)} chars")
        else:
            print_error("Status is empty")
            return False
        
        short_status = reporter.get_short_status()
        if short_status:
            print_success("Short status generated")
        else:
            print_error("Short status failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_3_robot_controller_integration():
    """Test 3: Robot Controller Integration"""
    print_test("Robot Controller Integration")
    
    try:
        from src.core.robot_controller import RobotController
        from src.config.settings import Settings
        
        settings = Settings()
        print_success("Settings loaded")
        
        robot = RobotController(settings)
        print_success("Robot Controller created")
        
        # Check text handler exists
        if hasattr(robot, 'text_handler'):
            print_success("Text handler integrated")
        else:
            print_error("Text handler not found")
            return False
        
        # Check status reporter exists
        if hasattr(robot, 'status_reporter'):
            print_success("Status reporter integrated")
        else:
            print_error("Status reporter not found")
            return False
        
        # Test adding text
        success = await robot.text_handler.add_text("Integration test", source="test")
        if success:
            print_success("Text added via robot controller")
        else:
            print_error("Failed to add text via robot controller")
            return False
        
        # Check queue size
        queue_size = robot.text_handler.get_queue_size()
        if queue_size > 0:
            print_success(f"Queue has {queue_size} item(s)")
        else:
            print_error("Queue is empty after adding text")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_4_telegram_bot_import():
    """Test 4: Telegram Bot Import (if available)"""
    print_test("Telegram Bot Import")
    
    try:
        from src.services.operator.telegram_bot import TelegramBot
        print_success("Telegram bot module imported")
        
        # Check if python-telegram-bot is available
        try:
            import telegram
            print_success("python-telegram-bot library available")
            return True
        except ImportError:
            print_info("python-telegram-bot not installed (optional)")
            print_info("Install with: pip install python-telegram-bot>=20.0")
            return True  # Not a failure, just optional
            
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

async def test_5_settings():
    """Test 5: Settings Configuration"""
    print_test("Settings Configuration")
    
    try:
        from src.config.settings import Settings
        
        settings = Settings()
        print_success("Settings loaded")
        
        # Check Telegram settings exist
        if hasattr(settings, 'TELEGRAM_BOT_TOKEN'):
            print_success("TELEGRAM_BOT_TOKEN setting exists")
            token = settings.TELEGRAM_BOT_TOKEN
            if token and token != "your_token_here":
                print_success(f"Token configured (length: {len(token)})")
            else:
                print_info("Token not set (using placeholder)")
        else:
            print_error("TELEGRAM_BOT_TOKEN setting missing")
            return False
        
        if hasattr(settings, 'TELEGRAM_ENABLED'):
            print_success("TELEGRAM_ENABLED setting exists")
            enabled = settings.TELEGRAM_ENABLED
            print_info(f"Telegram enabled: {enabled}")
        else:
            print_error("TELEGRAM_ENABLED setting missing")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print_header("Phase 1 Complete Testing")
    print("\nThis script tests all Phase 1 components step by step.")
    print("It will verify that everything is integrated correctly.")
    
    results = []
    
    # Test 1: Text Handler
    result = await test_1_text_handler()
    results.append(("Text Handler", result))
    
    # Test 2: Status Reporter
    result = await test_2_status_reporter()
    results.append(("Status Reporter", result))
    
    # Test 3: Robot Controller Integration
    result = await test_3_robot_controller_integration()
    results.append(("Robot Controller Integration", result))
    
    # Test 4: Telegram Bot Import
    result = await test_4_telegram_bot_import()
    results.append(("Telegram Bot Import", result))
    
    # Test 5: Settings
    result = await test_5_settings()
    results.append(("Settings", result))
    
    # Summary
    print_header("Test Results Summary")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Phase 1 is ready.")
        print("\nNext steps:")
        print("  1. Set TELEGRAM_BOT_TOKEN in .env (if using Telegram)")
        print("  2. Install: pip install python-telegram-bot>=20.0")
        print("  3. Start robot: python main.py")
        print("  4. Test Telegram bot (if enabled)")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        print("   Fix issues before proceeding to Phase 2.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
