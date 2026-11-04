"""
Unit and integration tests for the NILA Wi-Fi Provisioning and Recovery System.

Covers:
1. Port 80 availability check and fallback (including guarding port 5000).
2. Robust connectivity states (local Wi-Fi vs WAN internet).
3. Secure credential handling & keyfile generation.
4. Wi-Fi scanning, parsing, and deduplication.
5. Connection failure & rollback to NILA-SETUP (incorrect password, unavailable AP).
6. Grace period and state machine transitions.
7. Service restart & interrupted transition recovery.
8. Web portal routes & captive portal redirects.
"""

import os
import stat
import subprocess
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from src.services.wifi_provisioning.config import WifiProvisioningConfig
from src.services.wifi_provisioning.network_manager import SafeNetworkManager
from src.services.wifi_provisioning.hotspot_manager import HotspotManager
from src.services.wifi_provisioning.port_utils import is_port_in_use, select_portal_port
from src.services.wifi_provisioning.watchdog import WifiWatchdog, ProvisioningState
from src.services.wifi_provisioning.web_portal import create_portal_app


class TestPortUtils(unittest.TestCase):
    """Tests for port checking and forbidden port enforcement."""

    def test_forbidden_ports_rejected(self):
        # Port 5000 (NILA main robot) must never be bound
        with self.assertRaises(ValueError):
            select_portal_port(preferred_port=5000, forbidden_ports=(5000, 22))

        # Port 22 (SSH) must never be bound
        with self.assertRaises(ValueError):
            select_portal_port(preferred_port=22, forbidden_ports=(5000, 22))

        # Fallback to forbidden port must also be rejected
        with patch("src.services.wifi_provisioning.port_utils.is_port_in_use", return_value=True):
            with self.assertRaises(ValueError):
                select_portal_port(preferred_port=80, fallback_port=5000, forbidden_ports=(5000, 22))

    def test_preferred_port_selected_when_available(self):
        with patch("src.services.wifi_provisioning.port_utils.is_port_in_use", return_value=False):
            port = select_portal_port(preferred_port=80, fallback_port=8080)
            self.assertEqual(port, 80)

    def test_fallback_port_selected_when_preferred_busy(self):
        def mock_in_use(port, host="0.0.0.0"):
            return port == 80  # port 80 is busy, 8080 is free

        with patch("src.services.wifi_provisioning.port_utils.is_port_in_use", side_effect=mock_in_use):
            port = select_portal_port(preferred_port=80, fallback_port=8080)
            self.assertEqual(port, 8080)


class TestConnectivityStateLogic(unittest.TestCase):
    """Tests for robust connectivity determination."""

    def setUp(self):
        self.config = WifiProvisioningConfig(hotspot_iface="wlan0", hotspot_profile_name="NILA-SETUP")

    def test_connected_with_local_ip_and_no_internet(self):
        """CRITICAL: Lack of internet access must NOT trigger Wi-Fi disconnection."""
        mock_executor = MagicMock()

        def executor_side_effect(args, **kwargs):
            if "status" in args:
                # wlan0 is connected to HomeWifi
                out = "wlan0:wifi:connected:HomeWifi\neth0:ethernet:unavailable:--\n"
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=out, stderr="")
            elif "addr" in args:
                # wlan0 has valid local IP
                out = "3: wlan0    inet 192.168.1.150/24 brd 192.168.1.255 scope global wlan0\n"
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=out, stderr="")
            elif "CONNECTIVITY" in args:
                # NO INTERNET! (e.g. portal, limited, or none)
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="none\n", stderr="")
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        mock_executor.side_effect = executor_side_effect
        mgr = SafeNetworkManager(config=self.config, cmd_executor=mock_executor)

        state = mgr.get_wifi_interface_state()
        self.assertTrue(state["is_wifi_connected"], "Wi-Fi should be connected when associated with valid IP")
        self.assertFalse(state["has_internet"], "Internet should be false")
        self.assertEqual(state["active_connection"], "HomeWifi")
        self.assertEqual(state["ip_address"], "192.168.1.150")

    def test_disconnected_when_no_active_connection(self):
        mock_executor = MagicMock()

        def executor_side_effect(args, **kwargs):
            if "status" in args:
                out = "wlan0:wifi:disconnected:--\n"
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=out, stderr="")
            elif "addr" in args:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        mock_executor.side_effect = executor_side_effect
        mgr = SafeNetworkManager(config=self.config, cmd_executor=mock_executor)

        state = mgr.get_wifi_interface_state()
        self.assertFalse(state["is_wifi_connected"])
        self.assertEqual(state["state"], "disconnected")

    def test_not_wifi_connected_when_in_hotspot_mode(self):
        """Active connection is NILA-SETUP; should not be treated as connected station mode."""
        mock_executor = MagicMock()

        def executor_side_effect(args, **kwargs):
            if "status" in args:
                out = "wlan0:wifi:connected:NILA-SETUP\n"
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=out, stderr="")
            elif "addr" in args:
                out = "3: wlan0    inet 192.168.4.1/24 scope global wlan0\n"
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=out, stderr="")
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        mock_executor.side_effect = executor_side_effect
        mgr = SafeNetworkManager(config=self.config, cmd_executor=mock_executor)

        state = mgr.get_wifi_interface_state()
        self.assertFalse(state["is_wifi_connected"])
        self.assertEqual(state["active_connection"], "NILA-SETUP")


