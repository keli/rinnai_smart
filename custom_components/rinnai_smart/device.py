"""Rinnai device object"""
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN, LOGGER, MANUFACTURER, OPERATION_COMMAND_MAP, CYCLE_MODE_MAP, CYCLE_MODE_COMMAND_MAP, OPERATION_MAP
)
from .rinnai_client import RinnaiClient


def _decode_hex_byte(value: str | None) -> int | None:
    """Decode Rinnai one-byte values, including two-byte little-endian variants."""
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if not isinstance(value, str):
        return None

    normalized = value.strip().upper()
    if normalized in ("ON", "TRUE"):
        return 1
    if normalized in ("OFF", "FALSE"):
        return 0
    if not normalized:
        return None

    try:
        if len(normalized) >= 4 and len(normalized) % 2 == 0:
            bytes_ = [normalized[i : i + 2] for i in range(0, len(normalized), 2)]
            if all(byte == "00" for byte in bytes_[1:]):
                return int(bytes_[0], 16)
        return int(normalized, 16)
    except ValueError:
        return None


def _encode_like_current_value(current_value: str | None, command_data: str) -> str:
    """Preserve devices that expect two-byte little-endian command payloads."""
    if not isinstance(current_value, str):
        return command_data
    normalized = current_value.strip().upper()
    if len(normalized) >= 4 and len(normalized) % 2 == 0:
        bytes_ = [normalized[i : i + 2] for i in range(0, len(normalized), 2)]
        if all(byte == "00" for byte in bytes_[1:]):
            return f"{int(command_data, 16):02X}" + "00" * (len(bytes_) - 1)
    return command_data


def _is_enabled(value: str | None) -> bool:
    return _decode_hex_byte(value) in (1, 0x31)


def _encode_switch_value(current_value: str | None, enabled: bool) -> str:
    if isinstance(current_value, str) and current_value.strip().upper() in ("30", "31"):
        return "31" if enabled else "30"
    return _encode_like_current_value(current_value, "01" if enabled else "00")

