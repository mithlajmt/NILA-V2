# NILA-V2 — Wi-Fi Provisioning & Recovery Operator Guide

## Overview

The NILA-V2 Wi-Fi Provisioning and Recovery System provides automatic failover to a secured local hotspot (`NILA-SETUP`) whenever NILA cannot connect to any saved Wi-Fi network (such as upon moving to a new deployment location).

When connected to `NILA-SETUP`, users access a responsive web portal at **`http://192.168.4.1`** to scan for available networks, enter credentials, and connect the robot.

---

## Architecture & State Machine

```
[System Boot / Normal Operation]
          │
          ▼
   [ CONNECTED ] ──(Wi-Fi disconnected)──► [ GRACE_PERIOD (45s) ]
          ▲                                         │
          │ (reconnected)                           │ (grace period expires)
          │                                         ▼
   [ CONNECTED ] ◄──(Provision Success)─── [ HOTSPOT_ACTIVE ]
                                              (NILA-SETUP active,
                                               Portal on 192.168.4.1)
                                                    │
                                                    ▼
                                            [ PROVISIONING (25s) ]
                                                    │
                                                    ▼ (Connection fails)
                                            [ FAILED_ROLLBACK ]
                                            (Hotspot restored immediately)
```

### Key Operating Principles
1. **Local Association vs. Internet:** Wi-Fi is considered connected if `wlan0` is associated with an AP and has a valid IPv4 address. Lack of WAN/Internet does NOT trigger hotspot fallback.
2. **Grace Period (45s):** Prevents Wi-Fi flapping or momentary router reboots from prematurely switching to hotspot mode.
3. **Guaranteed Rollback:** If the user enters an incorrect password or the AP is out of range, the system automatically reactivates `NILA-SETUP` within 25 seconds, ensuring the operator is never stranded.
4. **Port Isolation:** Binds strictly to HTTP port 80 (or 8080 fallback). Port 5000 (NILA main robot) and port 22 (SSH) are strictly protected.

---

## Security Architecture

- **Zero Secret Exposure:** Wi-Fi passphrases are written to NetworkManager `.nmconnection` files with strict `0600` permissions (`-rw-------`). Passwords are never passed as command-line arguments (preventing visibility via `ps aux`) and are redacted from all logging streams.
- **Offline Self-Contained Portal:** The web portal inlines all CSS and JavaScript. It does not require any external internet connection or CDNs.
- **Dormant Profile Design:** The `NILA-SETUP` connection profile is created with `autoconnect=false`, ensuring NetworkManager never activates the hotspot at boot when saved networks are reachable.

---

## Installation & Deployment Procedure

> [!IMPORTANT]
> Perform these commands with a secondary access method (such as an Ethernet cable connected to `eth0` or direct HDMI/keyboard) if available as a precaution.

### Step 1: Install Service and Staged Configurations
Run the non-destructive installation script:
```bash
cd /home/learnlogicai/nilaprod/NILA-V2
sudo bash scripts/install_wifi_provisioning.sh
```

### Step 2: Enable the Service for Automatic Boot
```bash
sudo systemctl enable nila-wifi-provisioning.service
```

### Step 3: Start the Service
```bash
sudo systemctl start nila-wifi-provisioning.service
```

### Step 4: Verify Service Status
```bash
sudo systemctl status nila-wifi-provisioning.service
```
Check live logs:
```bash
journalctl -u nila-wifi-provisioning.service -f
```

---

## How to Test the Provisioning Flow

### Normal Testing (Controlled Environment)
1. Ensure the service is running. Since NILA is currently connected to its primary Wi-Fi, the watchdog will report `state: CONNECTED` and the hotspot will remain dormant.
2. Check the status endpoint:
   ```bash
   curl http://127.0.0.1/api/status
   ```
3. To test fallback mode safely:
   - Temporarily disable the router or take NILA out of range of its saved networks.
   - Wait 45 seconds (grace period).
   - Use a phone or laptop to search for Wi-Fi networks: `NILA-SETUP` will appear.
   - Connect using password: `nilasetup2026`.
   - Open a browser and navigate to: **`http://192.168.4.1`**.
   - Select your target Wi-Fi, enter the password, and click **Connect**.
   - If password is correct: NILA connects and `NILA-SETUP` turns off.
   - If password is wrong: NILA rolls back and `NILA-SETUP` stays active.

---

## Emergency SSH Recovery Procedure

If SSH connectivity is lost during network transitions:

### Option A: Connect to NILA-SETUP Hotspot (Recommended)
1. On your laptop or phone, search for Wi-Fi network `NILA-SETUP`.
2. Connect using password: `nilasetup2026`.
3. Open SSH directly to the fixed gateway IP:
   ```bash
   ssh learnlogicai@192.168.4.1
   ```
   *(This requires no name resolution or internet and works 100% deterministically).*

### Option B: Direct Ethernet Cable (Local Network)
1. Plug an Ethernet cable into the Raspberry Pi's `eth0` port and connect it to your local router or laptop.
2. Find the IP assigned by your router (or check ARP / router DHCP client list).
3. Connect directly via IP:
   ```bash
   ssh learnlogicai@<eth0-ip>
   ```

### Option C: Re-assert Saved Network via Local Console
If you have a keyboard and monitor or serial console connected:
```bash
# Bring up your primary working Wi-Fi connection directly:
sudo nmcli con up "ROBUVERSE_HQ_RnD_0.1"
```

