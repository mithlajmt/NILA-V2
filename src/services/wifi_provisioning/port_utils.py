"""
Network port verification and fallback utilities for NILA Wi-Fi Provisioning.
"""

import logging
import socket
from typing import Tuple

logger = logging.getLogger(__name__)


def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """
    Check if a TCP port is currently in use or cannot be bound on the given host.
    Returns True if port is unavailable, False if available.
    """
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        test_sock.bind((host, port))
        test_sock.close()
        return False
    except OSError as err:
        logger.debug("Port %s on %s is unavailable: %s", port, host, err)
        return True
    finally:
        try:
            test_sock.close()
        except Exception:
            pass


def select_portal_port(
    preferred_port: int = 80,
    fallback_port: int = 8080,
    forbidden_ports: Tuple[int, ...] = (5000, 22),
    host: str = "0.0.0.0",
) -> int:
    """
    Select an available port for the provisioning portal.
    Guarantees forbidden ports (such as NILA's voice service on 5000 or SSH on 22)
    are strictly rejected.

    Returns:
        int: The validated port number to bind.
    """
    if preferred_port in forbidden_ports:
        raise ValueError(
            f"Port {preferred_port} is reserved and strictly forbidden for Wi-Fi provisioning."
        )

    if not is_port_in_use(preferred_port, host):
        logger.info("Preferred portal port %s on %s is available.", preferred_port, host)
        return preferred_port

    logger.warning(
        "Preferred portal port %s is in use or restricted. Checking fallback port %s...",
        preferred_port,
        fallback_port,
    )

    if fallback_port in forbidden_ports:
        raise ValueError(
            f"Fallback port {fallback_port} is reserved and strictly forbidden."
        )

    if not is_port_in_use(fallback_port, host):
        logger.info("Fallback portal port %s is available.", fallback_port)
        return fallback_port

    logger.error("Neither port %s nor fallback port %s is available!", preferred_port, fallback_port)
    raise RuntimeError(
        f"Unable to find an open port for the Wi-Fi provisioning portal ({preferred_port}, {fallback_port} unavailable)."
    )

