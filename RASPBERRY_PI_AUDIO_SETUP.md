# PipeWire Audio Migration - Raspberry Pi Setup Guide

## What Changed

Your NILA-V2 robot has been migrated from `speech_recognition`/PyAudio to **PipeWire-compatible audio capture** using `sounddevice`. This fixes the voice recording issues on Raspberry Pi.

### Why This Was Necessary

- **Old system**: `speech_recognition` + PyAudio required exclusive ALSA access
- **Problem**: PipeWire (needed for Bluetooth) owns the USB mic, causing "device busy" errors
- **New system**: `sounddevice` works natively with PipeWire, no conflicts

---

## Installation on Raspberry Pi

### 1. Install System Dependencies

```bash
# Install PortAudio library (required by sounddevice)
sudo apt-get update
sudo apt-get install -y libportaudio2 portaudio19-dev

# Verify PipeWire is running (should already be installed)
systemctl --user status pipewire
```

### 2. Install Python Dependencies

```bash
cd ~/NILA-V2  # Or wherever your project is

# Uninstall old dependencies
pip uninstall -y SpeechRecognition pyaudio

# Install new dependencies
pip install sounddevice==0.4.6 scipy==1.11.4

# Or install all requirements
pip install -r requirements.txt
```

### 3. Verify Audio Setup

```bash
# Check PulseAudio/PipeWire devices
pactl list sources short

# You should see your USB microphone listed
# Example output:
# 45  alsa_input.usb-XXXX  PipeWire  s16le 1ch 16000Hz  RUNNING
```

### 4. Set Default Audio Devices (Important!)

```bash
# List all sources (microphones)
pactl list sources short

# Set USB mic as default (replace with your device name)
pactl set-default-source alsa_input.usb-XXXX

# List all sinks (speakers/headphones)
pactl list sinks short

# Set Bluetooth speaker as default (if using Bluetooth)
pactl set-default-sink bluez_output.XXXX
```

**💡 Tip**: Add these commands to `~/.bashrc` or create a startup script so they run on boot.

---

## Testing

### Test 1: List Audio Devices

```bash
python scripts/test_audio_capture.py --list-devices
```

**Expected output**: Should show your USB microphone in the list.

### Test 2: Simple Recording Test

```bash
python scripts/test_audio_capture.py --record 5
```

**Expected output**: 
- Records 5 seconds of audio
- Saves to `test_recording.wav`
- Shows audio statistics (amplitude, RMS level)

**Play it back**:
```bash
aplay test_recording.wav  # Or use VLC, etc.
```

### Test 3: Voice Activity Detection Test

```bash
python scripts/test_audio_capture.py --vad
```

**Expected output**:
- Starts listening
- Detects when you speak
- Stops after 1.5s of silence
- Saves to `test_vad_recording.wav`

### Test 4: Full STT Integration

```bash
python tests/manual_stt_check.py
```

**Expected output**: Should transcribe your speech using Google Cloud Speech API.

---

## Troubleshooting

### Issue: "No USB mic found, using default device"

**Solution**:
```bash
# Check if USB mic is connected
lsusb | grep -i audio

# Check PipeWire/PulseAudio sees it
pactl list sources short

# Set it as default
pactl set-default-source alsa_input.usb-XXXX
```

### Issue: "Audio level very low"

**Solution**:
```bash
# Increase microphone volume
pactl set-source-volume @DEFAULT_SOURCE@ 150%

# Or use alsamixer
alsamixer
# Press F6 to select USB device, F4 for capture, adjust with arrow keys
```

### Issue: "PortAudio not found" or "sounddevice import error"

**Solution**:
```bash
# Reinstall PortAudio
sudo apt-get install --reinstall libportaudio2 portaudio19-dev

# Reinstall sounddevice
pip install --force-reinstall sounddevice
```

### Issue: "Google Cloud Speech API error"

**Solution**:
```bash
# Make sure credentials are set
echo $GOOGLE_APPLICATION_CREDENTIALS

# If empty, set it in .env file:
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json

# Or export it:
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

### Issue: Recording works but transcription fails

**Possible causes**:
1. **No internet connection** (Google STT requires internet)
2. **Invalid Google Cloud credentials**
3. **Audio quality too low** (check with `--record` test)

---

## Configuration Options

You can customize audio settings in `.env` or `src/config/settings.py`:

```bash
# .env file
AUDIO_SAMPLE_RATE=16000      # Hz (don't change, Google STT requires 16kHz)
AUDIO_CHANNELS=1             # Mono (don't change)
AUDIO_DEVICE_NAME=           # Leave empty for auto-detect, or specify device name
```

---

## What's Different in the Code

### Old Way (speech_recognition)
```python
import speech_recognition as sr

recognizer = sr.Recognizer()
microphone = sr.Microphone()

with microphone as source:
    audio = recognizer.listen(source)
    text = recognizer.recognize_google(audio)
```

### New Way (sounddevice + Google Cloud)
```python
from src.services.speech.audio_capture import AudioCapture
from src.services.speech.providers.google_stt_provider import GoogleSTTProvider

capture = AudioCapture()
provider = GoogleSTTProvider()

audio_bytes = capture.record(timeout=30)
result = await provider.transcribe(audio_bytes)
text = result.text
```

**Benefits**:
- ✅ No ALSA conflicts
- ✅ Works with PipeWire/Bluetooth
- ✅ Lower latency
- ✅ More stable
- ✅ Better error handling

---

## Files Changed

### New Files
- `src/services/speech/audio_capture.py` - PipeWire-compatible audio capture
- `src/services/speech/providers/whisper_stt_provider.py` - Whisper provider (was missing)
- `scripts/test_audio_capture.py` - Audio testing utility

### Modified Files
- `src/services/speech/speech_recognizer.py` - Uses AudioCapture instead of speech_recognition
- `src/services/speech/providers/google_stt_provider.py` - Direct Google Cloud API
- `src/config/settings.py` - Added audio configuration
- `requirements.txt` - Replaced PyAudio with sounddevice

### Removed Dependencies
- ❌ `SpeechRecognition==3.10.0`
- ❌ `pyaudio==0.2.14`

### Added Dependencies
- ✅ `sounddevice==0.4.6`
- ✅ `scipy==1.11.4`

---

## Next Steps

1. **Deploy to Raspberry Pi**: Copy updated code to your Pi
2. **Install dependencies**: Run the installation commands above
3. **Test audio**: Use `test_audio_capture.py` to verify
4. **Run your robot**: `python main.py` should now work without audio errors
5. **Reboot test**: Reboot the Pi and verify audio still works

---

## Support

If you encounter issues:

1. Check PipeWire status: `systemctl --user status pipewire`
2. Check audio devices: `pactl list sources short`
3. Test recording: `python scripts/test_audio_capture.py --record 3`
4. Check logs in `data/logs/robot.log`

The new system is designed to be more reliable and should survive reboots without issues!
