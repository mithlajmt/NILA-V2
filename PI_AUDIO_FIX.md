# 🎤 Raspberry Pi Audio Fix Guide

## Problem
You're seeing these ALSA errors when NILA runs on your Raspberry Pi:
```
ALSA lib pcm_usb_stream.c:482:(_snd_pcm_usb_stream_open) Invalid card 'card'
ALSA lib confmisc.c:160:(snd_config_get_card) Invalid field card
```

Your USB microphone is detected as **card 2, device 0** but the system is trying to use "card" as a device name.

---

## 🚀 Quick Fix (Automatic)

### On your Raspberry Pi, run:

```bash
cd ~/motta/NILA-V2

# Pull latest changes (including the fix script)
git pull origin mattav1

# Make the script executable
chmod +x scripts/fix_pi_audio.sh

# Run the fix script
./scripts/fix_pi_audio.sh

# Restart NILA service
sudo systemctl restart nila.service

# Watch the logs (should see USB mic detected, no ALSA errors)
sudo journalctl -u nila.service -f
```

---

## 🔧 What the Fix Does

### 1. **Creates ALSA Configuration** (`~/.config/alsa/asoundrc`)
Tells ALSA to use your USB microphone (card 2) properly instead of looking for "card"

### 2. **Updates Systemd Service**
Changes the startup delay from 15 to 25 seconds to ensure USB audio is ready

### 3. **Enhanced Code**
Better USB microphone detection with clearer logging

---

## ✅ Verification

After running the fix and restarting, you should see in the logs:

```
✅ Found USB Microphone: 'USB PnP Sound Device: Audio (hw:2,0)' at index X
✅ Mic calibrated (threshold=XXX)
```

And **NO** ALSA errors about "Invalid card 'card'"

The JACK errors are harmless and can be ignored:
```
jack server is not running or cannot be started  ← This is fine!
```

---

## 🐛 If Issues Persist

### Check which device index is being used:

```bash
# Activate venv first
cd ~/motta/NILA-V2
source venv/bin/activate

# List all microphones with their index numbers
python3 -c "import speech_recognition as sr; [print(f'{i}: {name}') for i, name in enumerate(sr.Microphone.list_microphone_names())]"
```

Look for your USB mic and note its index number.

### Check service logs:
```bash
sudo journalctl -u nila.service -n 50
```

Look for the line that says "Found USB Microphone" with the index number.

---

## 📋 Manual Fix (if needed)

If the automatic script doesn't work, you can manually:

### 1. Create ALSA config:
```bash
mkdir -p ~/.config/alsa
nano ~/.config/alsa/asoundrc
```

Add:
```
defaults.pcm.card 2
defaults.ctl.card 2

pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:0,0"
    }
    capture.pcm {
        type plug
        slave.pcm "hw:2,0"
    }
}

ctl.!default {
    type hw
    card 2
}
```

### 2. Update service:
```bash
sudo nano /etc/systemd/system/nila.service
```

Change:
```
ExecStartPre=/bin/sleep 15
```

To:
```
ExecStartPre=/bin/sleep 25
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart nila.service
```

---

## 🎯 Expected Result

✅ No ALSA "Invalid card" errors  
✅ USB microphone detected automatically  
✅ Service starts reliably on boot  
✅ Voice recognition works smoothly  

---

**Questions?** Check the logs and share the output!
