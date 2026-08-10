"""Constants for the vPro (Intel AMT) integration."""
from __future__ import annotations

DOMAIN = "vpro"

CONF_USE_TLS = "use_tls"

DEFAULT_PORT_TLS = 16993
DEFAULT_PORT_PLAIN = 16992
DEFAULT_SCAN_INTERVAL = 30  # seconds

PLATFORMS = ["switch", "button", "sensor", "binary_sensor"]
