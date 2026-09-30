"""Tests for the EMT Madrid sensor platform."""

from unittest import mock
from unittest.mock import MagicMock, patch, AsyncMock

from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

import logging

import aiohttp
import pytest
from emt_madrid import EMTClient, Line, Stop
from homeassistant.helpers.entity_component import async_update_entity

from homeassistant.components.emt_madrid.sensor import (
    ATTR_ATTRIBUTION,
    ATTR_BUS_DISTANCE,
    ATTR_BUS_ESTIMATE_SECONDS,
    ATTR_BUS_ID,
    ATTR_BUS_LATITUDE,
    ATTR_BUS_LONGITUDE,
    ATTR_LINE,
    ATTR_LINE_DESTINATION,
    ATTR_LINE_DISTANCE,
    ATTR_LINE_END_TIME,
    ATTR_LINE_MAX_FREQ,
    ATTR_LINE_MIN_FREQ,
    ATTR_LINE_ORIGIN,
    ATTR_LINE_START_TIME,
    ATTR_NEXT_UP,
    ATTR_STOP_ADDRESS,
    ATTR_STOP_ID,
    ATTR_STOP_NAME,
    CONF_BUS_LINES,
    CONF_STOP_ID,
    BusLineSensor,
    DEFAULT_ICON,
    PLATFORM_SCHEMA as EMT_PLATFORM_SCHEMA,
)

VALID_CONFIG = {
    "sensor": {
        "platform": "emt_madrid",
        CONF_EMAIL: "test@example.com",
        CONF_PASSWORD: "test_password",
        CONF_STOP_ID: 1234,
    }
}

VALID_CONFIG_WITH_LINES = {
    "sensor": {
        "platform": "emt_madrid",
        CONF_EMAIL: "test@example.com",
        CONF_PASSWORD: "test_password",
        CONF_STOP_ID: 1234,
        CONF_BUS_LINES: ["1", "7"],
    }
}


async def test_platform_schema() -> None:
    """Test the platform schema."""
    assert CONF_EMAIL in EMT_PLATFORM_SCHEMA.schema
    assert CONF_PASSWORD in EMT_PLATFORM_SCHEMA.schema
    assert CONF_STOP_ID in EMT_PLATFORM_SCHEMA.schema
    assert CONF_BUS_LINES in EMT_PLATFORM_SCHEMA.schema


async def test_sensor_defaults() -> None:
    """Test sensor default values."""
    assert DEFAULT_ICON == "mdi:bus"


async def test_bus_line_sensor_unique_id() -> None:
    """Test BusLineSensor unique_id property."""
    mock_emt_client = MagicMock()
    mock_stop = MagicMock()
    mock_stop.stop_id = 1234
    mock_line = MagicMock()
    mock_line.line_number = "1"

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    assert sensor.unique_id == "1234_1"


async def test_bus_line_sensor_name() -> None:
    """Test BusLineSensor name property."""
    mock_emt_client = MagicMock()
    mock_stop = MagicMock()
    mock_line = MagicMock()

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Bus 1 - Test Stop",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    assert sensor.name == "Bus 1 - Test Stop"


async def test_bus_line_sensor_icon() -> None:
    """Test BusLineSensor icon property."""
    mock_emt_client = MagicMock()
    mock_stop = MagicMock()
    mock_line = MagicMock()

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon="mdi:bus",
        stop_id=1234,
    )

    assert sensor.icon == "mdi:bus"


async def test_bus_line_sensor_state_with_arrival(hass: HomeAssistant) -> None:
    """Test BusLineSensor state with arrival time."""
    mock_emt_client = MagicMock()
    mock_stop = MagicMock()
    mock_line = MagicMock()
    mock_line.arrival = 10
    mock_line.line_number = "1"

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    assert sensor.state == 10