class RinnaiDeviceDataUpdateCoordinator(DataUpdateCoordinator):
    """Rinnai device object"""

    def __init__(
        self, hass: HomeAssistant, client: RinnaiClient, device: dict, options
    ):
        """Initialize the device"""
        self.hass: HomeAssistant = hass
        self._client: RinnaiClient = client
        self._device: dict = device
        self._manufacturer: str = MANUFACTURER
        self._device_information: Optional[Dict[str, Any]] | None = None
        self.options = options
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}-{device["id"]}",
            always_update=True
        )
    
    @property
    def id(self) -> str:
        """Return Rinnai thing name"""
        return self._device["id"]

    @property
    def device_name(self) -> str:
        """Return device name."""
        return self._device["name"]

    @property
    def manufacturer(self) -> str:
        """Return manufacturer for device"""
        return self._manufacturer

    @property
    def model(self) -> str:
        """Return model for device"""
        return self._device.get("model") or self._device.get("remark") or self._device["deviceType"][-3:]

    @property
    def target_temperature(self) -> float:
        """Return the current temperature in degrees F"""
        return _decode_hex_byte(self._device_information.get("hotWaterTempSetting"))

    @property
    def operation_mode(self) -> str:
        data = _decode_hex_byte(self._device_information.get("operationMode"))
        if data is None:
            return None
        data &= 0xBF
        if mode := OPERATION_MAP.get("%02X" % data):
            return mode
        if self.target_temperature is not None:
            return "开机"
        return None

    @property
    def is_heating(self) -> bool:
        return _is_enabled(self._device_information.get("burningState"))

    @property
    def is_on(self) -> bool:
        return self.target_temperature is not None
    
    @property
    def cycle_mode(self) -> str | None:
        data = _decode_hex_byte(self._device_information.get("cycleModeSetting"))
        return CYCLE_MODE_MAP.get(str(data), None)
    
    @property
    def is_cycle_reservation_on(self) -> bool:
        return _is_enabled(self._device_information.get("cycleReservationSetting"))
    
    @property
    def is_temporary_cycle_insulation_on(self) -> bool:
        return _is_enabled(self._device_information.get("temporaryCycleInsulationSetting"))
    
    @property
    def is_burn_state_on(self) -> bool:
        return _is_enabled(self._device_information.get("burningState"))

    @property
    def cycle_reservation_time(self) -> str:
        hours = []
        hour = 0
        for hex_str in self._device_information["cycleReservationTimeSetting"].split():
            hex_value = int(hex_str, 16)
            for i in range(8):
                if hex_value & (1 << i):
                    hours.append(str(hour))
                hour += 1
        return ','.join(hours)

    @property
    def raw_device_information(self) -> dict[str, Any]:
        return self._device_information or {}

    async def _async_setup(self) -> None:
        await self._client.subscribe(self._device["id"], self._update_device)

    async def async_turn_off(self):
        await self._publish("power", "00")
        await self.async_request_refresh()

    async def async_turn_on(self):
        await self._publish("power", "01")
        await self.async_request_refresh()

    async def async_set_temperature(self, temperature: int):
        previous_temperature = self.target_temperature
        if previous_temperature is None:
            LOGGER.error("Unable to decode current temperature: %s", self._device_information.get("hotWaterTempSetting"))
            return
        if temperature > previous_temperature:
            await self._client.publish(self._device, "hotWaterTempOperate", "01")
        elif temperature < previous_temperature:
            await self._client.publish(self._device, "hotWaterTempOperate", "00")

    async def async_set_operation_mode(self, operation_mode):
        command_id = OPERATION_COMMAND_MAP.get(operation_mode)
        if command_id:
            await self._client.publish(self._device, command_id, "01")

    async def async_set_cycle_mode(self, cycle_mode):
        await self._publish("cycleModeSetting", CYCLE_MODE_COMMAND_MAP[cycle_mode])
        await self.async_request_refresh()

    async def async_turn_on_cycle_reservation(self):
        await self._publish_switch("cycleReservationSetting", True)
        await self.async_request_refresh()

    async def async_turn_off_cycle_reservation(self):
        await self._publish_switch("cycleReservationSetting", False)
        await self.async_request_refresh()

    async def async_turn_on_temporary_cycle_insulation(self):
        await self._publish_switch("temporaryCycleInsulationSetting", True)
        await self.async_request_refresh()

    async def async_turn_off_temporary_cycle_insulation(self):
        await self._publish_switch("temporaryCycleInsulationSetting", False)
        await self.async_request_refresh()

    async def async_set_cycle_reservation_time(self, value: str):
        hours = [0, 0, 0]
        for hour in value.split(","):
            hour = int(hour, 10)
            index = int(hour / 8)
            bit = hour % 8
            hours[index] |= (1<<bit)
        data = " ".join(["%02X" % hour for hour in hours])
        await self._client.publish(self._device, "cycleReservationTimeSetting", data)
        await self.async_request_refresh()

    async def _async_update_data(self):
        device_information = await self._client.refresh_device_information(self.id)
        if device_information is not None:
            self._device_information = device_information
            LOGGER.debug("Rinnai device data refreshed by HTTP: %s", self._device_information)
        return self._device_information

    async def _publish(self, command_id: str, command_data: str):
        current_value = None
        if self._device_information:
            current_value = self._device_information.get(command_id)
        data = _encode_like_current_value(current_value, command_data)
        await self._client.publish(self._device, command_id, data)

    async def _publish_switch(self, command_id: str, enabled: bool):
        current_value = None
        if self._device_information:
            current_value = self._device_information.get(command_id)
        data = _encode_switch_value(current_value, enabled)
        await self._client.publish(self._device, command_id, data)

    async def _update_device(self, device_info: dict) -> None:
        """Update the device information from the API"""
        self._device_information = device_info
        self.async_update_listeners()

        LOGGER.debug("Rinnai device data: %s", self._device_information)
