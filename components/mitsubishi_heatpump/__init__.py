# SPDX-License-Identifier: MIT
# Mitsubishi HeatPump custom component
# Updated for ESPHome 2025.10+:
# - Uses climate.climate_schema(...) instead of deprecated climate.CLIMATE_SCHEMA
# - Inherits from climate.Climate (exposed via components once we avoid name shadowing)
# - Async to_code (no @coroutine / yield)
# - UART mapping, vane selects, and traits preserved

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import climate, select
from esphome.components.logger import HARDWARE_UART_TO_SERIAL
from esphome.const import (
    CONF_ID,
    CONF_HARDWARE_UART,
    CONF_BAUD_RATE,
    CONF_RX_PIN,
    CONF_TX_PIN,
    CONF_UPDATE_INTERVAL,
    CONF_MODE,
    CONF_FAN_MODE,
    CONF_SWING_MODE,
)
from esphome.core import CORE

AUTO_LOAD = ["climate", "select"]

CONF_SUPPORTS = "supports"
CONF_HORIZONTAL_SWING_SELECT = "horizontal_vane_select"
CONF_VERTICAL_SWING_SELECT = "vertical_vane_select"

DEFAULT_CLIMATE_MODES = ["HEAT_COOL", "COOL", "HEAT", "DRY", "FAN_ONLY"]
DEFAULT_FAN_MODES = ["AUTO", "DIFFUSE", "LOW", "MEDIUM", "MIDDLE", "HIGH"]
DEFAULT_SWING_MODES = ["OFF", "VERTICAL"]

HORIZONTAL_SWING_OPTIONS = [
    "auto",
    "swing",
    "left",
    "left_center",
    "center",
    "right_center",
    "right",
]
VERTICAL_SWING_OPTIONS = ["swing", "auto", "up", "up_center", "center", "down_center", "down"]

# Remote temperature timeout configuration
CONF_REMOTE_OPERATING_TIMEOUT = "remote_temperature_operating_timeout_minutes"
CONF_REMOTE_IDLE_TIMEOUT = "remote_temperature_idle_timeout_minutes"
CONF_REMOTE_PING_TIMEOUT = "remote_temperature_ping_timeout_minutes"

# Bind to C++ classes (now safe because this file is __init__.py, not climate.py)
MitsubishiHeatPump = cg.global_ns.class_("MitsubishiHeatPump", climate.Climate, cg.PollingComponent)
MitsubishiACSelect = cg.global_ns.class_("MitsubishiACSelect", select.Select, cg.Component)


def valid_uart(uart):
    if CORE.is_esp8266:
        uarts = ["UART0"]  # UART1 is TX-only on ESP8266
    elif CORE.is_esp32:
        uarts = ["UART0", "UART1", "UART2"]
    else:
        raise NotImplementedError("Unsupported platform")
    return cv.one_of(*uarts, upper=True)(uart)


SELECT_SCHEMA = select._SELECT_SCHEMA.extend(
    {cv.GenerateID(CONF_ID): cv.declare_id(MitsubishiACSelect)}
)