async def test_bus_line_sensor_state_with_high_arrival(hass: HomeAssistant) -> None:
    """Test BusLineSensor state caps at 45 minutes."""
    mock_emt_client = MagicMock()
    mock_stop = MagicMock()
    mock_line = MagicMock()
    mock_line.arrival = 60
    mock_line.line_number = "1"

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    assert sensor.state == 45


async def test_bus_line_sensor_state_without_arrival(hass: HomeAssistant) -> None:
    """Test BusLineSensor state without arrival time."""
    mock_emt_client = MagicMock()
    mock_stop = MagicMock()
    mock_line = MagicMock()
    mock_line.arrival = None
    mock_line.line_number = "1"

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    assert sensor.state is None


async def test_bus_line_sensor_unit_of_measurement(hass: HomeAssistant) -> None:
    """Test BusLineSensor unit_of_measurement."""
    mock_emt_client = MagicMock()
    mock_stop = MagicMock()
    mock_line = MagicMock()

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    from homeassistant.const import UnitOfTime
    assert sensor.unit_of_measurement == UnitOfTime.MINUTES


async def test_bus_line_sensor_extra_state_attributes(hass: HomeAssistant) -> None:
    """Test BusLineSensor extra_state_attributes."""
    mock_emt_client = MagicMock()

    mock_stop = MagicMock()
    mock_stop.stop_id = 1234
    mock_stop.stop_name = "Calle de Alzheimer"
    mock_stop.stop_address = "Calle de Alzheimer, 63"

    mock_line = MagicMock()
    mock_line.line_number = "1"
    mock_line.arrival = 10
    mock_line.next_arrival = 8
    mock_line.destination = "Cuatro Caminos"
    mock_line.origin = "Pza. de Cibeles"
    mock_line.start_time = "06:00"
    mock_line.end_time = "23:30"
    mock_line.max_frequency = 15
    mock_line.min_frequency = 5
    mock_line.distance = 1200

    mock_bus_arrival = MagicMock()
    mock_bus_arrival.line = "1"
    mock_bus_arrival.coordinates = [-3.7038, 40.4168]
    mock_bus_arrival.bus_id = "BUS001"
    mock_bus_arrival.distance_bus = 500
    mock_bus_arrival.estimate_arrive_sec = 480
    mock_stop.bus_arrivals = [mock_bus_arrival]

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    attrs = sensor.extra_state_attributes

    assert attrs[ATTR_NEXT_UP] == 8
    assert attrs[ATTR_LINE] == "1"
    assert attrs[ATTR_LINE_DISTANCE] == 1200
    assert attrs[ATTR_LINE_DESTINATION] == "Cuatro Caminos"
    assert attrs[ATTR_LINE_ORIGIN] == "Pza. de Cibeles"
    assert attrs[ATTR_LINE_START_TIME] == "06:00"
    assert attrs[ATTR_LINE_END_TIME] == "23:30"
    assert attrs[ATTR_LINE_MAX_FREQ] == 15
    assert attrs[ATTR_LINE_MIN_FREQ] == 5
    assert attrs[ATTR_STOP_ID] == 1234
    assert attrs[ATTR_STOP_NAME] == "Calle de Alzheimer"
    assert attrs[ATTR_STOP_ADDRESS] == "Calle de Alzheimer, 63"
    assert attrs[ATTR_BUS_LATITUDE] == 40.4168
    assert attrs[ATTR_BUS_LONGITUDE] == -3.7038
    assert attrs[ATTR_BUS_ID] == "BUS001"
    assert attrs[ATTR_BUS_DISTANCE] == 500
    assert attrs[ATTR_BUS_ESTIMATE_SECONDS] == 480
    assert attrs[ATTR_ATTRIBUTION] == "Data provided by EMT Madrid MobilityLabs"


