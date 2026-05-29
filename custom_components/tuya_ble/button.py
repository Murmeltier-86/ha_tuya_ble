"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass, field

import asyncio
import logging
from typing import Callable

from homeassistant.components.button import (
    ButtonEntityDescription,
    ButtonEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)


TuyaBLEButtonIsAvailable = Callable[["TuyaBLEButton", TuyaBLEProductInfo], bool] | None


@dataclass
class TuyaBLEButtonMapping:
    dp_id: int
    description: ButtonEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    is_available: TuyaBLEButtonIsAvailable = None
    press_value: bool | int | str | None = None
    command_options: list[str] | None = None
    extra_datapoints: list[tuple[int, TuyaBLEDataPointType, bytes | bool | int | str]] | None = None
    command_sequence: list[tuple[bytes | bool | int | str, float]] | None = None


def is_fingerbot_in_push_mode(self: TuyaBLEButton, product: TuyaBLEProductInfo) -> bool:
    result: bool = True
    if product.fingerbot:
        datapoint = self._device.datapoints[product.fingerbot.mode]
        if datapoint:
            result = datapoint.value == 0
    return result


@dataclass
class TuyaBLEFingerbotModeMapping(TuyaBLEButtonMapping):
    description: ButtonEntityDescription = field(
        default_factory=lambda: ButtonEntityDescription(
            key="push",
        )
    )
    is_available: TuyaBLEButtonIsAvailable = is_fingerbot_in_push_mode

@dataclass
class TuyaBLELockMapping(TuyaBLEButtonMapping):
    description: ButtonEntityDescription = field(
        default_factory=lambda: ButtonEntityDescription(
            key="push",
        )
    )
    is_available: TuyaBLEButtonIsAvailable = 0

@dataclass
class TuyaBLECategoryButtonMapping:
    products: dict[str, list[TuyaBLEButtonMapping]] | None = None
    mapping: list[TuyaBLEButtonMapping] | None = None


