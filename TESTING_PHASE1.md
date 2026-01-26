# 🧪 Phase 1 Testing Guide

## Step-by-Step Testing

### Step 1: Test Text Input Handler (Isolated)

**Purpose**: Verify text queue works independently

```bash
cd /home/mithlajmt/finalrobot/NILA-V2
python scripts/test_text_input.py
```

**Expected Output**:
```
🧪 Testing Text Input Handler...
============================================================

📝 Test 1: Adding text to queue...
   Result: ✅ Success

📤 Test 2: Getting text from queue...
   Result: Hello robot, this is a test message

📝 Test 3: Adding multiple messages...
   Added: First message
   Added: Second message
   Added: Third message

📤 Test 4: Getting all messages...
   Got: First message
   Got: Second message
   Got: Third message
   Queue empty after 3 messages

📊 Test 5: Statistics...
   Total received: 4
   Total processed: 4
   Queue size: 0

📝 Test 6: Empty text handling...
   Result: ✅ Rejected (expected)

============================================================
✅ All tests completed!
```

**If this fails**: Check Python path and imports

---

### Step 2: Test Manual Text Input Integration

**Purpose**: Verify text input works with RobotController

#### Option A: Quick Test (Python REPL)

```bash
python
```

```python
import asyncio
from src.core.robot_controller import RobotController
from src.config.settings import Settings

# Create robot
settings = Settings()
robot = RobotController(settings)

# Test adding text manually
async def test():
    # Add text to queue
    await robot.text_handler.add_text("Hello robot, this is a test", source="manual")
    print("✅ Text added to queue")
    print(f"Queue size: {robot.text_handler.get_queue_size()}")
    
    # Get stats
    stats = robot.text_handler.get_stats()
    print(f"Stats: {stats}")

asyncio.run(test())
```

**Expected**: Text added successfully, queue size = 1

#### Option B: Test Script

Create `scripts/test_manual_text.py`:

```python
#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.robot_controller import RobotController
from src.config.settings import Settings

async def test():
    settings = Settings()
    robot = RobotController(settings)
    
    # Add text
    await robot.text_handler.add_text("Test message 1", source="manual")
    await robot.text_handler.add_text("Test message 2", source="manual")
    
    print(f"✅ Added 2 messages")
    print(f"Queue size: {robot.text_handler.get_queue_size()}")
    
    # Get one
    text = await robot.text_handler.get_text(timeout=1.0)
    print(f"Got: {text}")
    
    stats = robot.text_handler.get_stats()
    print(f"Stats: {stats}")

asyncio.run(test())
```

Run:
```bash
python scripts/test_manual_text.py
```

---

### Step 3: Test Robot with Text Input (Full Integration)

**Purpose**: Verify robot processes text input in main loop

**Important**: This requires the robot to be running. We'll test it step by step.

#### 3A: Start Robot (Don't interact yet)

```bash
python main.py
```

**Look for**:
- ✅ `Text Input Handler initialized`
- ✅ `Enhanced Robot Controller initialized`
- ✅ Robot greeting plays
- ✅ Robot enters listening mode

**If Telegram enabled**, also look for:
- ✅ `Telegram bot initialized`
- ✅ `Telegram bot started successfully`

#### 3B: Test Text Input While Robot Running

**Option 1: Using Python Script (Recommended)**

Create `scripts/send_text_to_robot.py`:

```python
#!/usr/bin/env python3
"""
Send text to running robot
Run this while robot is running in another terminal
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.operator.text_input_handler import TextInputHandler

async def send_text():
    # Note: This creates a NEW handler instance
    # In real usage, you'd access robot.text_handler
    # This is just for testing the concept
    
    handler = TextInputHandler()
    
    print("📝 Sending test messages to robot...")
    print("(Note: Robot must be running in another terminal)")
    
    messages = [
        "Hello robot, can you hear me?",
        "What is 2 plus 2?",
        "Tell me a joke"
    ]
    
    for msg in messages:
        success = await handler.add_text(msg, source="test")
        print(f"✅ Sent: {msg[:50]}...")
        await asyncio.sleep(2)  # Wait between messages
    
    print("\n✅ All messages sent!")
    print("Check robot terminal to see if messages were processed")

if __name__ == "__main__":
    asyncio.run(send_text())
```