async def test_setup_platform_all_lines(hass: HomeAssistant) -> None:
    """Test setting up the platform with all lines from stop."""
    with patch("homeassistant.components.emt_madrid.sensor.EMTClient") as mock_client_class:
        mock_emt_client = AsyncMock()
        mock_client_class.return_value = mock_emt_client

        mock_stop = MagicMock()
        mock_stop.stop_id = 1234
        mock_stop.stop_name = "Calle de Alzheimer"
        mock_stop.stop_address = "Calle de Alzheimer, 63"

        mock_line1 = MagicMock()
        mock_line1.line_number = "1"
        mock_line1.arrival = 10
        mock_line1.next_arrival = 8
        mock_line1.destination = "Cuatro Caminos"
        mock_line1.origin = "Pza. de Cibeles"
        mock_line1.start_time = "06:00"
        mock_line1.end_time = "23:30"
        mock_line1.max_frequency = 15
        mock_line1.min_frequency = 5

        mock_line7 = MagicMock()
        mock_line7.line_number = "7"
        mock_line7.arrival = 5
        mock_line7.next_arrival = 3
        mock_line7.destination = "Pitis"
        mock_line7.origin = "Oporto"
        mock_line7.start_time = "06:00"
        mock_line7.end_time = "23:30"
        mock_line7.max_frequency = 20
        mock_line7.min_frequency = 10

        mock_stop.stop_lines = [mock_line1, mock_line7]
        mock_stop.bus_arrivals = []

        mock_emt_client.get_stop_info.return_value = mock_stop
        mock_emt_client.get_arrivals.return_value = mock_stop

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            assert await async_setup_component(hass, "sensor", VALID_CONFIG)
            await hass.async_block_till_done()

    # Check that sensors were created
    bus_1_state = hass.states.get("sensor.bus_1_calle_de_alzheimer")
    assert bus_1_state is not None
    assert bus_1_state.state == "10"

    bus_7_state = hass.states.get("sensor.bus_7_calle_de_alzheimer")
    assert bus_7_state is not None
    assert bus_7_state.state == "5"


async def test_setup_platform_specific_lines(hass: HomeAssistant) -> None:
    """Test setting up the platform with specific lines."""
    with patch("homeassistant.components.emt_madrid.sensor.EMTClient") as mock_client_class:
        mock_emt_client = AsyncMock()
        mock_client_class.return_value = mock_emt_client

        mock_stop = MagicMock()
        mock_stop.stop_id = 1234
        mock_stop.stop_name = "Calle de Alzheimer"
        mock_stop.stop_address = "Calle de Alzheimer, 63"

        mock_line1 = MagicMock()
        mock_line1.line_number = "1"
        mock_line1.arrival = 10
        mock_line1.next_arrival = 8

        mock_line7 = MagicMock()
        mock_line7.line_number = "7"
        mock_line7.arrival = 5
        mock_line7.next_arrival = 3

        mock_stop.stop_lines = [mock_line1, mock_line7]
        mock_stop.bus_arrivals = []

        mock_emt_client.get_stop_info.return_value = mock_stop
        mock_emt_client.get_arrivals.return_value = mock_stop

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            assert await async_setup_component(
                hass, "sensor", VALID_CONFIG_WITH_LINES
            )
            await hass.async_block_till_done()

    # Check that only specified sensors were created
    bus_1_state = hass.states.get("sensor.bus_1_calle_de_alzheimer")
    assert bus_1_state is not None

    bus_7_state = hass.states.get("sensor.bus_7_calle_de_alzheimer")
    assert bus_7_state is not None