class TestCredentialSecurityAndKeyfile(unittest.TestCase):
    """Tests for secure keyfile generation and permissions."""

    def setUp(self):
        self.config = WifiProvisioningConfig()
        self.mgr = SafeNetworkManager(self.config)

    def test_keyfile_generation_wpa2(self):
        uuid_str, content = self.mgr.generate_keyfile_content(
            ssid="OfficeWifi", password="super_secret_password", hidden=False
        )
        self.assertIn("[connection]", content)
        self.assertIn("id=OfficeWifi", content)
        self.assertIn(f"uuid={uuid_str}", content)
        self.assertIn("[wifi-security]", content)
        self.assertIn("key-mgmt=wpa-psk", content)
        self.assertIn("psk=super_secret_password", content)
        self.assertIn("method=auto", content)

    def test_keyfile_generation_open_network(self):
        uuid_str, content = self.mgr.generate_keyfile_content(
            ssid="OpenGuest", password=None, hidden=True
        )
        self.assertIn("id=OpenGuest", content)
        self.assertIn("hidden=true", content)
        self.assertNotIn("[wifi-security]", content)

    def test_keyfile_file_permissions_0600(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_executor = MagicMock(return_value=subprocess.CompletedProcess(args=[], returncode=0))
            mgr = SafeNetworkManager(self.config, cmd_executor=mock_executor)

            conn_uuid, path = mgr.save_connection_keyfile(
                ssid="SecTest", password="pwd12345678", dest_dir=tmpdir
            )
            self.assertTrue(os.path.exists(path))

            # Verify permissions are strictly 0600 (-rw-------)
            file_stat = os.stat(path)
            mode = stat.S_IMODE(file_stat.st_mode)
            self.assertEqual(mode, 0o600, f"Expected permissions 0600, got {oct(mode)}")

    def test_activate_connection_does_not_expose_password_in_args(self):
        mock_executor = MagicMock(return_value=subprocess.CompletedProcess(args=[], returncode=0))
        mgr = SafeNetworkManager(self.config, cmd_executor=mock_executor)

        dummy_uuid = "12345678-abcd-1234-abcd-1234567890ab"
        mgr.activate_connection_by_uuid(dummy_uuid)

        called_args = mock_executor.call_args[0][0]
        self.assertEqual(called_args, ["nmcli", "connection", "up", "uuid", dummy_uuid])
        # Password is never in command args!


class TestWifiScanning(unittest.TestCase):
    """Tests for parsing, deduplication, and filtering of Wi-Fi scans."""

    def test_scan_deduplication_and_filtering(self):
        mock_output = (
            "OfficeAP:AA\\:BB\\:CC\\:11\\:22\\:33:1:45:WPA2: \n"
            "OfficeAP:AA\\:BB\\:CC\\:11\\:22\\:34:6:85:WPA2:*\n"  # Stronger signal + in-use
            "GuestNet:11\\:22\\:33\\:44\\:55\\:66:11:70:: \n"   # Open network
            "NILA-SETUP:2C\\:CF\\:67\\:14\\:F2\\:AC:1:99:WPA2: \n" # Self-hotspot (must be excluded)
            ":99\\:88\\:77\\:66\\:55\\:44:6:30:WPA2: \n"          # Hidden empty SSID (must be excluded)
        )

        mock_executor = MagicMock(
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=mock_output, stderr="")
        )
        mgr = SafeNetworkManager(cmd_executor=mock_executor)

        networks = mgr.scan_networks()

        ssids = [n["ssid"] for n in networks]
        self.assertIn("OfficeAP", ssids)
        self.assertIn("GuestNet", ssids)
        self.assertNotIn("NILA-SETUP", ssids, "Self-hotspot must be excluded")
        self.assertNotIn("", ssids, "Empty SSIDs must be excluded")

        # Deduplication check: OfficeAP should have signal 85 (not 45)
        office = next(n for n in networks if n["ssid"] == "OfficeAP")
        self.assertEqual(office["signal"], 85)
        self.assertEqual(office["security"], "WPA2")
        self.assertTrue(office["in_use"])

        # GuestNet check
        guest = next(n for n in networks if n["ssid"] == "GuestNet")
        self.assertEqual(guest["security"], "Open")


