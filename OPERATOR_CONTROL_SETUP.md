# 📱 Operator Control Setup Guide

## Overview

The Operator Control system allows remote control of the robot via Telegram, providing:
- **Text input** when microphone fails
- **Status monitoring** on demand
- **Operator override** (text priority over voice)

## Installation

### 1. Install Dependencies

```bash
pip install python-telegram-bot>=20.0
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 2. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to create a bot
4. Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 3. Configure Environment

Edit `.env` file:

```env
# Operator Control
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ENABLED=true
```

**Important:**
- Set `TELEGRAM_ENABLED=false` to disable Telegram (robot works normally)
- If token is invalid, robot will log error but continue working

## Testing

### Step 1: Test Text Input Handler (Isolated)

```bash
python scripts/test_text_input.py
```

This tests the text queue without Telegram.

### Step 2: Test Manual Text Input

Start the robot normally:
```bash
python main.py
```

In another terminal or Python script, you can manually add text:
```python
from src.core.robot_controller import RobotController
from src.config.settings import Settings

settings = Settings()
robot = RobotController(settings)

# Start robot (in async context)
# Then in another thread/script:
await robot.text_handler.add_text("Hello robot", source="manual")
```

### Step 3: Test Telegram Bot

1. Start the robot:
   ```bash
   python main.py
   ```

2. Look for log message:
   ```
   ✅ Telegram bot started successfully
   ```

3. Open Telegram and find your bot (search for the bot name you created)

4. Send `/start` - should receive welcome message

5. Send any text message - robot should process it and reply with status

6. Send `/status` - should receive detailed robot status

## Usage

### Telegram Commands

- `/start` - Get welcome message and instructions
- `/status` - Get detailed robot status
- Any other text - Sends to robot for processing (same as voice input)

### Text Priority

**TEXT FIRST** - Text input has priority over voice:
- If text is in queue, robot processes it immediately
- Voice listening only happens when text queue is empty
- This allows operator override

### Status Updates

Status is sent automatically when you send a message to the bot.

Status includes:
- Robot running status
- Message count
- Success/failure rates
- AI status
- Uptime
- Text input statistics

## Safety Features

### ✅ Isolated Design
- Telegram bot runs in separate async task
- If Telegram fails, robot continues normally
- No shared state that can break robot

### ✅ Error Handling
- All Telegram operations wrapped in try-except
- Invalid token → logs error, robot continues
- Network failure → logs error, robot continues
- Bot crash → logs error, robot continues

### ✅ Graceful Degradation
- If Telegram disabled → robot works normally
- If Telegram fails → robot works normally
- Text queue is optional → robot works without it

## Troubleshooting

### Bot Not Starting

**Check:**
1. Token is correct in `.env`
2. `TELEGRAM_ENABLED=true` in `.env`
3. `python-telegram-bot` is installed
4. Check logs for error messages

**Solution:**
- Robot will continue without Telegram
- Check token with BotFather
- Verify internet connection

### Bot Not Responding

**Check:**
1. Bot is running (check logs)
2. You're messaging the correct bot
3. Bot is not blocked

**Solution:**
- Send `/start` command
- Check robot logs for errors
- Restart robot if needed

### Text Not Processing

**Check:**
1. Text queue is working (test with manual input)
2. Robot is running
3. Check logs for errors

**Solution:**
- Test manual text input first
- Check if voice input still works
- Verify robot is in conversation loop

## Architecture

```
Telegram Message
    ↓
TelegramBot (isolated)
    ↓
TextInputHandler (queue)
    ↓
RobotController (main loop)
    ↓
_handle_conversation() (existing function)
    ↓
LLM → TTS → Response
```

## Next Steps

After Phase 1 is working:
- Phase 2: Health Monitoring
- Phase 3: Error Recovery
- Phase 4: Advanced Commands

## Support

If you encounter issues:
1. Check logs in `data/logs/robot.log`
2. Test manual text input first
3. Verify Telegram bot separately
4. Robot should continue working even if Telegram fails
