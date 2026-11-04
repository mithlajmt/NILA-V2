"""
Configuration settings for the NILA Wi-Fi Provisioning and Recovery System.
"""

import os
from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class WifiProvisioningConfig:
    """Wi-Fi provisioning service configuration."""

    # Hotspot settings
    hotspot_ssid: str = os.getenv("NILA_HOTSPOT_SSID", "NILA-SETUP")
    hotspot_password: str = os.getenv("NILA_HOTSPOT_PASSWORD", "nilasetup2026")
    hotspot_iface: str = os.getenv("NILA_WIFI_IFACE", "wlan0")
    hotspot_ip: str = os.getenv("NILA_HOTSPOT_IP", "192.168.4.1")
    hotspot_prefix: int = int(os.getenv("NILA_HOTSPOT_PREFIX", "24"))
    hotspot_profile_name: str = "NILA-SETUP"

    # Web portal settings
    portal_host: str = os.getenv("NILA_PORTAL_HOST", "0.0.0.0")
    portal_port: int = int(os.getenv("NILA_PORTAL_PORT", "80"))
    portal_fallback_port: int = int(os.getenv("NILA_PORTAL_FALLBACK_PORT", "8080"))
    primary_portal_ip: str = "192.168.4.1"

    # Protected ports: MUST NEVER bind to NILA main robot (5000) or SSH (22)
    forbidden_ports: Tuple[int, ...] = (5000, 22)

    # Timeouts and intervals (in seconds)
    disconnect_grace_period: float = float(os.getenv("NILA_DISCONNECT_GRACE_SEC", "45"))
    connect_timeout: float = float(os.getenv("NILA_CONNECT_TIMEOUT_SEC", "25"))
    health_check_interval: float = float(os.getenv("NILA_HEALTH_CHECK_SEC", "10"))
    scan_interval: float = float(os.getenv("NILA_SCAN_INTERVAL_SEC", "15"))

    # Filesystem paths
    system_connections_dir: str = os.getenv(
        "NILA_NM_CONNECTIONS_DIR", "/etc/NetworkManager/system-connections"
    )
    captive_dns_dir: str = os.getenv(
        "NILA_CAPTIVE_DNS_DIR", "/etc/NetworkManager/dnsmasq-shared.d"
    )

    # Logging
    log_level: str = os.getenv("NILA_WIFI_LOG_LEVEL", "INFO")


# Global default configuration instance
DEFAULT_CONFIG = WifiProvisioningConfig()