async def test_bus_line_sensor_async_update(hass: HomeAssistant) -> None:
    """Test BusLineSensor async_update method."""
    mock_emt_client = AsyncMock()

    mock_stop = MagicMock()
    mock_stop.stop_id = 1234
    mock_stop.stop_name = "Calle de Alzheimer"
    mock_stop.stop_address = "Calle de Alzheimer, 63"

    mock_line = MagicMock()
    mock_line.line_number = "1"
    mock_line.arrival = 5
    mock_line.next_arrival = 3
    mock_line.destination = "Cuatro Caminos"
    mock_line.origin = "Pza. de Cibeles"
    mock_line.start_time = "06:00"
    mock_line.end_time = "23:30"
    mock_line.max_frequency = 15
    mock_line.min_frequency = 5
    mock_line.distance = 1200

    mock_stop.stop_lines = [mock_line]
    mock_stop.bus_arrivals = []

    # Initial stop and line
    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    # Create updated stop with new data
    mock_updated_stop = MagicMock()
    mock_updated_stop.stop_id = 1234
    mock_updated_stop.stop_name = "Calle de Alzheimer"
    mock_updated_stop.stop_address = "Calle de Alzheimer, 63"

    mock_updated_line = MagicMock()
    mock_updated_line.line_number = "1"
    mock_updated_line.arrival = 3
    mock_updated_line.next_arrival = 2
    mock_updated_line.destination = "Cuatro Caminos"
    mock_updated_line.origin = "Pza. de Cibeles"
    mock_updated_line.start_time = "06:00"
    mock_updated_line.end_time = "23:30"
    mock_updated_line.max_frequency = 15
    mock_updated_line.min_frequency = 5
    mock_updated_line.distance = 1200

    mock_updated_stop.stop_lines = [mock_updated_line]
    mock_updated_stop.bus_arrivals = []

    mock_emt_client.get_arrivals.return_value = mock_updated_stop

    # Call async_update
    await sensor.async_update()

    # Verify the sensor state was updated
    assert sensor.state == 3
    assert sensor._line.arrival == 3
    assert sensor._line.next_arrival == 2


async def test_extra_state_attributes_no_bus_arrivals(hass: HomeAssistant) -> None:
    """Test extra_state_attributes when stop has no bus arrivals."""
    mock_emt_client = MagicMock()

    mock_stop = MagicMock()
    mock_stop.stop_id = 1234
    mock_stop.stop_name = "Calle de Alzheimer"
    mock_stop.stop_address = "Calle de Alzheimer, 63"
    mock_stop.bus_arrivals = []

    mock_line = MagicMock()
    mock_line.line_number = "1"
    mock_line.arrival = 10
    mock_line.next_arrival = 8
    mock_line.destination = "Cuatro Caminos"
    mock_line.origin = "Pza. de Cibeles"
    mock_line.start_time = "06:00"
    mock_line.end_time = "23:30"
    mock_line.max_frequency = 15
    mock_line.min_frequency = 5
    mock_line.distance = 1200

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    attrs = sensor.extra_state_attributes

    assert attrs[ATTR_NEXT_UP] == 8
    assert attrs[ATTR_LINE_DISTANCE] == 1200
    assert attrs[ATTR_BUS_LATITUDE] is None
    assert attrs[ATTR_BUS_LONGITUDE] is None
    assert attrs[ATTR_BUS_ID] is None
    assert attrs[ATTR_BUS_DISTANCE] is None
    assert attrs[ATTR_BUS_ESTIMATE_SECONDS] is None


async def test_extra_state_attributes_next_arrival_none(hass: HomeAssistant) -> None:
    """Test extra_state_attributes when line.next_arrival is None."""
    mock_emt_client = MagicMock()

    mock_stop = MagicMock()
    mock_stop.stop_id = 1234
    mock_stop.stop_name = "Calle de Alzheimer"
    mock_stop.stop_address = "Calle de Alzheimer, 63"
    mock_stop.bus_arrivals = []

    mock_line = MagicMock()
    mock_line.line_number = "1"
    mock_line.arrival = 10
    mock_line.next_arrival = None
    mock_line.destination = "Cuatro Caminos"
    mock_line.origin = "Pza. de Cibeles"
    mock_line.start_time = "06:00"
    mock_line.end_time = "23:30"
    mock_line.max_frequency = 15
    mock_line.min_frequency = 5
    mock_line.distance = 1200

    sensor = BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )

    attrs = sensor.extra_state_attributes

    assert attrs[ATTR_NEXT_UP] is None


