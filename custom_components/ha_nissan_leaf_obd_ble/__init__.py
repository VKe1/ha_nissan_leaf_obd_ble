"""Nissan Leaf OBD BLE — Home Assistant custom integration (ha_nissan_leaf_obd_ble).

Sets up one coordinator per config entry (one per OBD adapter / Leaf),
registers a Bluetooth callback so new polls are triggered immediately when
the adapter comes back into range, and forwards entries to the sensor platform.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from bleak_retry_connector import get_device

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, STARTUP_MESSAGE, VERSION
from .coordinator import NissanLeafCoordinator
from .py_nissan_leaf_obd_ble import NissanLeafObdBleApiClient

__version__ = VERSION

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML-based setup is not supported; only UI config flow is used."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an ha_nissan_leaf_obd_ble config entry."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    address: str = entry.data[CONF_ADDRESS]

    # Try to resolve a BLEDevice from the current scan results or from
    # HA's last-seen Bluetooth history.  Using connectable=False for the
    # history lookup lets us create the API client even when the car is
    # away from home — the coordinator handles the "device not reachable"
    # case gracefully by returning persisted data.
    ble_device = (
        bluetooth.async_ble_device_from_address(hass, address.upper(), connectable=True)
        or (
            (info := async_last_service_info(hass, address.upper(), connectable=False))
            and info.device
        )
        or await get_device(address)
    )

    api = NissanLeafObdBleApiClient(ble_device) if ble_device else None

    coordinator = NissanLeafCoordinator(hass, entry, api)

    # Load persisted sensor data BEFORE the first refresh so sensors
    # immediately show their last known values (even if the car is away).
    await coordinator.async_load_persistent_data()

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        cached_data = coordinator.cached_data
        if not cached_data:
            raise
        _LOGGER.warning(
            "Initial OBD poll failed for %s; continuing with cached data",
            address,
        )
        coordinator.async_set_updated_data(cached_data)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ------------------------------------------------------------------
    # Presence-triggered refresh
    #
    # Connecting to the adapter wakes the car's OBD/CAN bus, which makes the
    # Leaf's relays click.  That is normal but not free (relay wear + a small
    # 12 V drain), so the integration does not poll aggressively.  Instead it
    # reacts to *presence changes*:
    #
    #   * while the adapter keeps advertising in place (car parked at home),
    #     advertisement-triggered refreshes are throttled to the slow poll
    #     interval, so the relays are not clicked for every advertisement;
    #   * when the adapter disappears (car driven away, or the dongle loses
    #     power with the ignition) the throttle is reset and the coordinator
    #     falls back to the extra-slow interval;
    #   * the first advertisement after that triggers an immediate poll, so
    #     arriving home refreshes the data without waiting for the timer even
    #     when slow poll is set to e.g. 1800 s.
    # ------------------------------------------------------------------
    last_adv_refresh = 0.0
    adapter_unavailable = False

    @callback
    def _on_adapter_detected(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        nonlocal last_adv_refresh, adapter_unavailable
        now = time.monotonic()
        reappeared = adapter_unavailable
        if not reappeared and now - last_adv_refresh < coordinator.slow_poll:
            return
        adapter_unavailable = False
        last_adv_refresh = now
        if reappeared:
            _LOGGER.debug(
                "OBD adapter %s reappeared in range — polling immediately", address
            )
        else:
            _LOGGER.debug(
                "OBD adapter %s detected (%s) — scheduling refresh", address, change
            )
        hass.async_create_task(coordinator.async_request_refresh())

    @callback
    def _on_adapter_unavailable(
        service_info: bluetooth.BluetoothServiceInfoBleak,
    ) -> None:
        """Handle the adapter leaving BLE range.

        Resets the advertisement throttle (so the next sighting polls right
        away) and parks the coordinator on the extra-slow interval so a
        pending timer cannot keep trying to connect — and wake the car — while
        it is away.
        """
        nonlocal adapter_unavailable
        if adapter_unavailable:
            return
        adapter_unavailable = True
        coordinator.update_interval = timedelta(seconds=coordinator.xs_poll)
        _LOGGER.debug(
            "OBD adapter %s unavailable; next advertisement will refresh", address
        )

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _on_adapter_detected,
            {"address": address},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    entry.async_on_unload(
        bluetooth.async_track_unavailable(
            hass,
            _on_adapter_unavailable,
            address,
            connectable=True,
        )
    )

    # Apply updated options immediately when the user clicks "Configure"
    async def _on_options_updated(
        hass: HomeAssistant | None, entry: ConfigEntry
    ) -> None:
        coordinator.options = entry.options

    entry.async_on_unload(entry.add_update_listener(_on_options_updated))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    domain_data = hass.data.get(DOMAIN, {})
    coordinator = domain_data.get(entry.entry_id)

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        if coordinator is not None:
            await coordinator.async_shutdown()
        domain_data.pop(entry.entry_id, None)
        if not domain_data:
            hass.data.pop(DOMAIN, None)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry (called after options change that requires restart)."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
