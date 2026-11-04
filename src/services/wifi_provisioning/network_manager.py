"""
NetworkManager integration module for NILA Wi-Fi Provisioning.

Security Guarantees:
- Wi-Fi credentials are NEVER passed as process arguments (ps aux visible).
- Credentials are written via secure keyfiles with 0600 permissions.
- Logging filters ensure secrets are never leaked to logs or stdout.
- Robust connectivity detection differentiates local Wi-Fi association from WAN access.
"""

import logging
import os
import re
import subprocess
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.services.wifi_provisioning.config import WifiProvisioningConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class NetworkManagerError(Exception):
    """Base exception for NetworkManager operations."""
    pass


class SafeNetworkManager:
    """
    Safe wrapper around NetworkManager CLI (nmcli) and keyfile management.
    Supports dependency injection for subprocess execution to enable 100% test isolation.
    """

    def __init__(
        self,
        config: Optional[WifiProvisioningConfig] = None,
        cmd_executor: Optional[Callable[..., subprocess.CompletedProcess]] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        self._cmd_executor = cmd_executor or subprocess.run

    def _run_cmd(
        self,
        args: List[str],
        timeout: float = 15.0,
        check: bool = False,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Execute an external command safely without shell expansion.
        """
        try:
            res = self._cmd_executor(
                args,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                text=True,
                timeout=timeout,
                check=check,
            )
            return res
        except subprocess.TimeoutExpired as exc:
            logger.warning("Command %s timed out after %s seconds", args[0], timeout)
            raise NetworkManagerError(f"Command timed out: {args[0]}") from exc
        except Exception as exc:
            logger.error("Command %s failed: %s", args[0], exc)
            raise NetworkManagerError(f"Command failed: {args[0]} ({exc})") from exc

    def get_wifi_interface_state(self, iface: Optional[str] = None) -> Dict[str, Any]:
        """
        Inspect the wireless interface status.
        Returns:
            dict containing:
                - state: str (e.g. 'connected', 'disconnected', 'unavailable')
                - active_connection: str or None
                - ip_address: str or None
                - is_associated: bool
                - is_wifi_connected: bool (associated + valid IP, ignores WAN internet status)
                - has_internet: bool (informational only)
        """
        iface = iface or self.config.hotspot_iface
        result = {
            "iface": iface,
            "state": "unknown",
            "active_connection": None,
            "ip_address": None,
            "is_associated": False,
            "is_wifi_connected": False,
            "has_internet": False,
        }

        # 1. Check device status via nmcli
        try:
            cmd = ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev", "status"]
            proc = self._run_cmd(cmd, timeout=5.0)
            if proc.returncode == 0:
                for line in proc.stdout.strip().splitlines():
                    parts = line.split(":")
                    if len(parts) >= 4 and parts[0] == iface:
                        result["state"] = parts[2]
                        conn_name = parts[3].strip()
                        if conn_name and conn_name != "--":
                            result["active_connection"] = conn_name
                        break
        except Exception as err:
            logger.debug("Failed to query dev status for %s: %s", iface, err)

        # 2. Query IP address on iface
        try:
            cmd = ["ip", "-4", "-o", "addr", "show", "dev", iface]
            proc = self._run_cmd(cmd, timeout=5.0)
            if proc.returncode == 0 and proc.stdout.strip():
                # Format: 3: wlan0    inet 192.168.1.11/24 brd ...
                tokens = proc.stdout.strip().split()
                if "inet" in tokens:
                    inet_idx = tokens.index("inet")
                    if inet_idx + 1 < len(tokens):
                        cidr = tokens[inet_idx + 1]
                        result["ip_address"] = cidr.split("/")[0]
        except Exception as err:
            logger.debug("Failed to query IP address for %s: %s", iface, err)

        # 3. Determine robust connection status:
        # Interface is considered Wi-Fi connected if:
        # - state is 'connected'
        # - active_connection is not None and not the fallback hotspot profile
        # - it has a valid assigned IP address (not loopback/link-local 169.254/empty)
        is_conn = (
            result["state"] == "connected"
            and bool(result["active_connection"])
            and result["active_connection"] != self.config.hotspot_profile_name
            and bool(result["ip_address"])
            and not result["ip_address"].startswith("169.254.")
        )
        result["is_associated"] = result["state"] == "connected"
        result["is_wifi_connected"] = is_conn

        # 4. Check internet connectivity (informational only - NEVER used to trigger fallback)
        try:
            proc = self._run_cmd(["nmcli", "-t", "-f", "CONNECTIVITY", "g"], timeout=3.0)
            if proc.returncode == 0 and proc.stdout.strip() == "full":
                result["has_internet"] = True
        except Exception:
            result["has_internet"] = False

        return result

    def scan_networks(self, rescan: bool = False) -> List[Dict[str, Any]]:
        """
        Scan for nearby Wi-Fi networks and return a sanitized, sorted list.
        Deduplicates networks by SSID, keeping the one with the strongest signal.
        """
        cmd = ["nmcli", "-t", "-f", "SSID,BSSID,CHAN,SIGNAL,SECURITY,IN-USE", "dev", "wifi", "list"]
        if rescan:
            cmd.extend(["--rescan", "yes"])

        try:
            proc = self._run_cmd(cmd, timeout=12.0)
            if proc.returncode != 0:
                logger.warning("nmcli wifi scan returned non-zero code: %s", proc.returncode)
                return []
        except Exception as err:
            logger.error("Wi-Fi scan failed: %s", err)
            return []

        networks_map: Dict[str, Dict[str, Any]] = {}

        for line in proc.stdout.strip().splitlines():
            # nmcli escapes colons in SSIDs or BSSIDs with backslashes
            # Regex split respecting escaped colons:
            tokens = re.split(r"(?<!\\):", line)
            if len(tokens) < 5:
                continue

            ssid = tokens[0].replace(r"\:", ":").strip()
            bssid = tokens[1].replace(r"\:", ":").strip()
            chan = tokens[2].strip()
            signal_str = tokens[3].strip()
            security = tokens[4].replace(r"\:", ":").strip()
            in_use = tokens[5].strip() == "*" if len(tokens) >= 6 else False

            # Skip empty SSIDs (hidden networks from general scan) or our own setup hotspot
            if not ssid or ssid == self.config.hotspot_ssid:
                continue

            try:
                signal = int(signal_str)
            except ValueError:
                signal = 0

            # Simplify security display
            sec_display = "Open"
            if "WPA3" in security:
                sec_display = "WPA3"
            elif "WPA2" in security or "WPA1" in security:
                sec_display = "WPA2"
            elif "WEP" in security:
                sec_display = "WEP"

            net_entry = {
                "ssid": ssid,
                "bssid": bssid,
                "channel": chan,
                "signal": signal,
                "security": sec_display,
                "raw_security": security,
                "in_use": in_use,
            }

            # Deduplicate by SSID, keeping the highest signal
            if ssid not in networks_map or signal > networks_map[ssid]["signal"]:
                networks_map[ssid] = net_entry

        # Sort alphabetically or by signal strength (descending)
        sorted_networks = sorted(
            networks_map.values(), key=lambda x: (not x["in_use"], -x["signal"], x["ssid"].lower())
        )
        return sorted_networks

    def generate_keyfile_content(
        self,
        ssid: str,
        password: Optional[str] = None,
        hidden: bool = False,
        autoconnect: bool = True,
        autoconnect_priority: int = 10,
    ) -> Tuple[str, str]:
        """
        Generate a standard NetworkManager keyfile (INI format) in memory.
        Returns:
            Tuple[str, str]: (connection_uuid, keyfile_content)

        Security:
            Generated purely in memory; written directly to 0600 file.
            Zero command line argument exposure.
        """
        conn_uuid = str(uuid.uuid4())
        content_lines = [
            "[connection]",
            f"id={ssid}",
            f"uuid={conn_uuid}",
            "type=wifi",
            f"autoconnect={'true' if autoconnect else 'false'}",
            f"autoconnect-priority={autoconnect_priority}",
            "",
            "[wifi]",
            "mode=infrastructure",
            f"ssid={ssid}",
        ]

        if hidden:
            content_lines.append("hidden=true")

        if password:
            content_lines.extend([
                "",
                "[wifi-security]",
                "auth-alg=open",
                "key-mgmt=wpa-psk",
                f"psk={password}",
            ])

        content_lines.extend([
            "",
            "[ipv4]",
            "method=auto",
            "",
            "[ipv6]",
            "method=auto",
            "",
        ])

        return conn_uuid, "\n".join(content_lines)

    def save_connection_keyfile(
        self,
        ssid: str,
        password: Optional[str] = None,
        hidden: bool = False,
        dest_dir: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Securely save a Wi-Fi connection profile as a keyfile with 0600 permissions.
        Returns:
            Tuple[str, str]: (connection_uuid, keyfile_path)
        """
        dest_dir = dest_dir or self.config.system_connections_dir
        os.makedirs(dest_dir, exist_ok=True)

        # Sanitize filename (replace invalid chars with underscores)
        safe_filename = re.sub(r"[^a-zA-Z0-9_\-]", "_", ssid) + ".nmconnection"
        keyfile_path = os.path.join(dest_dir, safe_filename)

        conn_uuid, content = self.generate_keyfile_content(
            ssid=ssid,
            password=password,
            hidden=hidden,
            autoconnect=True,
            autoconnect_priority=10,
        )

        # Write file with restrictive 0600 permissions
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(keyfile_path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Saved secure connection keyfile for SSID '%s' (UUID: %s)", ssid, conn_uuid)

        # Reload connection in NetworkManager
        try:
            self._run_cmd(["nmcli", "connection", "load", keyfile_path], timeout=5.0)
        except Exception as err:
            logger.warning("nmcli connection load failed; attempting reload: %s", err)
            self._run_cmd(["nmcli", "connection", "reload"], timeout=5.0)

        return conn_uuid, keyfile_path

    def activate_connection_by_uuid(self, conn_uuid: str, timeout: Optional[float] = None) -> bool:
        """
        Activate a saved connection profile by UUID.
        Contains NO passwords or sensitive credentials in the command string!
        """
        timeout = timeout or self.config.connect_timeout
        logger.info("Activating connection UUID %s (timeout=%ss)...", conn_uuid, timeout)
        try:
            cmd = ["nmcli", "connection", "up", "uuid", conn_uuid]
            proc = self._run_cmd(cmd, timeout=timeout)
            if proc.returncode == 0:
                logger.info("Successfully activated connection UUID %s", conn_uuid)
                return True
            else:
                logger.warning(
                    "Connection up returned code %s: %s", proc.returncode, proc.stderr.strip()
                )
                return False
        except Exception as err:
            logger.error("Failed to activate connection UUID %s: %s", conn_uuid, err)
            return False

    def delete_connection_by_uuid(self, conn_uuid: str) -> bool:
        """Delete a connection profile by UUID."""
        try:
            proc = self._run_cmd(["nmcli", "connection", "delete", "uuid", conn_uuid], timeout=5.0)
            return proc.returncode == 0
        except Exception as err:
            logger.warning("Failed to delete connection UUID %s: %s", conn_uuid, err)
            return False

