# Telegram Bot Control Guide

This guide explains how to use the Telegram bot to control Torres remotely.

## Setup

### 1. Get a Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Configure the Bot

Add to your `.env` file:

```bash
TELEGRAM_ENABLED=True
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 3. Start the Robot

When you start the robot with Telegram enabled, you'll see:
```
📱 Telegram bot initialized (will start when robot starts)
✅ Telegram bot started successfully
```

## Available Commands

### Basic Commands

#### `/start`
Welcome message with quick command overview.

```
/start
```

#### `/help`
Complete list of all commands with current mode status.

```
/help
```

#### `/status`
Detailed robot status including:
- Messages received
- Transcription success/failure rates
- AI response statistics
- Current input mode
- Current conversation mode
- Uptime

```
/status
```

---

### Input Mode Control

Control how Torres receives input (microphone vs text).

#### `/mic off` - Text Only Mode
Disables microphone, robot only processes Telegram messages.

```
/mic off
```

**Use when:**
- Microphone is broken or unavailable
- You want remote-only control
- Testing without audio hardware

#### `/mic on` - Voice Only Mode
Enables microphone, disables text input.

```
/mic on
```

**Use when:**
- You want the robot to only listen to voice
- Testing microphone functionality

#### `/mic hybrid` - Hybrid Mode (Default)
Both microphone and text are active. Text has priority.

```
/mic hybrid
```

**Use when:**
- You want flexibility (normal operation)
- Text can interrupt voice input

---

### Conversation Mode Control

Control how Torres processes input (AI vs direct speech).

#### `/mode chat` - AI Conversation (Default)
Torres uses the LLM to generate responses.

```
/mode chat
```

**Behavior:**
- User input → LLM → AI-generated response → TTS
- Torres responds with personality (savage, witty, 2-5 words)

#### `/mode speak` - Direct Speak Mode
Torres speaks exactly what you type, bypassing the LLM.

```
/mode speak
```

**Behavior:**
- User input → TTS (no LLM processing)
- Zero lag, instant speech
- Perfect for scripted content

**Use when:**
- Exhibitions with scripted dialogue
- Testing TTS without LLM costs
- You want Torres to say something specific

---

### Speech Scripts

Trigger pre-written speeches for exhibitions and demos.

#### `/speech` - List Available Speeches
Shows all stored speech scripts.

```
/speech
```

**Output:**
```
🎤 Available Speeches:

/speech ai_future - ഭാവിയിലെ കൃത്രിമ ബുദ്ധിയും മനുഷ്യനും

💡 Use /speech <name> to trigger a speech
```

#### `/speech <name>` - Trigger a Speech
Triggers a specific pre-written speech.

```
/speech ai_future
```

**Behavior:**
- Bypasses LLM completely
- Direct TTS of the full speech
- Zero lag
- Interrupts any current listening

**Available Speeches:**
- `ai_future` - Malayalam speech about AI and the future (full exhibition speech)

---

### Sending Messages

Any text message (not starting with `/`) is sent to Torres for processing.

```
Hello Torres
```

**Behavior depends on current mode:**
- **Chat mode:** Torres responds using AI
- **Speak mode:** Torres speaks your exact text

---

## Usage Examples

### Example 1: Remote Control During Exhibition

```bash
# Switch to text-only mode (disable mic)
/mic off

# Switch to speak mode (no AI, direct speech)
/mode speak

# Send scripted responses
Torres is a humanoid robot built by Robuverse.

# Trigger the AI future speech
/speech ai_future

# Check status
/status
```

### Example 2: Testing AI Responses

```bash
# Enable hybrid mode
/mic hybrid

# Use chat mode
/mode chat

# Send test messages
What is your name?
How are you?

# Check status
/status
```

### Example 3: Emergency Mic Failure

```bash
# Mic broke during demo? Switch to text-only
/mic off

# Now you can control Torres entirely via Telegram
Hello everyone, I am Torres!

# Check if it's working
/status
```

---

## Mode Combinations

| Input Mode | Conversation Mode | Behavior |
|------------|-------------------|----------|
| `voice` | `chat` | Mic only, AI responses |
| `voice` | `speak` | Mic only, speaks transcribed text |
| `text` | `chat` | Telegram only, AI responses |
| `text` | `speak` | Telegram only, speaks your text |
| `hybrid` | `chat` | Both (text priority), AI responses |
| `hybrid` | `speak` | Both (text priority), speaks input |

---

## Troubleshooting

### Bot Not Responding

1. Check if Telegram is enabled in `.env`:
   ```bash
   TELEGRAM_ENABLED=True
   ```

2. Check if the bot token is correct

3. Check robot logs for errors:
   ```
   ❌ Telegram bot failed to start: ...
   ```

### "Another bot instance is running" Error

Stop any other instances of the robot, then restart.

### Messages Not Being Processed

1. Check current mode with `/status`
2. If in `voice` mode, switch to `hybrid` or `text`:
   ```
   /mic hybrid
   ```

---

## Security Notes

- Keep your bot token **private** (never commit to Git)
- Only you should have access to the bot
- The bot token is in `.env` which is gitignored

---

## Adding More Speech Scripts

Edit `src/services/operator/speech_scripts.py`:

```python
"my_speech": {
    "title": "My Custom Speech",
    "content": "Full speech text here...",
    "language": "ml"  # or "en"
}
```

Then use:
```
/speech my_speech
```
