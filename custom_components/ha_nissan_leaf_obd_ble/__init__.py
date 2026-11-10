"""Nissan Leaf OBD BLE — Home Assistant custom integration (ha_nissan_leaf_obd_ble).

Sets up one coordinator per config entry (one per OBD adapter / Leaf),
registers a Bluetooth callback so new polls are triggered immediately when
the adapter comes back into range, and forwards entries to the sensor platform.
"""

from __future__ import annotations

import logging
import time

from bleak_retry_connector import get_device

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType

from .py_nissan_leaf_obd_ble import NissanLeafObdBleApiClient

from .const import DOMAIN, STARTUP_MESSAGE, VERSION
from .coordinator import NissanLeafCoordinator

__version__ = VERSION

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

    # Re-trigger a data refresh whenever the adapter reappears in BLE range.
    # The Bluetooth callback can fire repeatedly while the adapter is merely
    # advertising, so throttle it to the configured slow poll interval.  The
    # throttle is reset when the adapter becomes unavailable, ensuring the
    # first advertisement after the car returns still refreshes immediately.
    last_adv_refresh = 0.0
    adapter_unavailable = False

    @callback
    def _on_adapter_detected(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        nonlocal last_adv_refresh, adapter_unavailable
        now = time.monotonic()
        if not adapter_unavailable and now - last_adv_refresh < coordinator.slow_poll:
            return
        adapter_unavailable = False
        last_adv_refresh = now
        _LOGGER.debug(
            "OBD adapter %s detected (%s) — scheduling refresh", address, change
        )
        hass.async_create_task(coordinator.async_request_refresh())

    @callback
    def _on_adapter_unavailable(
        service_info: bluetooth.BluetoothServiceInfoBleak,
    ) -> None:
        """Reset the advertisement throttle when the adapter disappears."""
        nonlocal adapter_unavailable
        adapter_unavailable = True
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
