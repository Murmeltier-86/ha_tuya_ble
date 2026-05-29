"""Lawn mower entities for Tuya BLE."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)

MOWER_STATUS_OPTIONS = [
    "STANDBY",
    "CHARGING",
    "MOWING",
    "PAUSED",
    "PARK",
    "UPDATA",
    "FIXED_MOWING",
    "ERROR",
    "SELF_TEST",
    "CHARGING_WITH_TASK_SUSPEND",
    "EMERGENCY",
    "LOCKED",
]

MOWER_COMMAND_OPTIONS = [
    "PauseWork",
    "CancelWork",
    "ContinueWork",
    "StartMowing",
    "StartFixedMowing",
    "StartReturnStation",
]

STATUS_TO_ACTIVITY = {
    "STANDBY": LawnMowerActivity.DOCKED,
    "CHARGING": LawnMowerActivity.DOCKED,
    "MOWING": LawnMowerActivity.MOWING,
    "PAUSED": LawnMowerActivity.PAUSED,
    "PARK": LawnMowerActivity.RETURNING,
    "UPDATA": LawnMowerActivity.DOCKED,
    "FIXED_MOWING": LawnMowerActivity.MOWING,
    "ERROR": LawnMowerActivity.ERROR,
    "SELF_TEST": LawnMowerActivity.DOCKED,
    "CHARGING_WITH_TASK_SUSPEND": LawnMowerActivity.DOCKED,
    "EMERGENCY": LawnMowerActivity.ERROR,
    "LOCKED": LawnMowerActivity.DOCKED,
}


@dataclass
class TuyaBLELawnMowerMapping:
    status_dp_id: int
    switch_dp_id: int
    mode_dp_id: int
    command_dp_id: int
    status_options: list[str]
    command_options: list[str]


@dataclass
class TuyaBLECategoryLawnMowerMapping:
    products: dict[str, TuyaBLELawnMowerMapping]


mapping: dict[str, TuyaBLECategoryLawnMowerMapping] = {
    "gcj": TuyaBLECategoryLawnMowerMapping(
        products={
            "7yr5iwga": TuyaBLELawnMowerMapping(
                status_dp_id=101,
                switch_dp_id=2,
                mode_dp_id=3,
                command_dp_id=115,
                status_options=MOWER_STATUS_OPTIONS,
                command_options=MOWER_COMMAND_OPTIONS,
            ),
        },
    ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> TuyaBLELawnMowerMapping | None:
    category = mapping.get(device.category)
    if category is None:
        return None
    return category.products.get(device.product_id)


class TuyaBLELawnMower(TuyaBLEEntity, LawnMowerEntity):
    """Representation of a Tuya BLE lawn mower."""

    _attr_supported_features = (
        LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.DOCK
    )

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mower_mapping: TuyaBLELawnMowerMapping,
    ) -> None:
        super().__init__(
            hass,
            coordinator,
            device,
            product,
            EntityDescription(key="lawn_mower"),
        )
        self._mapping = mower_mapping

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return the current activity."""
        datapoint = self._device.datapoints[self._mapping.status_dp_id]
        if not datapoint:
            return None

        value = datapoint.value
        if isinstance(value, int):
            if value < 0 or value >= len(self._mapping.status_options):
                return None
            value = self._mapping.status_options[value]

        return STATUS_TO_ACTIVITY.get(value)

    def _send_mower_command(self, command: str) -> None:
        """Send a mower command enum."""
        if command not in self._mapping.command_options:
            _LOGGER.debug("%s: unknown mower command %s", self._device.address, command)
            return
        value = self._mapping.command_options.index(command)
        datapoint = self._device.datapoints.get_or_create(
            self._mapping.command_dp_id,
            TuyaBLEDataPointType.DT_ENUM,
            value,
        )
        self._hass.create_task(datapoint.set_value(value))

    def _set_switch_go(self, value: bool) -> None:
        """Set the Tuya switch_go function datapoint."""
        datapoint = self._device.datapoints.get_or_create(
            self._mapping.switch_dp_id,
            TuyaBLEDataPointType.DT_BOOL,
            value,
        )
        self._hass.create_task(datapoint.set_value(value))

    async def _async_set_mode_and_switch(
        self, mode_value: int, switch_value: bool
    ) -> None:
        """Set Tuya mode and switch_go together over local BLE."""
        self._device.datapoints.begin_update()
        try:
            mode = self._device.datapoints.get_or_create(
                self._mapping.mode_dp_id,
                TuyaBLEDataPointType.DT_ENUM,
                mode_value,
            )
            switch_go = self._device.datapoints.get_or_create(
                self._mapping.switch_dp_id,
                TuyaBLEDataPointType.DT_BOOL,
                switch_value,
            )
            await mode.set_value(mode_value)
            await switch_go.set_value(switch_value)
        finally:
            await self._device.datapoints.end_update(force_connect=True)

    def start_mowing(self) -> None:
        """Start mowing via Tuya mode=smart and switch_go BLE functions."""
        self._hass.create_task(self._async_set_mode_and_switch(2, True))

    def pause(self) -> None:
        """Pause mowing via Tuya mode=standby and switch_go BLE functions."""
        self._hass.create_task(self._async_set_mode_and_switch(0, False))

    def dock(self) -> None:
        """Return to dock via Tuya mode=goto_charge and switch_go BLE functions."""
        self._hass.create_task(self._async_set_mode_and_switch(4, True))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya BLE lawn mower entities."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mower_mapping = get_mapping_by_device(data.device)
    if mower_mapping is None:
        return
    async_add_entities(
        [
            TuyaBLELawnMower(
                hass,
                data.coordinator,
                data.device,
                data.product,
                mower_mapping,
            )
        ]
    )