async def test_setup_platform_invalid_line(hass: HomeAssistant) -> None:
    """Test setting up the platform with an invalid line."""
    config = {
        "sensor": {
            "platform": "emt_madrid",
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
            CONF_STOP_ID: 1234,
            CONF_BUS_LINES: ["1", "99"],  # 99 doesn't exist
        }
    }

    with patch("homeassistant.components.emt_madrid.sensor.EMTClient") as mock_client_class:
        mock_emt_client = AsyncMock()
        mock_client_class.return_value = mock_emt_client

        mock_stop = MagicMock()
        mock_stop.stop_id = 1234
        mock_stop.stop_name = "Calle de Alzheimer"

        mock_line1 = MagicMock()
        mock_line1.line_number = "1"
        mock_line1.arrival = 10
        mock_line1.next_arrival = 8

        mock_stop.stop_lines = [mock_line1]
        mock_stop.bus_arrivals = []

        mock_emt_client.get_stop_info.return_value = mock_stop
        mock_emt_client.get_arrivals.return_value = mock_stop

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            assert await async_setup_component(hass, "sensor", config)
            await hass.async_block_till_done()

    # Check that only valid sensor was created
    bus_1_state = hass.states.get("sensor.bus_1_calle_de_alzheimer")
    assert bus_1_state is not None

    # Invalid line should not create a sensor
    bus_99_state = hass.states.get("sensor.bus_99_calle_de_alzheimer")
    assert bus_99_state is None


# Replies of the EMT arrivals endpoint, in the shapes recorded in emt-madrid's own test fixtures.
def _arrive(line: str, seconds: int, bus: int) -> dict:
    return {
        "line": line, "stop": "1234", "bus": bus, "destination": "Cuatro Caminos",
        "estimateArrive": seconds, "DistanceBus": 900, "isHead": "False", "deviation": 0,
        "positionTypeBus": "0", "geometry": {"type": "Point", "coordinates": [-3.7, 40.4]},
    }


ARRIVALS_RESPONSE = {
    "code": "00",
    "data": [{"Arrive": [_arrive("1", 300, 11), _arrive("1", 720, 12), _arrive("7", 600, 71)],
              "StopInfo": [], "ExtraInfo": [], "Incident": {}}],
}
ARRIVALS_EMPTY_RESPONSE = {
    "code": "00",
    "data": [{"Arrive": [], "StopInfo": [], "ExtraInfo": [], "Incident": {}}],
}
ARRIVALS_NO_DATA_RESPONSE = {"code": "00", "description": " Data recovered  OK  (lapsed: 1065 millsecs)"}
API_LIMIT_EXCEEDED_RESPONSE = {"code": "98", "description": "Limit use API reached", "data": []}
STOP_NOT_FOUND_RESPONSE = {
    "code": "80",
    "description": [{"EN": "Bus Stop disabled or not exists"}],
    "data": [{"Arrive": [], "StopInfo": [], "ExtraInfo": [], "Incident": {}}],
}


def _real_client(replies: list) -> tuple[EMTClient, Stop]:
    """A real emt-madrid client whose authenticated HTTP exchange returns the given replies in order."""
    client = EMTClient(email="test@example.com", password="test_password", stop_id=1234, session=MagicMock())
    stop = Stop(
        stop_id=1234,
        stop_name="Calle de Alzheimer",
        stop_address="Calle de Alzheimer, 63",
        stop_coordinates=[-3.7, 40.4],
        stop_lines=[Line("1", "Pza. de Cibeles", "Cuatro Caminos"), Line("7", "Colombia", "Pza. Manuel Becerra")],
    )
    client._stop = stop
    client._repository.emt_authenticated_client.exchange = AsyncMock(side_effect=replies)
    return client, stop


def _sensors(client: EMTClient, stop: Stop) -> list[BusLineSensor]:
    return [
        BusLineSensor(emt_client=client, stop=stop, line=line, name=f"Bus {line.line_number}",
                      icon=DEFAULT_ICON, stop_id=1234)
        for line in stop.stop_lines
    ]