class TestWatchdogTransitionsAndRecovery(unittest.TestCase):
    """Tests for state machine transitions, grace period, and failure recovery."""

    def test_grace_period_prevents_immediate_hotspot_trigger(self):
        cfg = WifiProvisioningConfig(disconnect_grace_period=40.0)
        mock_net = MagicMock()
        # Initially disconnected
        mock_net.get_wifi_interface_state.return_value = {"is_wifi_connected": False}

        mock_hotspot = MagicMock()
        mock_hotspot.is_hotspot_active.return_value = False

        wd = WifiWatchdog(config=cfg, network_mgr=mock_net, hotspot_mgr=mock_hotspot)
        wd._set_state(ProvisioningState.CONNECTED)

        # Step 1: Detect disconnect -> should enter GRACE_PERIOD
        wd.check_and_update_state()
        self.assertEqual(wd.state, ProvisioningState.GRACE_PERIOD)
        mock_hotspot.start_hotspot.assert_not_called()

        # Step 2: Immediate check within grace period -> stays in GRACE_PERIOD
        wd.check_and_update_state()
        self.assertEqual(wd.state, ProvisioningState.GRACE_PERIOD)
        mock_hotspot.start_hotspot.assert_not_called()

        # Step 3: Fast-forward time past grace period
        wd._disconnect_start_time = time.time() - 45.0
        wd.check_and_update_state()
        self.assertEqual(wd.state, ProvisioningState.HOTSPOT_ACTIVE)
        mock_hotspot.start_hotspot.assert_called_once()

    def test_reconnect_during_grace_period_aborts_hotspot(self):
        cfg = WifiProvisioningConfig(disconnect_grace_period=40.0)
        mock_net = MagicMock()
        mock_hotspot = MagicMock()
        mock_hotspot.is_hotspot_active.return_value = False

        wd = WifiWatchdog(config=cfg, network_mgr=mock_net, hotspot_mgr=mock_hotspot)
        wd._set_state(ProvisioningState.GRACE_PERIOD)
        wd._disconnect_start_time = time.time() - 10.0

        # Network reconnects naturally (e.g. temporary glitch resolved)
        mock_net.get_wifi_interface_state.return_value = {
            "is_wifi_connected": True,
            "active_connection": "HomeWifi",
            "ip_address": "192.168.1.50",
        }

        wd.check_and_update_state()
        self.assertEqual(wd.state, ProvisioningState.CONNECTED)
        mock_hotspot.start_hotspot.assert_not_called()

    def test_provisioning_failure_incorrect_password_triggers_rollback(self):
        """CRITICAL: Failed provisioning must immediately rollback to NILA-SETUP."""
        cfg = WifiProvisioningConfig(connect_timeout=2.0)
        mock_net = MagicMock()
        mock_net.save_connection_keyfile.return_value = ("uuid-1234", "/dummy/path")
        # Connection fails (e.g. wrong password or handshake failure)
        mock_net.activate_connection_by_uuid.return_value = False

        mock_hotspot = MagicMock()
        mock_hotspot.is_hotspot_active.return_value = True

        wd = WifiWatchdog(config=cfg, network_mgr=mock_net, hotspot_mgr=mock_hotspot)
        wd._set_state(ProvisioningState.HOTSPOT_ACTIVE)

        # Run provisioning worker directly
        wd._provision_worker(ssid="TargetNetwork", password="WrongPassword", hidden=False)

        # Rollback must restore hotspot
        mock_hotspot.start_hotspot.assert_called()
        self.assertEqual(wd.state, ProvisioningState.FAILED_ROLLBACK)
        self.assertIn("Connection failed", wd.last_error)

    def test_provisioning_unavailable_ap_times_out_and_rolls_back(self):
        cfg = WifiProvisioningConfig(connect_timeout=2.0)
        mock_net = MagicMock()
        mock_net.save_connection_keyfile.return_value = ("uuid-5678", "/dummy/path")
        # Simulate timeout exception
        mock_net.activate_connection_by_uuid.side_effect = Exception("AP not found / timeout")

        mock_hotspot = MagicMock()
        wd = WifiWatchdog(config=cfg, network_mgr=mock_net, hotspot_mgr=mock_hotspot)

        wd._provision_worker(ssid="NonExistentAP", password="password123", hidden=False)

        mock_hotspot.start_hotspot.assert_called()
        self.assertEqual(wd.state, ProvisioningState.FAILED_ROLLBACK)
        self.assertIn("Provisioning error", wd.last_error)

    def test_interrupted_transition_hotspot_reasserted_on_drop(self):
        """If hotspot unexpectedly drops while in HOTSPOT_ACTIVE, watchdog re-asserts it."""
        cfg = WifiProvisioningConfig()
        mock_net = MagicMock()
        mock_net.get_wifi_interface_state.return_value = {"is_wifi_connected": False}

        mock_hotspot = MagicMock()
        # Hotspot dropped unexpectedly
        mock_hotspot.is_hotspot_active.return_value = False

        wd = WifiWatchdog(config=cfg, network_mgr=mock_net, hotspot_mgr=mock_hotspot)
        wd._set_state(ProvisioningState.HOTSPOT_ACTIVE)

        wd.check_and_update_state()
        mock_hotspot.start_hotspot.assert_called_once()

    def test_watchdog_retains_hotspot_active_if_already_running_on_start(self):
        """If watchdog starts/restarts while hotspot is already up, immediately set HOTSPOT_ACTIVE."""
        cfg = WifiProvisioningConfig()
        mock_net = MagicMock()
        mock_net.get_wifi_interface_state.return_value = {"is_wifi_connected": False}

        mock_hotspot = MagicMock()
        mock_hotspot.is_hotspot_active.return_value = True

        wd = WifiWatchdog(config=cfg, network_mgr=mock_net, hotspot_mgr=mock_hotspot)
        # Starts with default initial state CONNECTED
        self.assertEqual(wd.state, ProvisioningState.CONNECTED)

        wd.check_and_update_state()
        self.assertEqual(wd.state, ProvisioningState.HOTSPOT_ACTIVE)


    def test_keyfile_with_special_characters_in_ssid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_executor = MagicMock(return_value=subprocess.CompletedProcess(args=[], returncode=0))
            mgr = SafeNetworkManager(cmd_executor=mock_executor)

            special_ssid = "My-Home_WiFi 5GHz (Guest)!"
            conn_uuid, path = mgr.save_connection_keyfile(
                ssid=special_ssid, password="passphrase_test", dest_dir=tmpdir
            )
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(f"id={special_ssid}", content)
            self.assertIn(f"ssid={special_ssid}", content)



