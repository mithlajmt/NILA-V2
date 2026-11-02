# 🤖 NILA-V2: Setup & Quick Start Helper

Welcome to **NILA-V2** by Robuverse! This document is your quick setup helper to get Nila up and running on your laptop or Raspberry Pi.

---

## 🚀 Quick Setup Helper

### 1. Automated Installation (Recommended for Raspberry Pi & Linux)

Run the automated setup script to install system dependencies, set up a Python virtual environment, download local Malayalam voice models, and configure serial permissions:

```bash
chmod +x setup.sh
./setup.sh
```

### 2. Manual Setup

If setting up manually:

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Download local Malayalam Piper TTS voice model
python3 scripts/setup_piper.py

# 4. Copy environment configuration template
cp .env.template .env
```

---

## ⚙️ Environment Setup (`.env`)

Edit your `.env` file to configure keys, speech settings, and personality:

```env
# --- MODE SELECTION ---
ENABLE_REALTIME_MODE=True            # True = Gemini Live WebSockets | False = 3-Step Offline Pipeline
REALTIME_PROVIDER=gemini_live        # gemini_live

# --- GEMINI LIVE SPEECH & PERSONALITY ---
GEMINI_API_KEY=AIzaSyYourActualKeyHere
GEMINI_LIVE_VOICE=Puck              # Puck, Charon, Kore, Fenrir, Aoede
GEMINI_LIVE_SILENCE_CHUNKS=18      # ~1.15s silence before turn commit (prevents cutting off mid-sentence)

# Personality System Prompt
LLM_SYSTEM_PROMPT="You are Nila, a funny humanoid robot built by Robuverse in Kerala. Speak short, friendly, and naturally in Malayalam or English."

# --- 3-STEP PIPELINE FALLBACK (OFFLINE / BACKUP) ---
SPEECH_PROVIDER=whisper            # whisper | deepgram | google
LLM_PROVIDER=openrouter            # openrouter | openai | anthropic | google
TTS_PROVIDER=piper                 # piper (local Malayalam) | elevenlabs | openai
```

---

## 🎮 Running Nila

### Start Full Robot Engine
```bash
source venv/bin/activate
python3 main.py
```

### Test Gemini Live Speech (Standalone Diagnostic)
```bash
python3 scripts/test_gemini_live.py
```

### Run Hardware Diagnostics
```bash
# Test microphone input & speaker output
python3 scripts/test_audio_capture.py

# Test Arduino USB serial connection & jaw servo lip-sync
python3 scripts/test_hardware.py

# Detect connected Arduino serial port (/dev/ttyUSB0)
python3 scripts/find_arduino.py
```

---

## ⚡ Auto-Start & Background Service Guide (`nila.service`)

NILA is completely set up and configured to run automatically in the background as a `systemd` service (`nila.service`) whenever the Raspberry Pi powers on or is plugged into a charger.

### 📋 Useful Service Commands

| Action | Command | Description |
| :--- | :--- | :--- |
| **👀 View Live Terminal / Logs** | `journalctl -u nila.service -f` | Stream live application logs, speech conversations & terminal output |
| **🔄 Restart Program** | `sudo systemctl restart nila.service` | Restart the robot service (after code or `.env` changes) |
| **⏹️ Stop Program** | `sudo systemctl stop nila.service` | Stop the background service (e.g. to run manually) |
| **▶️ Start Program** | `sudo systemctl start nila.service` | Start the background service manually |
| **📊 Check Service Status** | `sudo systemctl status nila.service` | View PID, active state, uptime, and latest status output |

---

### 🔍 Auto-Start & Fail-Safe Highlights

1. **Auto-Start on Power / Charge**:
   - `Loaded: ... enabled` means as soon as the Pi powers on when connected to power/charger, NILA starts automatically in the background without requiring manual intervention.
2. **Bluetooth Fail-Safe**:
   - At boot, the service automatically attempts to connect to the Bluetooth speaker (`ExecStartPre=-/bin/bash -c ...`).
   - If the speaker is powered off or temporarily out of range (`br-connection-page-timeout`), the `-` fail-safe prefix ensures `systemd` does not crash and proceeds to start NILA normally. Once the speaker is switched on within range, it connects automatically.
3. **Crash Recovery**:
   - `Restart=on-failure` with `RestartSec=5s` automatically recovers and relaunches NILA if an unexpected network or application interruption occurs.

---

### 🛠️ Installing or Updating the Service

To install or apply changes to `scripts/nila.service`:
```bash
chmod +x scripts/install_service.sh
./scripts/install_service.sh
```

---

## 🔧 Raspberry Pi Audio Fix

If running on Raspberry Pi and encountering ALSA errors (`Invalid card 'card'`):

```bash
chmod +x scripts/fix_pi_audio.sh
./scripts/fix_pi_audio.sh
```

---

## 📘 Comprehensive Architecture & Developer Guide

For detailed technical architecture, execution flow diagrams, and a developer roadmap on where to add future code (Next.js/Flutter frontend, Agent Workflows, Camera Vision), refer to **[DEVELOPER_GUIDE.md](file:///home/learnlogicai/nilaprod/NILA-V2/DEVELOPER_GUIDE.md)**.
