# Contributing

Thank you for contributing — this document explains the recommended developer workflow, coding conventions, build & test steps, and a PR checklist specific to this repository.

1) Branching & commits
- Branch from `main` and use short, descriptive branch names: `fix/logger-compat`, `feat/new-yaml-option`, `chore/docs`.
- Make small, focused commits. Use imperative commit messages, e.g.: `Fix: avoid logger internals in verify_serial()`.
- Sign commits if your org requires it; otherwise include a clear description and a related issue/PR number if relevant.

2) Build & test locally (ESPHome)
- Use the ESPHome CLI or the ESPHome add-on in Home Assistant.
- From your ESPHome config directory run:
  ```bash
  esphome clean mitsu_ilp.yaml
  esphome compile mitsu_ilp.yaml
  ```
- On Home Assistant: ESPHome add-on → node page → three-dot menu → "Clean build files" → "Compile".
- For iterative dev, push changes to a GitHub branch and reference it from `external_components` in your YAML (Home Assistant cannot access arbitrary local Windows paths):
  ```yaml
  external_components:
    - source: github://<your-user>/esphome-mitsubishi-heatpump@my-branch
  ```

3) Code conventions & repository patterns
- C++ changes should be small and preserve the public API/ABI. `MitsubishiHeatPump` is instantiated by ESPHome codegen; avoid renaming constructor signatures or public methods without coordination.
- This component uses `HardwareSerial*` directly; do not try to route comms through the ESPHome `uart` component — parity and direct hardware access are required.
- Preserve persistence format: setpoints use `global_preferences->make_preference<uint8_t>(...)` and are stored as steps from `ESPMHP_MIN_TEMPERATURE`.
- Do not rely on internal ESPHome logger APIs. Use `ESP_LOGx(TAG, ...)`. If you must inspect logger internals, guard with preprocessor checks and document supported ESPHome versions.
- Respect `USE_CALLBACKS` and keep both polling and callback code paths working where relevant.
- Keep `update_interval` <= 9000 ms — the underlying `HeatPump` library reconnects if interval exceeds 9s.

4) Adding YAML options
- Update `components/mitsubishi_heatpump/climate.py` CONFIG_SCHEMA and `to_code()` mapping. Follow existing patterns for `baud_rate`, `rx_pin`, `tx_pin`, and remote timeouts.
- When adding dependencies with `cg.add_library(...)`, prefer pinning to a commit hash and document why.

5) Testing & QA
- Verify the component compiles cleanly with the pinned ESPHome version(s) you support.
- Smoke tests: compile, and if possible flash to a development ESP32/ESP8266 board and verify basic operations (connect, mode change, temperature set, vane control).
- For Home Assistant users: ensure `logger: baud_rate: 0` is configured on ESP8266 when using UART0.

6) Pull Request checklist (fill in on PR description)
- [ ] Title describes the change and references an issue (if applicable).
- [ ] Changes are focused and limited in scope (one logical change per PR).
- [ ] Code compiles locally with `esphome compile` (attach logs if you can't run locally).
- [ ] README or `copilot-instructions.md` updated when public behaviors or configuration changes.
- [ ] Tests or manual verification steps included in PR description.

7) Emergency / quick fixes
- If Home Assistant must build immediately and you can't push to GitHub, you may temporarily edit the cached copy under `/config/.esphome/build/<node>/src/esphome/components/mitsubishi_heatpump/` on the HA host and rebuild. This is ephemeral — upstream rebuilds will overwrite it.

8) Contact & follow-up
- When in doubt, open an issue describing the problem, the ESPHome version used, target board (ESP32/ESP8266), and the steps to reproduce.

Thank you — your contribution helps keep this component stable and usable for others.