mapping: dict[str, TuyaBLECategoryButtonMapping] = {
    "szjqr": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                ["3yqdo5yt", "xhf790if"],  # CubeTouch 1s and II
                [
                    TuyaBLEFingerbotModeMapping(dp_id=1),
                ],
            ),
            **dict.fromkeys(
                [
                    "blliqpsj",
                    "ndvkgsrm",
                    "yiihr7zh",
                    "neq16kgd"
                ],  # Fingerbot Plus
                [
                    TuyaBLEFingerbotModeMapping(dp_id=2),
                ],
            ),
            **dict.fromkeys(
                [
                    "ltak7e1p",
                    "y6kttvd6",
                    "yrnk7mnn",
                    "nvr2rocq",
                    "bnt7wajf",
                    "rvdceqjh",
                    "5xhbk964",
                ],  # Fingerbot
                [
                    TuyaBLEFingerbotModeMapping(dp_id=2),
                ],
            ),
        },
    ),
    "kg": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                [
                    "mknd4lci",
                    "riecov42"
                ],  # Fingerbot Plus
                [
                    TuyaBLEFingerbotModeMapping(dp_id=108),
                ],
            ),
        },
    ),
    "znhsb": TuyaBLECategoryButtonMapping(
        products={
            "cdlandip":  # Smart water bottle
            [
                TuyaBLEButtonMapping(
                    dp_id=109,
                    description=ButtonEntityDescription(
                        key="bright_lid_screen",
                    ),
                ),
            ],
        },
    ),
    "ms": TuyaBLECategoryButtonMapping(
          products={
             "okkyfgfs": # Smart Lock
             [
                 TuyaBLELockMapping(
                     dp_id=6,
                     description=ButtonEntityDescription(
                         key="bluetooth_unlock",
                     ),
                 ),
             ],
          },
      ),
    "gcj": TuyaBLECategoryButtonMapping(
        products={
            "7yr5iwga": [  # Robot Mower PMRC 250 A1 (BT)
                TuyaBLEButtonMapping(
                    dp_id=115,
                    description=ButtonEntityDescription(
                        key="start_mowing",
                        icon="mdi:mower-on",
                    ),
                    dp_type=TuyaBLEDataPointType.DT_ENUM,
                    press_value=3,
                ),
                TuyaBLEButtonMapping(
                    dp_id=115,
                    description=ButtonEntityDescription(
                        key="start_fixed_mowing",
                        icon="mdi:mower-on",
                    ),
                    dp_type=TuyaBLEDataPointType.DT_ENUM,
                    press_value=4,
                ),
                TuyaBLEButtonMapping(
                    dp_id=115,
                    description=ButtonEntityDescription(
                        key="pause_mowing",
                        icon="mdi:pause",
                    ),
                    dp_type=TuyaBLEDataPointType.DT_ENUM,
                    press_value=0,
                ),
                TuyaBLEButtonMapping(
                    dp_id=115,
                    description=ButtonEntityDescription(
                        key="cancel_mowing",
                        icon="mdi:cancel",
                    ),
                    dp_type=TuyaBLEDataPointType.DT_ENUM,
                    press_value=1,
                ),
                TuyaBLEButtonMapping(
                    dp_id=115,
                    description=ButtonEntityDescription(
                        key="continue_mowing",
                        icon="mdi:mower-on",
                    ),
                    dp_type=TuyaBLEDataPointType.DT_ENUM,
                    press_value=2,
                ),
                TuyaBLEButtonMapping(
                    dp_id=115,
                    description=ButtonEntityDescription(
                        key="return_to_dock",
                        icon="mdi:home-import-outline",
                    ),
                    dp_type=TuyaBLEDataPointType.DT_ENUM,
                    press_value=5,
                    command_sequence=[
                        (0, 1.0),
                        (1, 1.0),
                        (5, 0.0),
                    ],
                ),
                TuyaBLEButtonMapping(
                    dp_id=107,
                    description=ButtonEntityDescription(
                        key="clear_schedule",
                        icon="mdi:calendar-remove",
                        entity_category=EntityCategory.CONFIG,
                    ),
                    press_value=True,
                ),
                TuyaBLEButtonMapping(
                    dp_id=108,
                    description=ButtonEntityDescription(
                        key="query_schedule",
                        icon="mdi:calendar-refresh",
                        entity_category=EntityCategory.CONFIG,
                    ),
                    press_value=True,
                ),
                TuyaBLEButtonMapping(
                    dp_id=109,
                    description=ButtonEntityDescription(
                        key="query_zones",
                        icon="mdi:map-search",
                        entity_category=EntityCategory.CONFIG,
                    ),
                    press_value=True,
                ),
            ],
        },
    ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECategoryButtonMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if device.category == "gcj" and "7yr5iwga" in category.products:
            return category.products["7yr5iwga"]
        if category.mapping is not None:
            return category.mapping
        else:
            return []
    else:
        return []


class TuyaBLEButton(TuyaBLEEntity, ButtonEntity):
    """Representation of a Tuya BLE Button."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLEButtonMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

    def press(self) -> None:
        """Press the button."""
        dp_type = self._mapping.dp_type or TuyaBLEDataPointType.DT_BOOL
        value = self._mapping.press_value

        if dp_type == TuyaBLEDataPointType.DT_ENUM and isinstance(value, str):
            if self._mapping.command_options and value in self._mapping.command_options:
                value = self._mapping.command_options.index(value)
            else:
                _LOGGER.debug("%s: unknown enum button value %s", self._device.address, value)
                return

        if value is None:
            value = False

        datapoint = self._device.datapoints.get_or_create(
            self._mapping.dp_id,
            dp_type,
            value,
        )
        if datapoint:
            if self._mapping.command_sequence is not None:
                self._hass.create_task(self._async_press_sequence(dp_type))
            elif self._mapping.press_value is not None:
                _LOGGER.info(
                    "%s: BLE button command %s -> dp=%s type=%s value=%s",
                    self._device.address,
                    self.entity_description.key,
                    self._mapping.dp_id,
                    dp_type.name,
                    value,
                )
                self._hass.create_task(
                    self._async_press_datapoints(datapoint, value)
                )
            elif getattr(self._product, "lock", False):  # Safely check if 'lock' exists and is True
                #Lock needs true to activate lock/unlock commands
                self._hass.create_task(datapoint.set_value(True))
            else:
                self._hass.create_task(datapoint.set_value(not bool(datapoint.value)))

    async def _async_press_sequence(self, dp_type: TuyaBLEDataPointType) -> None:
        """Send a sequence of button values with delays between writes."""
        if self._mapping.command_sequence is None:
            return

        for value, delay_after in self._mapping.command_sequence:
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.dp_id,
                dp_type,
                value,
            )
            _LOGGER.info(
                "%s: BLE button sequence %s -> dp=%s type=%s value=%s",
                self._device.address,
                self.entity_description.key,
                self._mapping.dp_id,
                dp_type.name,
                value,
            )
            await datapoint.set_value(value)
            if delay_after > 0:
                await asyncio.sleep(delay_after)

    async def _async_press_datapoints(
        self,
        datapoint,
        value: bytes | bool | int | str,
    ) -> None:
        """Send the button datapoint and optional companion datapoints as one BLE write."""
        self._device.datapoints.begin_update()
        try:
            if self._mapping.extra_datapoints:
                for dp_id, dp_type, dp_value in self._mapping.extra_datapoints:
                    _LOGGER.info(
                        "%s: BLE button companion datapoint %s -> dp=%s type=%s value=%s",
                        self._device.address,
                        self.entity_description.key,
                        dp_id,
                        dp_type.name,
                        dp_value,
                    )
                    companion = self._device.datapoints.get_or_create(
                        dp_id,
                        dp_type,
                        dp_value,
                    )
                    await companion.set_value(dp_value)
            await datapoint.set_value(value)
        finally:
            await self._device.datapoints.end_update(force_connect=True)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        result = super().available
        if result and self._mapping.is_available:
            result = self._mapping.is_available(self, self._product)
        return result


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLEButton] = []
    for mapping in mappings:
        if mapping.force_add or data.device.datapoints.has_id(
            mapping.dp_id, mapping.dp_type
        ):
            entities.append(
                TuyaBLEButton(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    mapping,
                )
            )
    async_add_entities(entities)
