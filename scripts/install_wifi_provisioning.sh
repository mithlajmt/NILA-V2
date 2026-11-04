#!/bin/bash
# ==============================================================================
# NILA-V2 — Wi-Fi Provisioning Service Installer
#
# Safe installation script:
# - Installs systemd service definition.
# - Stages dormant NILA-SETUP NetworkManager profile (autoconnect=false).
# - Configures optional captive portal DNS redirection.
# - DOES NOT activate the hotspot or disrupt the active Wi-Fi connection.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$SCRIPT_DIR/nila-wifi-provisioning.service"
DEST_SERVICE="/etc/systemd/system/nila-wifi-provisioning.service"

echo "=========================================================="
echo "🤖 NILA-V2: Installing Wi-Fi Provisioning Service"
echo "=========================================================="

# 1. Copy systemd service file
echo "📋 [1/4] Copying service definition to /etc/systemd/system/..."
sudo cp "$SERVICE_FILE" "$DEST_SERVICE"
sudo chmod 644 "$DEST_SERVICE"

# 2. Reload systemd daemon
echo "🔄 [2/4] Reloading systemd daemon..."
sudo systemctl daemon-reload

# 3. Create dormant NetworkManager hotspot profile if missing
echo "📡 [3/4] Ensuring dormant NILA-SETUP profile is registered (autoconnect=false)..."
NM_CONN_DIR="/etc/NetworkManager/system-connections"
HOTSPOT_KEYFILE="$NM_CONN_DIR/NILA-SETUP.nmconnection"

if [ ! -f "$HOTSPOT_KEYFILE" ]; then
    echo "Creating dormant $HOTSPOT_KEYFILE..."
    sudo bash -c "cat > '$HOTSPOT_KEYFILE'" << 'EOF'
[connection]
id=NILA-SETUP
uuid=7a18b763-9524-4f04-89c5-849547d6e47d
type=wifi
interface-name=wlan0
autoconnect=false
autoconnect-priority=-100

[wifi]
mode=ap
ssid=NILA-SETUP
band=bg
channel=1

[wifi-security]
key-mgmt=wpa-psk
psk=nilasetup2026

[ipv4]
address1=192.168.4.1/24
method=shared

[ipv6]
method=ignore
EOF
    sudo chmod 600 "$HOTSPOT_KEYFILE"
    sudo chown root:root "$HOTSPOT_KEYFILE"
    sudo nmcli connection load "$HOTSPOT_KEYFILE" || true
    echo "✓ Dormant NILA-SETUP profile created."
else
    echo "✓ NILA-SETUP profile already exists."
fi

# 4. Configure optional captive portal DNS
echo "🌐 [4/4] Configuring optional captive portal DNS redirection..."
DNS_DIR="/etc/NetworkManager/dnsmasq-shared.d"
if [ -d "$DNS_DIR" ]; then
    sudo bash -c "cat > '$DNS_DIR/nila-captive.conf'" << 'EOF'
address=/connectivitycheck.gstatic.com/192.168.4.1
address=/captive.apple.com/192.168.4.1
address=/msftconnecttest.com/192.168.4.1
address=/nila.local/192.168.4.1
EOF
    echo "✓ Captive DNS configuration saved to $DNS_DIR/nila-captive.conf."
fi

echo ""
echo "=========================================================="
echo "✅ Installation complete!"
echo "Service is INSTALLED but NOT started or enabled."
echo "Active Wi-Fi connection and SSH have NOT been modified."
echo ""
echo "To enable at boot:  sudo systemctl enable nila-wifi-provisioning.service"
echo "To start now:        sudo systemctl start nila-wifi-provisioning.service"
echo "To check status:     sudo systemctl status nila-wifi-provisioning.service"
echo "=========================================================="

