# Quick Setup Guide - Deepgram STT

## 1. Install Deepgram SDK

```bash
pip install deepgram-sdk
```

## 2. Configure Your Environment

Add to your `.env` file:

```bash
# Switch to Deepgram provider
SPEECH_PROVIDER=deepgram

# Add your Deepgram API key
DEEPGRAM_API_KEY=your_api_key_here

# Optional: Configure settings
DEEPGRAM_MODEL=nova-2
DEEPGRAM_LANGUAGE=en-US
DEEPGRAM_SMART_FORMAT=True
```

> **Note**: You mentioned your API key is stored as `DEEPSEEK_KEY`. You can either:
> - Rename it to `DEEPGRAM_API_KEY` in your `.env`, or
> - Change line 18 in `src/config/settings.py` to use `DEEPSEEK_KEY` instead

## 3. Run Your Application

```bash
python main.py
```

That's it! Your robot will now use Deepgram for speech-to-text.

## Switching Providers

Change `SPEECH_PROVIDER` in `.env`:

```bash
SPEECH_PROVIDER=google    # Free Google STT
SPEECH_PROVIDER=whisper   # Offline Whisper
SPEECH_PROVIDER=deepgram  # Deepgram (requires API key)
```

No code changes needed!
