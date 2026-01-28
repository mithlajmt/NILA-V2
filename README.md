# NILA-V2: AI Robot Companion

NILA-V2 is an advanced AI robot companion capable of speech recognition, intelligent conversation (via LLMs), and expressive text-to-speech with lip-sync capabilities. It is designed to run on platforms like Raspberry Pi.

## Features
- **Speech Recognition**: Uses `SpeechRecognition` with `webrtcvad` for voice activity detection.
- **LLM Integration**: Supports OpenAI, Anthropic, and OpenRouter for intelligent responses.
- **Text-to-Speech**:
  - **Piper TTS**: High-quality, local neural TTS with low latency (Recommended for Pi).
  - **Edge TTS**: Free, high-quality neural TTS (Requires internet).
  - **Google Cloud TTS**: High-quality cloud-based TTS.
  - **gTTS**: Basic fallback.
- **Hardware Control**: Controls a robotic head (jaw and eye LEDs) via Arduino using serial communication.
- **Lip Sync**: Synchronizes jaw movement with speech amplitude.

## Hardware Requirements
- **Raspberry Pi 4 or 5** (Recommended for better performance with local TTS).
- **USB Microphone**.
- **Speaker** (3.5mm jack or USB).
- **Arduino** (Uno/Nano) connected via USB for servo control.
- **Servo Motor** (for jaw) and **LEDs** (for eyes).

## Installation on Raspberry Pi

### 1. Quick Start (Recommended)
The easiest way to get up and running is to use the automated setup script.

```bash
# 1. Clone the repository
git clone https://github.com/mithlajmt/NILA-V2.git
cd NILA-V2

# 2. Run the setup script
bash setup.sh
```

This script will automatically:
- Install system dependencies (ffmpeg, portaudio, etc.)
- Create a Python virtual environment
- Install Python libraries
- Download Piper TTS binary and voices (Ryan, Lessac, Arjun, Meera)
- Download Vosk speech recognition model

### 2. Configuration
After setup, configure your environment:

```bash
# Edit the configuration file
nano .env
```

**Key Settings:**
- `SPEECH_PROVIDER`: `google` (online) or `vosk` (offline)
- `TTS_PROVIDER`: `edge` (free, high quality) or `piper` (offline)
- `SERIAL_PORT`: `/dev/ttyUSB0` (for Arduino)

### Edge TTS Setup (Raspberry Pi)
If using Edge TTS, install `mpg123` for audio playback:
```bash
sudo apt-get install mpg123
```

### 3. Running the Robot
```bash
source venv/bin/activate
python main.py
```

### Manual Setup (Advanced)
If you prefer to set up manually, see `docs/MANUAL_SETUP.md` (optional).

## Troubleshooting

### Audio Issues
- **"No Default Output Device Available"**: Check your audio settings in `raspi-config` or use `alsamixer`.
- **Microphone not working**: Test with `arecord -d 5 test.wav` and `aplay test.wav`.

### Serial Permission Error
If you get "Permission denied" for `/dev/ttyUSB0`, the setup script tries to fix this, but you may need to **reboot** or **logout/login** for the changes to take effect.

### Piper Issues
- Ensure the `piper` binary has execute permissions: `chmod +x tools/piper/piper`.
- The setup script automatically detects your architecture (64-bit vs 32-bit).
