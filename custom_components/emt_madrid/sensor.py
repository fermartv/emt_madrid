"""Support for EMT Madrid (Empresa Municipal de Transportes de Madrid) to get next departures."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_EMAIL,
    CONF_ICON,
    CONF_PASSWORD,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .emt_madrid import APIEMT

_LOGGER = logging.getLogger(__name__)


CONF_STOP_ID = "stop"
CONF_BUS_LINES = "lines"

DEFAULT_ICON = "mdi:bus"

ATTR_NEXT_UP = "next_bus"
ATTR_STOP_ID = "stop_id"
ATTR_STOP_NAME = "stop_name"
ATTR_STOP_ADDRESS = "stop_address"
ATTR_LINE = "line"
ATTR_LINE_DESTINATION = "destination"
ATTR_LINE_ORIGIN = "origin"
ATTR_LINE_START_TIME = "start_time"
ATTR_LINE_END_TIME = "end_time"
ATTR_LINE_MAX_FREQ = "max_frequency"
ATTR_LINE_MIN_FREQ = "min_frequency"
ATTR_LINE_DISTANCE = "distance"
ATTRIBUTION = "Data provided by EMT Madrid MobilityLabs"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_STOP_ID): cv.positive_int,
        vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
        vol.Optional(CONF_BUS_LINES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


class BusLineSensor(Entity):
    """Implementation of an EMT-Madrid bus line sensor."""

    def __init__(self, api_emt: APIEMT, stop_id, line, name, icon) -> None:
        """Initialize the sensor."""
        self._state = None
        self._api_emt = api_emt
        self._stop_id = stop_id
        self._bus_line = line
        self._icon = icon
        self._name = name

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self) -> int:
        """Return the state of the sensor."""
        arrival_time = self._api_emt.get_arrival_time(self._bus_line)
        return arrival_time[0]

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfTime.MINUTES

    @property
    def icon(self) -> str:
        """Return sensor specific icon."""
        return self._icon

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        arrival_time = self._api_emt.get_arrival_time(self._bus_line)
        stop_info = self._api_emt.get_stop_info()
        line_info = self._api_emt.get_line_info(self._bus_line)

        return {
            ATTR_NEXT_UP: arrival_time[1],
            ATTR_LINE: self._bus_line,
            ATTR_LINE_DISTANCE: line_info.get("distance")[0],
            ATTR_LINE_DESTINATION: line_info.get("destination"),
            ATTR_LINE_ORIGIN: line_info.get("origin"),
            ATTR_LINE_START_TIME: line_info.get("start_time"),
            ATTR_LINE_END_TIME: line_info.get("end_time"),
            ATTR_LINE_MAX_FREQ: line_info.get("max_freq"),
            ATTR_LINE_MIN_FREQ: line_info.get("min_freq"),
            ATTR_STOP_ID: self._stop_id,
            ATTR_STOP_NAME: stop_info.get("bus_stop_name"),
            ATTR_STOP_ADDRESS: stop_info.get("bus_stop_address"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    def update(self) -> None:
        """Fetch new state data for the sensor."""
        self._api_emt.update_arrival_times(self._stop_id)


def get_api_emt_instance(config: ConfigType) -> APIEMT:
    """Create an instance of the APIEMT class with the provided configuration."""
    email = config.get(CONF_EMAIL)
    password = config.get(CONF_PASSWORD)
    stop_id = config.get(CONF_STOP_ID)
    api_emt = APIEMT(email, password, stop_id)
    api_emt.authenticate()
    api_emt.update_stop_info(stop_id)
    return api_emt


def create_bus_line_sensor(
    api_emt: APIEMT, stop_id, line, name, icon, config: ConfigType
) -> BusLineSensor:
    """Create a BusLineSensor instance with the provided APIEMT instance and configuration."""
    api_emt.update_arrival_times(stop_id)
    return BusLineSensor(api_emt, stop_id, line, name, icon)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    api_emt = get_api_emt_instance(config)
    stop_id = config.get(CONF_STOP_ID)
    stop_info = api_emt.get_stop_info()
    lines = config.get(CONF_BUS_LINES)
    bus_line_sensors = []
    if not lines or len(lines) == 0:
        lines = list(stop_info["lines"].keys())
    for line in lines:
        if line in stop_info["lines"]:
            name = f"Bus {line} - {stop_info['bus_stop_name']}"
            icon = config.get(CONF_ICON)
            bus_line_sensors.append(
                create_bus_line_sensor(api_emt, stop_id, line, name, icon, config)
            )
        else:
            _LOGGER.error(
                f"Sensor setup failed. Line {line} not serviced at this stop (Stop ID: {stop_id})"
            )
    add_entities(bus_line_sensors)