class TestWebPortalAPI(unittest.TestCase):
    """Tests for Web Portal routes and Captive Portal redirects."""

    def setUp(self):
        self.config = WifiProvisioningConfig(primary_portal_ip="192.168.4.1", portal_port=80)
        self.mock_net = MagicMock()
        self.mock_watchdog = MagicMock()
        self.mock_watchdog.get_status_info.return_value = {
            "state": "HOTSPOT_ACTIVE",
            "is_wifi_connected": False,
            "active_connection": None,
            "ip_address": "192.168.4.1",
            "last_error": None,
            "primary_portal": "http://192.168.4.1:80",
        }
        self.mock_watchdog.provision_network_async.return_value = True

        self.app = create_portal_app(self.config, self.mock_net, self.mock_watchdog)
        self.client = self.app.test_client()

    def test_index_route(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"NILA-V2 Setup Portal", resp.data)

    def test_captive_portal_redirects(self):
        for path in ["/generate_204", "/hotspot-detect.html", "/ncsi.txt", "/connecttest.txt"]:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.headers["Location"].startswith("http://192.168.4.1"))

    def test_api_status(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["state"], "HOTSPOT_ACTIVE")

    def test_api_networks(self):
        self.mock_net.scan_networks.return_value = [
            {"ssid": "NetA", "signal": 80, "security": "WPA2"}
        ]
        resp = self.client.get("/api/networks")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data["networks"]), 1)
        self.assertEqual(data["networks"][0]["ssid"], "NetA")

    def test_api_connect_validation(self):
        # Empty SSID
        resp = self.client.post("/api/connect", json={"ssid": "", "password": "123"})
        self.assertEqual(resp.status_code, 400)

        # Password too short (< 8 chars)
        resp = self.client.post("/api/connect", json={"ssid": "ValidSSID", "password": "short"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("at least 8 characters", resp.get_json()["error"])

        # Valid payload
        resp = self.client.post("/api/connect", json={"ssid": "ValidSSID", "password": "valid_password_123"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "provisioning_started")
        self.mock_watchdog.provision_network_async.assert_called_with(
            ssid="ValidSSID", password="valid_password_123", hidden=False
        )


if __name__ == "__main__":
    unittest.main()
