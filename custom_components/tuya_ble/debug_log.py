"""Private file logging for Tuya BLE diagnostics."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

from homeassistant.core import HomeAssistant

from .const import DOMAIN

DEBUG_LOG_FILE: Final = "tuya_ble_debug.log"
_LOGGER_NAMES: Final = (f"custom_components.{DOMAIN}",)
_HANDLER_NAME: Final = "tuya_ble_private_file_handler"


def setup_private_debug_log(hass: HomeAssistant) -> Path:
    """Route Tuya BLE debug logs to a private rotating file.

    Home Assistant's logging integration receives records through propagation to
    the root logger.  The Tuya BLE namespace is configured with ``propagate =
    False`` so detailed debug diagnostics stay in this file instead of flooding
    Home Assistant Core/system logs.
    """

    log_path = Path(hass.config.path(DEBUG_LOG_FILE))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    for logger_name in _LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        handler = next(
            (
                existing_handler
                for existing_handler in logger.handlers
                if getattr(existing_handler, "name", None) == _HANDLER_NAME
            ),
            None,
        )
        if handler is None:
            handler = RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            handler.name = _HANDLER_NAME
            logger.addHandler(handler)

        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)

    logging.getLogger(__name__).info(
        "Tuya BLE private debug logging enabled at %s", log_path
    )
    return log_path
