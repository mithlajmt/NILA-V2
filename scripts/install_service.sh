#!/bin/bash
set -e

SERVICE_SRC="$(dirname "$0")/nila.service"
SERVICE_DEST="/etc/systemd/system/nila.service"

echo "📋 Copying nila.service to /etc/systemd/system/..."
sudo cp "$SERVICE_SRC" "$SERVICE_DEST"

echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "⚡ Enabling nila.service to run automatically at boot/power on..."
sudo systemctl enable nila.service

echo "🚀 Starting nila.service now..."
sudo systemctl restart nila.service

echo "📊 Status of nila.service:"
sudo systemctl status nila.service --no-pager
