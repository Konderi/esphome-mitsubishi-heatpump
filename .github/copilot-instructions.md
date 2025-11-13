# Copilot instructions — esphome-mitsubishiheatpump

Purpose
- Help AI coding agents be productive quickly when editing this ESPHome external component.

Big picture
- This repository implements an ESPHome external component that talks to Mitsubishi heat pumps over the CN105 serial interface using the Arduino `HeatPump` library (https://github.com/SwiCago/HeatPump).
- Main runtime piece is a C++ `MitsubishiHeatPump` class (ESPHome `PollingComponent` + `climate::Climate`) in `components/mitsubishi_heatpump/espmhp.cpp`/`.h`.
- The Python code in `components/mitsubishi_heatpump/climate.py` is the ESPHome YAML-to-C++ generator: it maps YAML config to constructor calls, sets UART hardware, timeouts and registers the external `HeatPump` library.

Key files to read first
- `components/mitsubishi_heatpump/espmhp.h` — public API, macros (`USE_CALLBACKS`), constants (min/max temperature), and member variables (preferences, timeouts).
- `components/mitsubishi_heatpump/espmhp.cpp` — implementation: serial verification, mapping between ESPHome/HA modes and Mitsubishi modes, persistence, callbacks, and packet logging.
- `components/mitsubishi_heatpump/climate.py` — codegen: how YAML fields map to C++ calls (e.g. `hardware_uart`, `baud_rate`, `rx_pin`, `tx_pin`, `remote_*_timeout_minutes`). Also shows how `HeatPump` is added via `cg.add_library`.
- `components/mitsubishi_heatpump/*.py` (other helper files) — see `climate_old.py` for legacy behavior patterns.
- `README.md` — contains usage, upgrade notes (important), and YAML examples (including `external_components`).

Project-specific workflows & notes
- Build/test: this is an ESPHome external component. To compile, add this repo under `external_components` in your ESPHome YAML (see `README.md`), then run `esphome compile <your.yaml>` or `esphome run <your.yaml>` from your ESPHome config directory.
- Upgrading from older versions: follow the README steps exactly — remove old `libraries` and `includes` references, delete the old `src/esphome-mitsubishiheatpump` copy and clean build directories. Duplicate symbol/linker errors are common if those steps are skipped.

Conventions & patterns to preserve
- Hardware UART only: The C++ component uses an Arduino `HardwareSerial*` pointer (see `MitsubishiHeatPump::get_hw_serial_()` and constructor). Do NOT attempt to wire this through the ESPHome `uart` component — parity and direct HardwareSerial access are required.
- Serial/logging conflict: `verify_serial()` rejects using the same serial used by the global logger (ESP8266 users must set `logger: baud_rate: 0`). Check for `USE_LOGGER` conditional in code before changing serial behavior.
- Callbacks vs polling: `USE_CALLBACKS` macro (present in `espmhp.h`) toggles the HeatPump library callback wiring (settings/status/packet callbacks). Keep changes aware of both modes.
- Persistence: saved setpoints use `global_preferences->make_preference<uint8_t>(this->get_object_id_hash() + N)`. Values are saved as steps from `ESPMHP_MIN_TEMPERATURE` (see `save`/`load` in `espmhp.cpp`); preserve this compact storage format.
- Communication with HeatPump library: use `hp->connect(hw_serial, baud, rx_pin, tx_pin)` and `hp->update()` / `hp->sync()` as the code does. Changes to timing/polling must respect the 9 second maximum poll interval documented in comments.

Integration points & external deps
- External Arduino library: `SwiCago/HeatPump` — added at codegen via `cg.add_library(...)` in `climate.py` (pin to specific commit if needed).
- ESPHome features: `external_components`, `select` (vane selects), and `climate` traits. The Python generator registers `MitsubishiACSelect` for horizontal/vertical vane selects.

Developer editing guidance
- Small, focused C++ changes: edit `espmhp.cpp`/`.h`. Keep API/ABI stable — these classes are instantiated by ESPHome codegen.
- When adding new YAML options, update `climate.py` CONFIG_SCHEMA and `to_code()` mapping (follow existing patterns for `set_baud_rate`, `set_rx_pin`, `set_tx_pin`, and registering selects).
- Logging/diagnostics: use `ESP_LOGx(TAG, ...)` and the existing `log_packet` helper to inspect packets. Avoid enabling serial logging on ESP8266 when testing hardware UART.

Helpful snippets / examples (copy into PRs if needed)
- Hardware UART YAML example (from README):
  ```yaml
  external_components:
    - source: github://geoffdavis/esphome-mitsubishiheatpump

  climate:
    - platform: mitsubishi_heatpump
      hardware_uart: UART0
      baud_rate: 4800
  ```
- If supporting a new `supports:` trait, add to `climate.py` default lists and call `traits.add_supported_*` exactly as existing code does.

What to watch out for (common pitfalls)
- Duplicate definitions when upgrading: leftover `src/esphome-mitsubishiheatpump` or old `includes`/`libraries` entries will produce link errors; remove them and clean build files.
- ESP8266 serial conflict: logger enabled on same UART causes component failure — tests on ESP8266 should set `logger: baud_rate: 0` when using UART0.
- Poll interval >9000ms: HeatPump library will reconnect and break polling; `climate.py` enforces a max of 9000ms.

If anything is ambiguous or you'd like examples for a change (new YAML options, tests, or refactors), ask which file (C++ or Python generator) you want edited and I will update the instructions or produce a focused patch.

---
Files referenced: `components/mitsubishi_heatpump/espmhp.h`, `components/mitsubishi_heatpump/espmhp.cpp`, `components/mitsubishi_heatpump/climate.py`, `README.md`
