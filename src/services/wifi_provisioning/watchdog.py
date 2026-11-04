"""
Watchdog state machine for NILA Wi-Fi Provisioning and Recovery.

Guarantees:
- Never blocks NILA main robot service (operates independently as a non-blocking daemon).
- Robust connectivity logic: local Wi-Fi association + IP is considered connected;
  lack of WAN/internet does NOT trigger hotspot fallback.
- Grace period before activating hotspot on disconnect to allow natural roaming/reconnect.
- Reliable rollback: If newly provisioned credentials fail, NILA-SETUP is immediately restored.
"""

import enum
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

from src.services.wifi_provisioning.config import WifiProvisioningConfig, DEFAULT_CONFIG
from src.services.wifi_provisioning.network_manager import SafeNetworkManager
from src.services.wifi_provisioning.hotspot_manager import HotspotManager

logger = logging.getLogger(__name__)


class ProvisioningState(str, enum.Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    GRACE_PERIOD = "GRACE_PERIOD"
    HOTSPOT_ACTIVE = "HOTSPOT_ACTIVE"
    PROVISIONING = "PROVISIONING"
    FAILED_ROLLBACK = "FAILED_ROLLBACK"


class WifiWatchdog:
    """
    Watches Wi-Fi connectivity and manages transitions between managed station mode
    and the NILA-SETUP fallback hotspot.
    """

    def __init__(
        self,
        config: Optional[WifiProvisioningConfig] = None,
        network_mgr: Optional[SafeNetworkManager] = None,
        hotspot_mgr: Optional[HotspotManager] = None,
        portal_starter: Optional[Callable[[], Any]] = None,
        portal_stopper: Optional[Callable[[], Any]] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        self.net_mgr = network_mgr or SafeNetworkManager(self.config)
        self.hotspot_mgr = hotspot_mgr or HotspotManager(self.config)
        self._portal_starter = portal_starter
        self._portal_stopper = portal_stopper

        self._state = ProvisioningState.CONNECTED
        self._disconnect_start_time: Optional[float] = None
        self._last_error_message: Optional[str] = None
        self._target_ssid: Optional[str] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def state(self) -> ProvisioningState:
        with self._lock:
            return self._state

    @property
    def last_error(self) -> Optional[str]:
        with self._lock:
            return self._last_error_message

    @property
    def target_ssid(self) -> Optional[str]:
        with self._lock:
            return self._target_ssid

    def get_status_info(self) -> Dict[str, Any]:
        """Return full diagnostic status dictionary."""
        with self._lock:
            current_state = self._state.value
            err = self._last_error_message
            tgt = self._target_ssid

        wifi_state = self.net_mgr.get_wifi_interface_state()

        return {
            "state": current_state,
            "is_wifi_connected": wifi_state.get("is_wifi_connected", False),
            "active_connection": wifi_state.get("active_connection"),
            "ip_address": wifi_state.get("ip_address"),
            "has_internet": wifi_state.get("has_internet", False),
            "target_ssid": tgt,
            "last_error": err,
            "hotspot_active": self.hotspot_mgr.is_hotspot_active(),
            "primary_portal": f"http://{self.config.primary_portal_ip}:{self.config.portal_port}",
        }

    def _set_state(self, new_state: ProvisioningState, error_msg: Optional[str] = None):
        with self._lock:
            if self._state != new_state:
                logger.info("Watchdog state transition: %s -> %s", self._state.value, new_state.value)
            self._state = new_state
            if error_msg is not None:
                self._last_error_message = error_msg

    def start(self):
        """Start the watchdog background monitoring loop."""
        with self._lock:
            if self._running:
                return
            self._running = True

        logger.info("Starting Wi-Fi provisioning watchdog daemon...")
        self._thread = threading.Thread(target=self._run_loop, name="WifiWatchdogThread", daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the watchdog daemon."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Wi-Fi provisioning watchdog stopped.")

    def check_and_update_state(self):
        """
        Single step of the state machine.
        Inspects link state, manages grace periods, and triggers hotspot fallback or recovery.
        """
        with self._lock:
            current_state = self._state

        # If currently provisioning a new connection, allow provisioning worker thread to finish
        if current_state == ProvisioningState.PROVISIONING:
            return

        wifi_info = self.net_mgr.get_wifi_interface_state()
        is_connected = wifi_info.get("is_wifi_connected", False)

        now = time.time()

        if is_connected:
            # Successfully connected to normal Wi-Fi network
            self._disconnect_start_time = None
            if current_state != ProvisioningState.CONNECTED:
                logger.info(
                    "Wi-Fi connection verified (SSID: %s, IP: %s).",
                    wifi_info.get("active_connection"),
                    wifi_info.get("ip_address"),
                )
                # If hotspot was running, shut it down
                if self.hotspot_mgr.is_hotspot_active():
                    self.hotspot_mgr.stop_hotspot()
                self._set_state(ProvisioningState.CONNECTED)
            return

        # Interface is NOT connected to a normal Wi-Fi network
        # If hotspot is already active (e.g. after service restart), maintain HOTSPOT_ACTIVE state
        if self.hotspot_mgr.is_hotspot_active():
            if current_state != ProvisioningState.HOTSPOT_ACTIVE:
                self._set_state(ProvisioningState.HOTSPOT_ACTIVE)
            return

        if current_state == ProvisioningState.CONNECTED:
            # Transition to GRACE_PERIOD
            self._disconnect_start_time = now
            self._set_state(
                ProvisioningState.GRACE_PERIOD,
                error_msg="Wi-Fi disconnected. Waiting for automatic reconnect...",
            )
            return

        if current_state == ProvisioningState.GRACE_PERIOD:
            elapsed = now - (self._disconnect_start_time or now)
            if elapsed < self.config.disconnect_grace_period:
                logger.debug(
                    "In grace period (%.1fs / %.1fs)...",
                    elapsed,
                    self.config.disconnect_grace_period,
                )
                return

            # Grace period expired without reconnect -> Activate Hotspot
            logger.warning(
                "Grace period of %ss expired without reconnection. Activating fallback hotspot...",
                self.config.disconnect_grace_period,
            )
            self._activate_hotspot_mode()
            return

        if current_state in (ProvisioningState.HOTSPOT_ACTIVE, ProvisioningState.FAILED_ROLLBACK):
            # Ensure hotspot remains active
            if not self.hotspot_mgr.is_hotspot_active():
                logger.warning("Hotspot unexpectedly dropped; re-activating...")
                self.hotspot_mgr.start_hotspot()

    def _activate_hotspot_mode(self):
        """Ensure dormant profile exists, start hotspot, and ensure portal is running."""
        self.hotspot_mgr.create_dormant_hotspot_profile()
        self.hotspot_mgr.setup_optional_captive_dns()
        started = self.hotspot_mgr.start_hotspot()

        if started:
            self._set_state(ProvisioningState.HOTSPOT_ACTIVE)
            if self._portal_starter:
                try:
                    self._portal_starter()
                except Exception as err:
                    logger.error("Failed to start web portal: %s", err)
        else:
            self._set_state(
                ProvisioningState.DISCONNECTED,
                error_msg="Failed to start fallback hotspot. Will retry...",
            )

    def provision_network_async(
        self, ssid: str, password: Optional[str] = None, hidden: bool = False
    ) -> bool:
        """
        Initiate asynchronous Wi-Fi provisioning.
        Returns True if provisioning started, False if already in progress.
        """
        with self._lock:
            if self._state == ProvisioningState.PROVISIONING:
                logger.warning("Provisioning already in progress for '%s'", self._target_ssid)
                return False
            self._target_ssid = ssid
            self._last_error_message = None
            self._state = ProvisioningState.PROVISIONING

        thread = threading.Thread(
            target=self._provision_worker,
            args=(ssid, password, hidden),
            name="WifiProvisionWorker",
            daemon=True,
        )
        thread.start()
        return True

    def _provision_worker(self, ssid: str, password: Optional[str], hidden: bool):
        """
        Background worker that executes the connection attempt and handles reliable rollback.
        """
        logger.info("Starting provisioning attempt for SSID '%s'...", ssid)
        conn_uuid = None

        try:
            # 1. Save connection keyfile securely with 0600 permissions
            conn_uuid, _ = self.net_mgr.save_connection_keyfile(
                ssid=ssid, password=password, hidden=hidden
            )

            # Brief grace delay to ensure HTTP 200 response packets reach the client browser
            time.sleep(1.0)

            # 2. If hotspot is running, pause/stop hotspot before attempting association
            if self.hotspot_mgr.is_hotspot_active():
                logger.info("Stopping hotspot to test association with '%s'...", ssid)
                self.hotspot_mgr.stop_hotspot()

            # 3. Attempt connection with strict timeout
            connected = self.net_mgr.activate_connection_by_uuid(
                conn_uuid, timeout=self.config.connect_timeout
            )

            # 4. Verify link state and IPv4 assignment
            if connected:
                time.sleep(2.0)
                wifi_state = self.net_mgr.get_wifi_interface_state()
                if wifi_state.get("is_wifi_connected", False):
                    logger.info("Successfully connected to '%s'! Provisioning complete.", ssid)
                    self._set_state(ProvisioningState.CONNECTED)
                    return

            # Connection attempt failed or timed out -> ROLLBACK
            fail_reason = "Connection failed: Invalid password, out of range, or DHCP timeout."
            logger.warning("Connection to '%s' failed. Initiating rollback to hotspot...", ssid)
            self._rollback_to_hotspot(fail_reason)

        except Exception as err:
            logger.error("Unhandled error during provisioning for '%s': %s", ssid, err)
            self._rollback_to_hotspot(f"Provisioning error: {err}")

    def _rollback_to_hotspot(self, error_msg: str):
        """
        Reliably restore NILA-SETUP hotspot after connection failure.
        Ensures user is never stranded.
        """
        logger.info("Restoring NILA-SETUP fallback hotspot...")
        self.hotspot_mgr.start_hotspot()
        self._set_state(ProvisioningState.FAILED_ROLLBACK, error_msg=error_msg)

    def _run_loop(self):
        """Main monitoring loop."""
        while True:
            with self._lock:
                if not self._running:
                    break

            try:
                self.check_and_update_state()
            except Exception as exc:
                logger.error("Error in watchdog loop: %s", exc, exc_info=True)

            # Sleep in small increments for responsive shutdown
            for _ in range(int(self.config.health_check_interval * 2)):
                with self._lock:
                    if not self._running:
                        break
                time.sleep(0.5)

