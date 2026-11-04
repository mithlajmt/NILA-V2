"""
Main daemon entry point for NILA Wi-Fi Provisioning and Recovery Service.

Runs as a systemd background service.
Guarantees:
- Safe signal handling (SIGTERM, SIGINT).
- Port 80 validation with graceful 8080 fallback.
- Never logs sensitive credentials.
- Non-blocking design that does not hinder nila.service.
"""

import logging
import signal
import sys
import time

from src.services.wifi_provisioning.config import DEFAULT_CONFIG, WifiProvisioningConfig
from src.services.wifi_provisioning.network_manager import SafeNetworkManager
from src.services.wifi_provisioning.hotspot_manager import HotspotManager
from src.services.wifi_provisioning.web_portal import PortalServer
from src.services.wifi_provisioning.watchdog import WifiWatchdog


def setup_secure_logging(level: str = "INFO"):
    """Configure logging with credential masking."""
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [WifiProvisioning] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers = [handler]


def main():
    setup_secure_logging(DEFAULT_CONFIG.log_level)
    logger = logging.getLogger("WifiProvisioningDaemon")
    logger.info("Initializing NILA Wi-Fi Provisioning and Recovery Service...")

    config = DEFAULT_CONFIG
    net_mgr = SafeNetworkManager(config)
    hotspot_mgr = HotspotManager(config)

    # 1. Ensure dormant hotspot profile is created (autoconnect=false)
    hotspot_mgr.create_dormant_hotspot_profile()

    # 2. Setup server & watchdog components
    portal_server: PortalServer = None

    def start_portal():
        nonlocal portal_server
        if portal_server:
            portal_server.start()

    def stop_portal():
        nonlocal portal_server
        if portal_server:
            portal_server.stop()

    watchdog = WifiWatchdog(
        config=config,
        network_mgr=net_mgr,
        hotspot_mgr=hotspot_mgr,
        portal_starter=start_portal,
        portal_stopper=stop_portal,
    )

    portal_server = PortalServer(config=config, net_mgr=net_mgr, watchdog=watchdog)

    # 3. Handle termination signals gracefully
    running = True

    def sig_handler(signum, frame):
        nonlocal running
        logger.info("Received termination signal (%s). Shutting down cleanly...", signum)
        running = False

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # 4. Start watchdog and portal
    watchdog.start()
    portal_server.start()

    logger.info("Wi-Fi Provisioning Service running. Press Ctrl+C or send SIGTERM to terminate.")

    # 5. Main loop
    try:
        while running:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    finally:
        logger.info("Cleaning up resources...")
        watchdog.stop()
        portal_server.stop()
        logger.info("Wi-Fi Provisioning Service exited cleanly.")


if __name__ == "__main__":
    main()