@pytest.mark.parametrize("empty_reply", [ARRIVALS_EMPTY_RESPONSE, ARRIVALS_NO_DATA_RESPONSE])
async def test_async_update_no_arrivals_clears_every_line(hass: HomeAssistant, caplog, empty_reply) -> None:
    """No bus scheduled (e.g. at night): no line keeps the last bus, and the sensors stay available."""
    client, stop = _real_client([ARRIVALS_RESPONSE, empty_reply])
    line_1, line_7 = _sensors(client, stop)

    await line_1.async_update()
    assert (line_1.state, line_7.state) == (5, 10)
    assert line_1.extra_state_attributes[ATTR_NEXT_UP] == 12
    assert line_1.extra_state_attributes[ATTR_BUS_LATITUDE] == 40.4

    caplog.clear()
    await line_1.async_update()

    assert (line_1.state, line_7.state) == (None, None)
    assert line_1.available and line_7.available
    for sensor in (line_1, line_7):
        assert sensor.extra_state_attributes[ATTR_NEXT_UP] is None
        assert sensor.extra_state_attributes[ATTR_BUS_LATITUDE] is None
    assert not [r for r in caplog.records if r.levelno >= logging.INFO]


@pytest.mark.parametrize(
    "failure",
    [API_LIMIT_EXCEEDED_RESPONSE, STOP_NOT_FOUND_RESPONSE, aiohttp.ClientConnectionError("connection reset"), TimeoutError()],
    ids=["rate-limit", "stop-not-found", "network", "timeout"],
)
async def test_async_update_api_error_marks_unavailable(hass: HomeAssistant, caplog, failure) -> None:
    """An API or network failure makes the sensor unavailable, logged once at INFO, and it recovers."""
    client, stop = _real_client([ARRIVALS_RESPONSE, failure, failure, ARRIVALS_RESPONSE, failure])
    line_1, _ = _sensors(client, stop)
    await line_1.async_update()
    caplog.clear()

    await line_1.async_update()
    await line_1.async_update()
    assert line_1.available is False
    down = [r for r in caplog.records if "unavailable for stop 1234, line 1" in r.getMessage()]
    assert len(down) == 1 and down[0].levelno == logging.INFO

    await line_1.async_update()
    assert line_1.available is True
    assert line_1.state == 5
    up = [r for r in caplog.records if "available again for stop 1234, line 1" in r.getMessage()]
    assert len(up) == 1 and up[0].levelno == logging.INFO

    await line_1.async_update()
    assert line_1.available is False
    assert len([r for r in caplog.records if "unavailable for stop 1234, line 1" in r.getMessage()]) == 2


async def test_states_published_by_home_assistant(hass: HomeAssistant, caplog) -> None:
    """End to end through HA: minutes, then unknown when no bus is scheduled, then unavailable on an error."""
    client, stop = _real_client([ARRIVALS_RESPONSE, ARRIVALS_EMPTY_RESPONSE, API_LIMIT_EXCEEDED_RESPONSE])
    client.get_stop_info = AsyncMock(return_value=stop)
    with patch("homeassistant.components.emt_madrid.sensor.EMTClient", return_value=client), \
            patch("aiohttp.ClientSession", return_value=MagicMock(close=AsyncMock())):
        assert await async_setup_component(hass, "sensor", VALID_CONFIG_WITH_LINES)
        await hass.async_block_till_done()

    entity_id = "sensor.bus_1_calle_de_alzheimer"
    assert hass.states.get(entity_id).state == "unknown"  # no update before add

    await async_update_entity(hass, entity_id)
    assert hass.states.get(entity_id).state == "5"

    await async_update_entity(hass, entity_id)
    assert hass.states.get(entity_id).state == "unknown"

    await async_update_entity(hass, entity_id)
    assert hass.states.get(entity_id).state == "unavailable"
    assert "Update for" not in caplog.text