**Problem**: This creates a NEW handler, not the robot's handler.

**Better**: We need to access the robot's handler. Let me create a better test.

---

### Step 4: Test Telegram Bot (If Enabled)

**Prerequisites**:
1. Bot token in `.env`
2. `TELEGRAM_ENABLED=true`
3. `python-telegram-bot` installed

#### 4A: Check Configuration

```bash
# Check .env has:
grep TELEGRAM .env
```

Should show:
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_ENABLED=true
```

#### 4B: Install Dependency

```bash
pip install python-telegram-bot>=20.0
```

#### 4C: Start Robot

```bash
python main.py
```

**Look for**:
```
📱 Telegram bot initialized (will start when robot starts)
✅ Telegram bot started successfully
```

#### 4D: Test in Telegram

1. Open Telegram
2. Search for your bot (the name you gave BotFather)
3. Send `/start`
   - **Expected**: Welcome message
4. Send any text message (e.g., "Hello robot")
   - **Expected**: 
     - Robot processes message
     - Bot replies with status
     - Robot speaks response
5. Send `/status`
   - **Expected**: Detailed robot status

---

### Step 5: Test Failure Scenarios

#### 5A: Invalid Telegram Token

1. Edit `.env`: Set wrong token
   ```env
   TELEGRAM_BOT_TOKEN=invalid_token_123
   TELEGRAM_ENABLED=true
   ```
2. Start robot: `python main.py`
3. **Expected**: 
   - Error logged about invalid token
   - Robot continues normally
   - Voice input still works

#### 5B: Disable Telegram

1. Edit `.env`:
   ```env
   TELEGRAM_ENABLED=false
   ```
2. Start robot: `python main.py`
3. **Expected**: 
   - No Telegram bot started
   - Robot works normally
   - Voice input works

#### 5C: Text Queue Failure

1. Start robot normally
2. Try to add text with invalid handler
3. **Expected**: Robot continues, voice still works

---

## Testing Checklist

- [ ] Step 1: Text handler isolated test passes
- [ ] Step 2: Manual text input works
- [ ] Step 3: Robot starts with text handler
- [ ] Step 4: Telegram bot starts (if enabled)
- [ ] Step 5: Telegram messages received
- [ ] Step 6: Robot processes text input
- [ ] Step 7: Status command works
- [ ] Step 8: Failure scenarios handled gracefully
- [ ] Step 9: Voice input still works
- [ ] Step 10: Text priority (text before voice)

---

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'src'"
**Solution**: Run from project root directory
```bash
cd /home/mithlajmt/finalrobot/NILA-V2
python scripts/test_text_input.py
```

### Issue: "Telegram bot not starting"
**Check**:
1. Token is correct
2. `TELEGRAM_ENABLED=true`
3. `python-telegram-bot` installed
4. Internet connection

**Solution**: Robot will continue without Telegram

### Issue: "Text not processing"
**Check**:
1. Robot is running
2. Text handler initialized (check logs)
3. Queue has items (check stats)

**Solution**: Verify text handler is integrated correctly

### Issue: "Voice stopped working"
**This shouldn't happen** - text input doesn't modify voice flow
**If it does**: Check logs, verify no errors in main loop

---

## Quick Test Commands

```bash
# Test 1: Text handler
python scripts/test_text_input.py

# Test 2: Check imports
python -c "from src.services.operator.text_input_handler import TextInputHandler; print('✅ Import OK')"

# Test 3: Check settings
python -c "from src.config.settings import Settings; s = Settings(); print(f'Telegram enabled: {s.TELEGRAM_ENABLED}')"

# Test 4: Start robot
python main.py
```

---

## What to Report

After testing, report:
1. ✅ Which tests passed
2. ❌ Which tests failed (if any)
3. 📝 Any errors or warnings
4. 💡 Suggestions or issues found

---

**Ready to test?** Start with Step 1 and work through each step!
