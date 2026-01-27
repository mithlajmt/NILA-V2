#!/bin/bash
# Quick diagnostic script to check audio system
# Run this on your Raspberry Pi

echo "🔍 Audio System Diagnostic"
echo "=" * 60
echo ""

echo "1️⃣ Checking PulseAudio/PipeWire status..."
echo "----------------------------------------"
systemctl --user status pipewire --no-pager | head -10
echo ""

echo "2️⃣ Listing audio sources (microphones)..."
echo "----------------------------------------"
pactl list sources short
echo ""

echo "3️⃣ Listing audio sinks (speakers)..."
echo "----------------------------------------"
pactl list sinks short
echo ""

echo "4️⃣ Checking USB devices..."
echo "----------------------------------------"
lsusb | grep -i audio
echo ""

echo "5️⃣ Testing ALSA devices..."
echo "----------------------------------------"
arecord -l
echo ""

echo "6️⃣ Testing default input..."
echo "----------------------------------------"
timeout 2 arecord -d 2 -f cd test.wav 2>&1 | head -5
if [ -f test.wav ]; then
    echo "✅ Recording file created (mic might be working)"
    rm -f test.wav
else
    echo "❌ No recording file (mic not working)"
fi
echo ""

echo "7️⃣ Checking for audio processes..."
echo "----------------------------------------"
ps aux | grep -E "(parecord|arecord|pulseaudio|pipewire)" | grep -v grep
echo ""

echo "✅ Diagnostic complete!"
echo ""
echo "💡 Common fixes:"
echo "   - Restart audio: systemctl --user restart pipewire"
echo "   - Check USB connection: lsusb"
echo "   - Check permissions: groups (should include audio)"
echo "   - Reboot if needed"