CONFIG_SCHEMA = climate.climate_schema(
    {
        cv.GenerateID(): cv.declare_id(MitsubishiHeatPump),
        cv.Optional(CONF_HARDWARE_UART, default="UART0"): valid_uart,
        cv.Optional(CONF_BAUD_RATE): cv.positive_int,
        cv.Optional(CONF_REMOTE_OPERATING_TIMEOUT): cv.positive_int,
        cv.Optional(CONF_REMOTE_IDLE_TIMEOUT): cv.positive_int,
        cv.Optional(CONF_REMOTE_PING_TIMEOUT): cv.positive_int,
        cv.Optional(CONF_RX_PIN): cv.positive_int,
        cv.Optional(CONF_TX_PIN): cv.positive_int,
        # If polling interval > 9s, HeatPump library reconnects and may skip follow-up request.
        cv.Optional(CONF_UPDATE_INTERVAL, default="500ms"): cv.All(
            cv.update_interval, cv.Range(max=cv.TimePeriod(milliseconds=9000))
        ),
        # Adds selects for vertical and horizontal vane positions
        cv.Optional(CONF_HORIZONTAL_SWING_SELECT): SELECT_SCHEMA,
        cv.Optional(CONF_VERTICAL_SWING_SELECT): SELECT_SCHEMA,
        # Optionally override the supported ClimateTraits.
        cv.Optional(CONF_SUPPORTS, default={}): cv.Schema(
            {
                cv.Optional(CONF_MODE, default=DEFAULT_CLIMATE_MODES):
                    cv.ensure_list(climate.validate_climate_mode),
                cv.Optional(CONF_FAN_MODE, default=DEFAULT_FAN_MODES):
                    cv.ensure_list(climate.validate_climate_fan_mode),
                cv.Optional(CONF_SWING_MODE, default=DEFAULT_SWING_MODES):
                    cv.ensure_list(climate.validate_climate_swing_mode),
            }
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    # Map selected UART to hardware serial symbol for the current platform
    platform_key = "esp8266" if CORE.is_esp8266 else "esp32" if CORE.is_esp32 else None
    if platform_key is None:
        raise cv.Invalid("Unsupported platform for MitsubishiHeatPump")

    serial_sym = HARDWARE_UART_TO_SERIAL[platform_key][config[CONF_HARDWARE_UART]]
    var = cg.new_Pvariable(config[CONF_ID], cg.RawExpression(f"&{serial_sym}"))

    if CONF_BAUD_RATE in config:
        cg.add(var.set_baud_rate(config[CONF_BAUD_RATE]))

    if CONF_RX_PIN in config:
        cg.add(var.set_rx_pin(config[CONF_RX_PIN]))

    if CONF_TX_PIN in config:
        cg.add(var.set_tx_pin(config[CONF_TX_PIN]))

    if CONF_REMOTE_OPERATING_TIMEOUT in config:
        cg.add(var.set_remote_operating_timeout_minutes(config[CONF_REMOTE_OPERATING_TIMEOUT]))

    if CONF_REMOTE_IDLE_TIMEOUT in config:
        cg.add(var.set_remote_idle_timeout_minutes(config[CONF_REMOTE_IDLE_TIMEOUT]))

    if CONF_REMOTE_PING_TIMEOUT in config:
        cg.add(var.set_remote_ping_timeout_minutes(config[CONF_REMOTE_PING_TIMEOUT]))

    # Configure supported traits
    supports = config.get(CONF_SUPPORTS, {})
    traits = var.config_traits()

    for mode in supports.get(CONF_MODE, []):
        if mode == "OFF":
            continue
        cg.add(traits.add_supported_mode(climate.CLIMATE_MODES[mode]))

    for mode in supports.get(CONF_FAN_MODE, []):
        cg.add(traits.add_supported_fan_mode(climate.CLIMATE_FAN_MODES[mode]))

    for mode in supports.get(CONF_SWING_MODE, []):
        cg.add(traits.add_supported_swing_mode(climate.CLIMATE_SWING_MODES[mode]))

    # Optional vane position selects
    if CONF_HORIZONTAL_SWING_SELECT in config:
        conf = config[CONF_HORIZONTAL_SWING_SELECT]
        swing_select = await select.new_select(conf, options=HORIZONTAL_SWING_OPTIONS)
        await cg.register_component(swing_select, conf)
        cg.add(var.set_horizontal_vane_select(swing_select))

    if CONF_VERTICAL_SWING_SELECT in config:
        conf = config[CONF_VERTICAL_SWING_SELECT]
        swing_select = await select.new_select(conf, options=VERTICAL_SWING_OPTIONS)
        await cg.register_component(swing_select, conf)
        cg.add(var.set_vertical_vane_select(swing_select))

    # Register main component and climate
    await cg.register_component(var, config)
    await climate.register_climate(var, config)

    # Pin HeatPump library to known-good commit
    cg.add_library(
        name="HeatPump",
        repository="https://github.com/SwiCago/HeatPump#5d1e146771d2f458907a855bf9d5d4b9bf5ff033",
        version=None,
    )
