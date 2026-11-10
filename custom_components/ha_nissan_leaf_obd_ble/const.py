"""Constants for Nissan Leaf OBD BLE (ha_nissan_leaf_obd_ble)."""

NAME = "Nissan Leaf OBD BLE"
DOMAIN = "ha_nissan_leaf_obd_ble"
VERSION = "1.2.0"

ISSUE_URL = "https://github.com/VKe1/ha_nissan_leaf_obd_ble/issues"

# Configuration keys — stored in config entry DATA (require re-adding to change)
CONF_GENERATION = "generation"

# Configuration keys — stored in config entry OPTIONS (changeable via Configure)
CONF_SERVICE_UUID = "service_uuid"
CONF_CHARACTERISTIC_UUID_READ = "characteristic_uuid_read"
CONF_CHARACTERISTIC_UUID_WRITE = "characteristic_uuid_write"
CONF_NOMINAL_AH = "nominal_ah"

# Default BLE UUIDs (LeLink2 / OBDBLE dongle)
DEFAULT_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
DEFAULT_CHARACTERISTIC_UUID_READ = "0000ffe1-0000-1000-8000-00805f9b34fb"
DEFAULT_CHARACTERISTIC_UUID_WRITE = "0000ffe1-0000-1000-8000-00805f9b34fb"

# BLE local names to search for when scanning for adapters
BLE_LOCAL_NAMES = {"OBDBLE", "IOS-Vlink"}

# Generation identifiers
GENERATION_AUTO = "auto"
GENERATION_ZE0 = "ze0"
GENERATION_AZE0 = "aze0"
GENERATION_ZE1 = "ze1"

# Human-readable labels for UI display
GENERATION_OPTIONS: dict[str, str] = {
    GENERATION_ZE0: "ZE0 — 2010–2017 Nissan Leaf (uses passive CAN odometer)",
    GENERATION_AZE0: "AZE0 — 2017–2018 Nissan Leaf (uses passive CAN odometer)",
    GENERATION_ZE1: "ZE1 — 2018+ Nissan Leaf",
    GENERATION_AUTO: "Auto — all generations (recommended if unsure)",
}

# Battery nominal Ah capacity by size (used to calculate State of Health)
# These are the approximate maximum usable capacities for each battery size.
BATTERY_NOMINAL_AH: dict[int, float] = {
    24: 60.6,
    30: 79.48,
    40: 105.6,
    62: 167.6,
}

# Default nominal Ah if user doesn't specify (30 kWh is most common)
DEFAULT_NOMINAL_AH = 79.48

# Default polling intervals (seconds).
#
# Every poll connects to the OBD adapter, which wakes the car's OBD/CAN bus
# and makes the Leaf's relays click.  That is normal behaviour, but it is not
# free: each actuation adds wear and each wake-up drains the 12 V battery a
# little.  Polling every 10 s while the car sits on the driveway means
# thousands of relay clicks per day for data nobody needs.
#
# The defaults below are therefore deliberately conservative.  Trip
# consumption is calculated from two readings (start/end of a drive), so a
# few minutes of resolution is plenty.  The integration also polls
# immediately when the adapter reappears in Bluetooth range, so a long
# interval does not delay the first reading after arriving home.
DEFAULT_FAST_POLL = 300
DEFAULT_SLOW_POLL = 1800
DEFAULT_XS_POLL = 3600
DEFAULT_FETCH_TIMEOUT = 90

# Hard floor for user-configured poll intervals.  Anything shorter wakes the
# OBD bus far more often than the car's data changes, and only serves to wear
# the relays.  Values below this are clamped by the coordinator.
MIN_POLL_INTERVAL = 60

# Storage — persists last-known sensor values across HA restarts
STORAGE_KEY = f"{DOMAIN}.sensor_cache"
STORAGE_VERSION = 1

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
Custom integration — report issues at: {ISSUE_URL}
-------------------------------------------------------------------
"""
