"""
Hotspot management module for NILA Wi-Fi Provisioning.

Responsible for:
- Creating the dormant NILA-SETUP NetworkManager connection profile (autoconnect=no).
- Starting/stopping the secured fallback access point.
- Setting up optional captive portal DNS redirection (192.168.4.1).
"""

import logging
import os
import subprocess
from typing import Callable, Optional

from src.services.wifi_provisioning.config import WifiProvisioningConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class HotspotManager:
    """Manages the fallback Wi-Fi Hotspot (NILA-SETUP)."""

    def __init__(
        self,
        config: Optional[WifiProvisioningConfig] = None,
        cmd_executor: Optional[Callable[..., subprocess.CompletedProcess]] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        self._cmd_executor = cmd_executor or subprocess.run

    def _run_cmd(self, args, timeout=10.0, check=False) -> subprocess.CompletedProcess:
        return self._cmd_executor(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=check,
        )

    def is_hotspot_profile_present(self) -> bool:
        """Check if the NILA-SETUP connection profile exists in NetworkManager."""
        try:
            res = self._run_cmd(["nmcli", "-t", "-f", "NAME", "connection", "show"], timeout=5.0)
            if res.returncode == 0:
                names = [line.strip() for line in res.stdout.strip().splitlines()]
                return self.config.hotspot_profile_name in names
        except Exception as err:
            logger.debug("Failed to list connections: %s", err)
        return False

    def is_hotspot_active(self) -> bool:
        """Check if the NILA-SETUP hotspot is currently active on wlan0."""
        try:
            res = self._run_cmd(
                ["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"], timeout=5.0
            )
            if res.returncode == 0:
                for line in res.stdout.strip().splitlines():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        name, dev = parts[0], parts[1]
                        if name == self.config.hotspot_profile_name and dev == self.config.hotspot_iface:
                            return True
        except Exception as err:
            logger.debug("Failed to check active hotspot: %s", err)
        return False

    def generate_hotspot_keyfile_content(self) -> str:
        """
        Generate keyfile content for the NILA-SETUP hotspot.
        CRITICAL: autoconnect is explicitly 'false'.
        """
        cfg = self.config
        lines = [
            "[connection]",
            f"id={cfg.hotspot_profile_name}",
            f"uuid=7a18b763-9524-4f04-89c5-849547d6e47d",
            "type=wifi",
            f"interface-name={cfg.hotspot_iface}",
            "autoconnect=false",
            "autoconnect-priority=-100",
            "",
            "[wifi]",
            "mode=ap",
            f"ssid={cfg.hotspot_ssid}",
            "band=bg",
            "channel=1",
            "",
            "[wifi-security]",
            "key-mgmt=wpa-psk",
            f"psk={cfg.hotspot_password}",
            "",
            "[ipv4]",
            f"address1={cfg.hotspot_ip}/{cfg.hotspot_prefix}",
            "method=shared",
            "",
            "[ipv6]",
            "method=ignore",
            "",
        ]
        return "\n".join(lines)

    def create_dormant_hotspot_profile(self, dest_dir: Optional[str] = None) -> bool:
        """
        Create the dormant NILA-SETUP profile if it does not exist.
        Leaves it inactive (autoconnect=false).
        """
        dest_dir = dest_dir or self.config.system_connections_dir
        keyfile_path = os.path.join(dest_dir, f"{self.config.hotspot_profile_name}.nmconnection")

        if os.path.exists(keyfile_path) or self.is_hotspot_profile_present():
            logger.info("Hotspot profile '%s' already exists.", self.config.hotspot_profile_name)
            return True

        content = self.generate_hotspot_keyfile_content()
        try:
            os.makedirs(dest_dir, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            fd = os.open(keyfile_path, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info("Created dormant hotspot profile at %s (autoconnect=false)", keyfile_path)
            # Notify NetworkManager
            self._run_cmd(["nmcli", "connection", "load", keyfile_path], timeout=5.0)
            return True
        except PermissionError:
            logger.warning(
                "Permission denied creating %s (service will create upon start with root).",
                keyfile_path,
            )
            return False
        except Exception as err:
            logger.error("Failed to create dormant hotspot profile: %s", err)
            return False

    def setup_optional_captive_dns(self, dns_dir: Optional[str] = None) -> bool:
        """
        Configure optional captive portal DNS redirection for NetworkManager's shared dnsmasq.
        Treats failure gracefully (e.g. if running unprivileged during testing).
        """
        dns_dir = dns_dir or self.config.captive_dns_dir
        conf_path = os.path.join(dns_dir, "nila-captive.conf")

        content = (
            f"# NILA Captive Portal DNS redirection\n"
            f"# Direct common captive check domains to primary portal IP\n"
            f"address=/connectivitycheck.gstatic.com/{self.config.primary_portal_ip}\n"
            f"address=/captive.apple.com/{self.config.primary_portal_ip}\n"
            f"address=/msftconnecttest.com/{self.config.primary_portal_ip}\n"
            f"address=/nila.local/{self.config.primary_portal_ip}\n"
        )
        try:
            os.makedirs(dns_dir, exist_ok=True)
            with open(conf_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("Configured captive portal DNS at %s", conf_path)
            return True
        except PermissionError:
            logger.debug("Optional captive DNS configuration skipped (permission denied; root required).")
            return False
        except Exception as err:
            logger.debug("Optional captive DNS setup: %s", err)
            return False

    def start_hotspot(self) -> bool:
        """
        Activate the NILA-SETUP fallback hotspot.
        """
        logger.info("Starting fallback hotspot '%s'...", self.config.hotspot_profile_name)
        try:
            res = self._run_cmd(
                ["nmcli", "connection", "up", self.config.hotspot_profile_name], timeout=15.0
            )
            if res.returncode == 0:
                logger.info("Successfully started hotspot '%s'.", self.config.hotspot_profile_name)
                return True
            else:
                logger.error("Failed to start hotspot: %s", res.stderr.strip())
                return False
        except Exception as err:
            logger.error("Error starting hotspot '%s': %s", self.config.hotspot_profile_name, err)
            return False

    def stop_hotspot(self) -> bool:
        """
        Deactivate the NILA-SETUP fallback hotspot.
        """
        logger.info("Stopping fallback hotspot '%s'...", self.config.hotspot_profile_name)
        try:
            res = self._run_cmd(
                ["nmcli", "connection", "down", self.config.hotspot_profile_name], timeout=10.0
            )
            return res.returncode == 0
        except Exception as err:
            logger.warning("Error stopping hotspot '%s': %s", self.config.hotspot_profile_name, err)
            return False

