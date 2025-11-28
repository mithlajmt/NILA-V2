#!/bin/bash
# Fix audio configuration for NILA on Raspberry Pi
# This script fixes ALSA "Invalid card 'card'" errors and configures USB microphone

set -e

echo "🔧 Fixing NILA Audio Configuration on Raspberry Pi..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Create ALSA configuration to fix "Invalid card 'card'" error
echo -e "${YELLOW}📝 Creating ALSA configuration...${NC}"

mkdir -p ~/.config/alsa

cat > ~/.config/alsa/asoundrc << 'EOF'
# ALSA configuration for NILA-V2 on Raspberry Pi
# This fixes "Invalid card 'card'" errors

# Set default devices to USB Audio (card 2)
defaults.pcm.card 2
defaults.ctl.card 2

# Define USB microphone as default capture device
pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:0,0"  # Default audio output
    }
    capture.pcm {
        type plug
        slave.pcm "hw:2,0"  # USB microphone
    }
}

# Control device
ctl.!default {
    type hw
    card 2
}
EOF

echo -e "${GREEN}✅ Created ~/.config/alsa/asoundrc${NC}"
echo ""

# 2. Update systemd service to wait longer for USB audio
echo -e "${YELLOW}🔧 Updating systemd service...${NC}"

if [ -f /etc/systemd/system/nila.service ]; then
    sudo cp /etc/systemd/system/nila.service /etc/systemd/system/nila.service.backup
    echo -e "${GREEN}✅ Backed up existing service to nila.service.backup${NC}"
    
    # Update sleep time from 15 to 25 seconds
    sudo sed -i 's|ExecStartPre=/bin/sleep 15|ExecStartPre=/bin/sleep 25|g' /etc/systemd/system/nila.service
    
    echo -e "${GREEN}✅ Updated service wait time to 25 seconds${NC}"
    echo ""
    
    # Reload systemd
    echo -e "${YELLOW}🔄 Reloading systemd...${NC}"
    sudo systemctl daemon-reload
    echo -e "${GREEN}✅ Systemd reloaded${NC}"
    echo ""
else
    echo -e "${RED}⚠️  Service file not found at /etc/systemd/system/nila.service${NC}"
    echo "If you're running manually, that's fine!"
    echo ""
fi

# 3. Test microphone detection
echo -e "${YELLOW}🎤 Testing microphone detection...${NC}"
echo ""

arecord -l

echo ""
echo -e "${GREEN}✅ Audio fix script completed!${NC}"
echo ""
echo "📋 Next steps:"
echo "  1. Restart the NILA service: sudo systemctl restart nila.service"
echo "  2. Check logs: sudo journalctl -u nila.service -f"
echo "  3. The ALSA 'Invalid card' errors should be gone!"
echo ""
