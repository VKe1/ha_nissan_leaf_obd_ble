# Nissan Leaf OBD BLE — Home Assistant Custom Integration

A Home Assistant custom integration for monitoring Nissan Leaf battery and
vehicle data via a Bluetooth Low Energy ELM327 OBD-II adapter (e.g. LeLink2).

This integration is a fork of
[hucknz/ha_nissan_leaf_obd_ble](https://github.com/hucknz/ha_nissan_leaf_obd_ble),
which in turn builds on
[pbutterworth/nissan-leaf-obd-ble](https://github.com/pbutterworth/nissan-leaf-obd-ble).
It is maintained by [@VKe1](https://github.com/VKe1).

### What this fork adds

| Feature | Upstream | This fork |
|---|---|---|
| OBD adapter selection | Manual MAC entry | **Dropdown of discovered adapters** |
| Generation support | Manual overrides.yaml | **Built-in per-generation profiles** |
| ZE0/AZE0 odometer | Active query (unreliable) | **Passive CAN broadcast (0x5C5)** |
| ZE0/AZE0 battery decoder | ZE1 offsets (incorrect) | **Correct ZE0 byte offsets** |
| Sensor list | Fixed (all sensors always created) | **Trimmed to generation-supported set** |
| Data persistence | Lost on HA restart | **Persisted to HA storage** |
| IOS-Vlink BLE adapter | Not recognised | **Supported (`IOS-Vlink` local name)** |
| Manual refresh | — | **Diagnostic "Refresh" button** |
| Startup with car away | Entities unavailable | **Cached values used immediately** |
| Reconnect behaviour | Repeated polling while away | **Advertisement-triggered refresh, throttled** |
| Polling defaults | 10 s fast poll (relay wear) | **Relay-friendly intervals + poll on arrival** |

---

## Supported hardware

| Item | Notes |
|---|---|
| LeLink2 ELM327 BLE OBD-II adapter | Primary tested hardware |
| IOS-Vlink ELM327 BLE OBD-II adapter | Supported (advertises as `IOS-Vlink`) |
| Any ELM327 BLE OBD-II adapter advertising as `OBDBLE` | Should work; UUIDs configurable |
| ESPHome Bluetooth Proxy (e.g. GL-iNet GL-S10) | Recommended for garage setups |

## Supported vehicles

| Generation | Years | Notes |
|---|---|---|
| ZE0 | 2010–2017 | Odometer via passive CAN broadcast; ZE0 battery decoder |
| AZE0 | 2017–2018 | Same as ZE0 profile |
| ZE1 | 2018+ | Active KWP2000 odometer; includes e-Pedal sensor |
| Auto | All | All sensors enabled; uses ZE1 decoders (ZE0/AZE0 owners should pick their generation for accurate battery data) |

---

## Prerequisites

The OBD/ELM327 library (derived from
[pbutterworth/py-nissan-leaf-obd-ble](https://github.com/pbutterworth/py-nissan-leaf-obd-ble))
is bundled inside the integration as `py_nissan_leaf_obd_ble/`, so no separate
package install is needed.  The only external requirement is
`bleak-retry-connector`, which Home Assistant installs automatically, along
with the built-in `bluetooth_adapters` dependency.

---

## Installation

### Option 1 — HACS (Custom Repository)

1. Open HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/VKe1/ha_nissan_leaf_obd_ble` with category **Integration**.
3. Find *Nissan Leaf OBD BLE* and click **Download**.
4. Restart Home Assistant.

### Option 2 — Manual

1. Copy the `custom_components/ha_nissan_leaf_obd_ble/` folder into your HA
   `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Setup

1. Plug the OBD adapter into the Nissan Leaf's OBD-II port and turn on the
   ignition (or accessory mode).
2. In Home Assistant: **Settings → Devices & Services → Add Integration →
   Nissan Leaf OBD BLE**.
3. **Step 1 — OBD adapter**: Select your adapter from the dropdown.  If it
   doesn't appear, check that it's powered and within BLE range.
4. **Step 2 — Leaf generation**: Select your Leaf platform.

   | Label | Choose if… |
   |---|---|
   | ZE0 — 2010–2017 | Your Leaf is a pre-facelift (original) model |
   | AZE0 — 2017–2018 | Your Leaf is the 2017 or 2018 refresh |
   | ZE1 — 2018+ | Your Leaf is the second-generation (40 kWh / 62 kWh) |
   | Auto | You're unsure — all sensors enabled, ZE1 decoders used |

5. **Step 3 — Battery size**: Select your battery size (24, 30, 40 or 62 kWh).
   This is used to calculate state of health.
6. HA will create the device and all generation-appropriate sensor entities.
   BLE UUIDs use the LeLink2 defaults and can be changed later under
   **Configure**.

---

## Sensors

Entity IDs are derived from the sensor name prefixed with
`Nissan Leaf OBD BLE`, e.g. `sensor.nissan_leaf_obd_ble_state_of_charge`.

### All generations

| Sensor name | Unit | Description |
|---|---|---|
| State of charge | % | Battery charge level |
| State of health | % | Calculated from capacity and the selected battery size |
| HV battery health index | % | Health index (Hx) reported by the battery controller |
| HV battery capacity | Ah | Battery capacity |
| HV battery voltage | V | HV battery pack voltage |
| HV battery current 1 / 2 | A | Pack current (two channels) |
| Odometer | km | Total distance travelled |
| Range remaining | km | Estimated remaining range |
| Vehicle speed | km/h | Vehicle speed |
| Traction motor power | W | Traction motor power |
| Gear position | — | Park / Reverse / Neutral / Drive / Eco |
| Charging mode | — | Charge mode |
| Plug state | — | Plug state |
| Motor RPM | RPM | Motor speed |
| 12V battery voltage / current | V / A | 12V auxiliary battery |
| Number of quick charges | — | Quick (CHAdeMO) charge count |
| Number of L1/L2 charges | — | L1/L2 charge count |
| AC system power | W | Climate system power |
| AC on | — | Climate on/off |
| Estimated AC power | W | Estimated climate draw |
| Estimated PTC power | W | Estimated PTC heater draw |
| Auxiliary equipment power | W | Auxiliary equipment power |
| On-board charger output power | W | On-board charger output |
| ECO mode | — | ECO mode active |
| Rear heater | — | Rear heater active |
| Power switch | — | Power switch status |
| Tyre pressure (FR / FL / RR / RL) | kPa | Four tyre pressure sensors |

### ZE0 / AZE0 only

| Sensor name | Unit | Description |
|---|---|---|
| Battery temperature | °C | Battery temperature |

### ZE1 and Auto only

| Sensor name | Description |
|---|---|
| e-Pedal mode | e-Pedal mode active |

---

## Notes on ZE0/AZE0 battery data accuracy

The battery decoder byte offsets for ZE0/AZE0 (`state_of_charge`,
`hv_battery_health`, `hv_battery_Ah`) are based on community research and
tested on a 2018 AZE0 with a 30 kWh battery.  They have not been exhaustively
verified across all ZE0 and AZE0 vehicles.  If you notice incorrect battery
figures, please open an issue with your raw LBC data.

---

## Configuration options

After setup, click **Configure** on the integration card to adjust:

| Option | Default | Description |
|---|---|---|
| Battery size | 30 kWh (79.48 Ah) | Nominal capacity in Ah, used to calculate state of health |
| Fast poll interval | 300 s | Polling rate when the car is responding (ignition on) |
| Slow poll interval | 1800 s | Polling rate when in range but not responding; also the advertisement-refresh throttle |
| Extra-slow poll interval | 3600 s | Fallback timer when out of BLE range (no connection attempted) |
| BLE service UUID | `0000ffe0-…` | GATT service UUID for the adapter |
| BLE read characteristic UUID | `0000ffe1-…` | Read characteristic UUID |
| BLE write characteristic UUID | `0000ffe1-…` | Write characteristic UUID |

---

## Polling intervals and the car's relays

Every time Home Assistant connects to the OBD adapter, the Leaf wakes its
OBD/CAN bus and the relays can be heard clicking.  This is a property of the
car, not of this integration, and it cannot be avoided while polling.  It is
harmless in itself, but two things follow:

- every actuation adds a little wear to the relays,
- every wake-up draws a small amount of power from the 12 V battery.

Polling every 10 s while the car sits parked therefore means thousands of
relay clicks a day for data that does not change.  This fork therefore ships
with conservative defaults:

| Scenario | Default | Notes |
|---|---|---|
| Car responding (ignition on) | 300 s | Trip statistics only need the readings at the start and end of a drive |
| In range but not responding | 1800 s | Car parked; also the throttle for advertisement-driven refreshes |
| Out of BLE range | 3600 s | No connection is attempted; only a fallback timer |

The intervals can be changed at any time in **Configure**.  Sensible
trade-offs:

| Goal | Fast | Slow | Extra-slow |
|---|---|---|---|
| Default in this fork | 300 | 1800 | 3600 |
| Maximum relay life (trip-level data only) | 1800 | 3600 | 7200 |
| Near-live readings while driving (more wear) | 60 | 600 | 3600 |

The minimum accepted value is **60 s**; shorter values are clamped, because
anything faster only wears the relays without adding useful information.

### Polling when you arrive home

You do not need to shorten the intervals for this.  The integration listens to
Bluetooth advertisements and:

1. notices when the adapter disappears (car driven away, or the dongle loses
   power with the ignition),
2. polls **immediately** the first time the adapter is seen again — even if
   the slow interval is 1800 s or more,
3. while the adapter keeps advertising in place (parked at home), limits
   advertisement-driven polls to the slow interval, so the relays are not
   clicked for every advertisement.

If you want an additional guarantee (for example to poll the moment your phone
connects to home Wi-Fi, before Bluetooth notices the car), add an automation
that presses the refresh button:

```yaml
automation:
  - alias: "Leaf: poll on arrival"
    triggers:
      - trigger: state
        entity_id: person.me
        to: home
    actions:
      - action: button.press
        target:
          entity_id: button.nissan_leaf_obd_ble_refresh
```

Check the actual entity ID under *Settings → Devices & services → Entities*.
A refresh still requires the adapter to be in range; pressing the button while
the car is away only returns the cached values.

---

## Data persistence

Sensor values are saved to HA's `.storage/` directory after each successful
poll.  After a Home Assistant restart, all sensors immediately display their
last known values — no need to drive the car home first.

If the first poll after startup fails (for example because the car is away or
the adapter is not yet reachable), the integration starts with the cached
values instead of failing setup.  The next successful poll replaces them with
live data.

## Refresh button

Each configured adapter gets a diagnostic **Nissan Leaf OBD BLE Refresh**
button.  Pressing it triggers an immediate poll without waiting for the next
scheduled interval — useful after turning the car on, before an automation
runs, or from an arrival automation (see *Polling when you arrive home*
above).  The integration already reacts to the adapter reappearing in range,
so the button is an extra manual safety net rather than a requirement.

## Known limitations

**State of charge may freeze while charging**
: The battery controller (`lbc`) can return no usable value (or `0xFFFFFF`)
during some charging sessions, while other values such as on-board charger
output power keep updating.  The integration intentionally keeps the last
known state of charge rather than replacing it with an invalid value, so the
SoC sensor may appear frozen until the next valid reading.  This is a decoder
limitation, not a connectivity problem.

**Relays click on every poll**
: Expected Leaf behaviour, not a fault.  The car cannot be queried without
waking its OBD bus.  Increase the poll intervals (see *Polling intervals and
the car's relays*) if the clicking is annoying or you want to minimise relay
wear.

**Derived virtual sensors are not part of the integration**
: Virtual state of charge, consumption estimates, and similar calculated
values belong in Home Assistant templates (or the Energy dashboard) rather
than in this integration.  Keeping them in templates makes them easy to tune
without changing the integration.

---

## Troubleshooting

**No adapters appear in the dropdown**
: Ensure the OBD adapter is plugged in, the ignition is on, and the adapter
is within Bluetooth range of your HA host or a Bluetooth proxy.  Check
*Settings → Devices & Services → Bluetooth* to verify HA can see the adapter.

**Sensors stay at last known value indefinitely**
: This is the persistence feature working as designed.  Values update the
next time the car is in range and the ignition is on.

**Relays click every few minutes while the car is parked at home**
: The adapter is in range and is being polled at the slow interval.  Raise the
slow poll interval, or let the dongle power down with the ignition so the
integration falls back to the extra-slow interval and stops connecting.

**Incorrect battery / SoC values on a ZE0 or AZE0**
: Ensure you selected the correct generation during setup.  If you used
*Auto*, re-add the integration and select *ZE0* or *AZE0* explicitly.

**SoC is stuck at the same value while charging**
: See *Known limitations* above.  The battery controller occasionally reports
no usable SoC during charging; the integration keeps the last valid value
until a new one arrives.

**Refresh button does nothing**
: A refresh still requires the adapter to be reachable over Bluetooth.  Check
the standard *Bluetooth* integration and the debug log; the button triggers a
poll but cannot wake an adapter that is out of range.

**Enable debug logging**
```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.ha_nissan_leaf_obd_ble: debug
```

---

## Credits

- [pbutterworth/nissan-leaf-obd-ble](https://github.com/pbutterworth/nissan-leaf-obd-ble) — original integration
- [hucknz/ha_nissan_leaf_obd_ble](https://github.com/hucknz/ha_nissan_leaf_obd_ble) — upstream fork this repository is based on
- [pbutterworth/py-nissan-leaf-obd-ble](https://github.com/pbutterworth/py-nissan-leaf-obd-ble) — upstream Python library, bundled here in modified form
- [@Jopand](https://github.com/Jopand) — IOS-Vlink adapter testing and contributions
- [HA Community thread](https://community.home-assistant.io/t/custom-component-nissan-leaf-via-lelink-2-elm327-ble/561961)

## License

GPL-2.0-or-later (inherited from python-OBD lineage).
