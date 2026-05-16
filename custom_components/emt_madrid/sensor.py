"""Support for EMT Madrid (Empresa Municipal de Transportes de Madrid) to get next departures."""

import logging
from typing import Any

import aiohttp
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


from emt_madrid import EMTClient, Stop, Line


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
ATTR_BUS_LATITUDE = "bus_latitude"
ATTR_BUS_LONGITUDE = "bus_longitude"
ATTR_BUS_ID = "bus_id"
ATTR_BUS_DISTANCE = "bus_distance"
ATTR_BUS_ESTIMATE_SECONDS = "bus_estimate_seconds"
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
    """Implementation of an EMT-Madrid bus line sensor using the emt-madrid library."""

    def __init__(
        self,
        emt_client: EMTClient,
        stop: Stop,
        line: Line,
        name: str,
        icon: str,
        stop_id: int,
    ) -> None:
        """Initialize the sensor."""
        self._emt_client = emt_client
        self._stop = stop
        self._line = line
        self._name = name
        self._icon = icon
        self._stop_id = stop_id
        self._state = None

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the sensor."""
        return f"{self._stop_id}_{self._line.line_number}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        if self._line.arrival is not None:
            return min(self._line.arrival, 45)
        return None

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
        # Find bus arrival for this specific line
        bus_arrival = None
        if self._stop.bus_arrivals:
            for arrival in self._stop.bus_arrivals:
                if arrival.line == self._line.line_number:
                    bus_arrival = arrival
                    break

        # Extract bus coordinates if available
        bus_latitude = None
        bus_longitude = None
        bus_id = None
        bus_distance = None
        bus_estimate_seconds = None

        if bus_arrival and bus_arrival.coordinates and len(bus_arrival.coordinates) >= 2:
            bus_latitude = bus_arrival.coordinates[1]  # latitude is second element
            bus_longitude = bus_arrival.coordinates[0]  # longitude is first element
            bus_id = bus_arrival.bus_id
            bus_distance = bus_arrival.distance_bus
            bus_estimate_seconds = bus_arrival.estimate_arrive_sec

        return {
            ATTR_NEXT_UP: min(self._line.next_arrival, 45) if self._line.next_arrival is not None else None,
            ATTR_LINE: self._line.line_number,
            ATTR_LINE_DISTANCE: self._line.distance if hasattr(self._line, 'distance') else None,
            ATTR_LINE_DESTINATION: self._line.destination,
            ATTR_LINE_ORIGIN: self._line.origin,
            ATTR_LINE_START_TIME: str(self._line.start_time) if self._line.start_time else None,
            ATTR_LINE_END_TIME: str(self._line.end_time) if self._line.end_time else None,
            ATTR_LINE_MAX_FREQ: self._line.max_frequency,
            ATTR_LINE_MIN_FREQ: self._line.min_frequency,
            ATTR_STOP_ID: self._stop_id,
            ATTR_STOP_NAME: self._stop.stop_name,
            ATTR_STOP_ADDRESS: self._stop.stop_address,
            ATTR_BUS_LATITUDE: bus_latitude,
            ATTR_BUS_LONGITUDE: bus_longitude,
            ATTR_BUS_ID: bus_id,
            ATTR_BUS_DISTANCE: bus_distance,
            ATTR_BUS_ESTIMATE_SECONDS: bus_estimate_seconds,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        # Get updated stop with bus arrivals
        self._stop = await self._emt_client.get_arrivals()
        # Refresh reference to line from the updated stop
        for line in self._stop.stop_lines:
            if line.line_number == self._line.line_number:
                self._line = line
                break


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""

    email = config.get(CONF_EMAIL)
    password = config.get(CONF_PASSWORD)
    stop_id = config.get(CONF_STOP_ID)
    lines = config.get(CONF_BUS_LINES)
    icon = config.get(CONF_ICON)

    # Create aiohttp session
    session = aiohttp.ClientSession()

    try:
        # Create EMT client
        emt_client = EMTClient(
            email=email,
            password=password,
            stop_id=stop_id,
            session=session,
            lines=lines if lines else None,
        )

        # Get stop information
        stop: Stop = await emt_client.get_stop_info()

        # If no lines specified, use all lines from the stop
        if not lines or len(lines) == 0:
            lines = [line.line_number for line in stop.stop_lines]

        bus_line_sensors = []
        for line_number in lines:
            # Find the line in the stop's lines
            line_obj = next(
                (line for line in stop.stop_lines if line.line_number == line_number),
                None
            )
            if line_obj is None:
                _LOGGER.error(
                    f"Sensor setup failed. Line {line_number} not serviced at this stop (Stop ID: {stop_id})"
                )
                continue

            name = f"Bus {line_number} - {stop.stop_name}"
            sensor = BusLineSensor(
                emt_client=emt_client,
                stop=stop,
                line=line_obj,
                name=name,
                icon=icon,
                stop_id=stop_id,
            )
            bus_line_sensors.append(sensor)

        add_entities(bus_line_sensors)

    except Exception as e:
        _LOGGER.error(f"Error setting up EMT Madrid sensor: {e}")
        await session.close()
        raise

    async def cleanup(_):
        """Close the aiohttp session when the platform is unloaded."""
        await session.close()

    hass.bus.async_listen_once("homeassistant_stop", cleanup)
