"""
Flask-based captive and local web portal for NILA Wi-Fi Provisioning.

Key Features:
- Bound to port 80 (or fallback 8080) after explicit port availability verification.
- Strictly guards against port 5000 (NILA main robot) and port 22 (SSH).
- Serves captive portal detection redirects (Android, Apple, Windows) pointing to http://192.168.4.1.
- Async Wi-Fi provisioning endpoint that handles secrets securely without logging.
"""

import logging
import os
import threading
from typing import Any, Dict, Optional

from flask import Flask, jsonify, redirect, render_template, request
from werkzeug.serving import make_server

from src.services.wifi_provisioning.config import WifiProvisioningConfig, DEFAULT_CONFIG
from src.services.wifi_provisioning.network_manager import SafeNetworkManager
from src.services.wifi_provisioning.port_utils import select_portal_port

logger = logging.getLogger(__name__)


def create_portal_app(
    config: Optional[WifiProvisioningConfig] = None,
    net_mgr: Optional[SafeNetworkManager] = None,
    watchdog: Optional[Any] = None,
) -> Flask:
    """Create and configure the Flask web portal."""
    cfg = config or DEFAULT_CONFIG
    mgr = net_mgr or SafeNetworkManager(cfg)

    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.config["SECRET_KEY"] = "nila-wifi-provisioning-secret-key"

    @app.route("/")
    def index():
        return render_template("index.html")

    # Captive portal detection endpoints
    @app.route("/generate_204")
    @app.route("/gen_204")
    @app.route("/mobile/status.php")
    @app.route("/hotspot-detect.html")
    @app.route("/canonical.html")
    @app.route("/connecttest.txt")
    @app.route("/ncsi.txt")
    def captive_redirect():
        """Redirect captive portal probes to the primary web portal."""
        primary_url = f"http://{cfg.primary_portal_ip}"
        if cfg.portal_port != 80:
            primary_url += f":{cfg.portal_port}"
        return redirect(primary_url + "/", code=302)

    # API Endpoints
    @app.route("/api/status", methods=["GET"])
    def get_status():
        if watchdog:
            return jsonify(watchdog.get_status_info())
        state = mgr.get_wifi_interface_state()
        return jsonify({
            "state": "STANDALONE",
            "is_wifi_connected": state.get("is_wifi_connected", False),
            "active_connection": state.get("active_connection"),
            "ip_address": state.get("ip_address"),
            "has_internet": state.get("has_internet", False),
            "primary_portal": f"http://{cfg.primary_portal_ip}:{cfg.portal_port}",
        })

    @app.route("/api/networks", methods=["GET"])
    def list_networks():
        rescan = request.args.get("rescan", "0") in ("1", "true", "yes")
        networks = mgr.scan_networks(rescan=rescan)
        return jsonify({"networks": networks, "count": len(networks)})

    @app.route("/api/connect", methods=["POST"])
    def connect_network():
        data = request.get_json(silent=True) or {}
        ssid = data.get("ssid", "").strip()
        password = data.get("password")
        hidden = bool(data.get("hidden", False))

        if not ssid:
            return jsonify({"error": "SSID cannot be empty"}), 400

        # WPA-PSK minimum passphrase length validation
        if password is not None and len(password) > 0 and len(password) < 8:
            return jsonify({"error": "WPA Wi-Fi passphrase must be at least 8 characters long"}), 400

        # Safe logging: strictly avoid logging the password
        logger.info("Received Wi-Fi provisioning request for SSID '%s' (hidden=%s)", ssid, hidden)

        if not watchdog:
            return jsonify({"error": "Watchdog service not attached"}), 503

        started = watchdog.provision_network_async(ssid=ssid, password=password, hidden=hidden)
        if not started:
            return jsonify({"error": "A provisioning attempt is already in progress"}), 409

        return jsonify({
            "status": "provisioning_started",
            "ssid": ssid,
            "message": f"Connection attempt started for '{ssid}'. Monitor /api/status for results.",
        })

    return app


class PortalServer:
    """Threaded HTTP server wrapper for the Flask provisioning portal."""

    def __init__(
        self,
        config: Optional[WifiProvisioningConfig] = None,
        net_mgr: Optional[SafeNetworkManager] = None,
        watchdog: Optional[Any] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        self.app = create_portal_app(self.config, net_mgr, watchdog)
        self._server = None
        self._thread: Optional[threading.Thread] = None
        self._bound_port: Optional[int] = None

    @property
    def bound_port(self) -> Optional[int]:
        return self._bound_port

    def start(self):
        """Select an open port and start the portal server."""
        if self._server:
            logger.info("Portal server is already running on port %s", self._bound_port)
            return

        # Explicitly verify port availability before binding
        self._bound_port = select_portal_port(
            preferred_port=self.config.portal_port,
            fallback_port=self.config.portal_fallback_port,
            forbidden_ports=self.config.forbidden_ports,
            host=self.config.portal_host,
        )

        logger.info(
            "Binding Wi-Fi provisioning portal to %s:%s...",
            self.config.portal_host,
            self._bound_port,
        )

        self._server = make_server(self.config.portal_host, self._bound_port, self.app, threaded=True)
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="PortalServerThread", daemon=True
        )
        self._thread.start()
        logger.info(
            "Provisioning portal running at http://%s:%s (Primary: http://%s:%s)",
            self.config.portal_host,
            self._bound_port,
            self.config.primary_portal_ip,
            self._bound_port,
        )

    def stop(self):
        """Shut down the portal server."""
        if self._server:
            logger.info("Shutting down portal server on port %s...", self._bound_port)
            self._server.shutdown()
            self._server = None
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._thread = None
            self._bound_port = None

