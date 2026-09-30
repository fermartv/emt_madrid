"""Tests for the EMT Madrid sensor platform."""

from unittest import mock
from unittest.mock import MagicMock, patch, AsyncMock

from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from emt_madrid import ArrivalsNotFoundError

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


def _wrapped_error(cause: Exception) -> ArrivalsNotFoundError:
    """Return the error emt-madrid raises: every failure re-raised as ArrivalsNotFoundError from its cause."""
    try:
        try:
            raise cause
        except Exception as err:
            raise ArrivalsNotFoundError(1234, str(err)) from err
    except ArrivalsNotFoundError as wrapped:
        return wrapped


def _sensor_with_arrival(mock_emt_client) -> BusLineSensor:
    """Build a sensor whose line currently shows a bus in 5 min (next in 12)."""
    mock_stop = MagicMock()
    mock_stop.stop_name = "Calle de Alzheimer"
    mock_stop.stop_address = "Calle de Alzheimer, 63"
    mock_line = MagicMock()
    mock_line.line_number = "1"
    mock_line.arrival = 5
    mock_line.next_arrival = 12
    mock_stop.stop_lines = [mock_line]
    mock_stop.bus_arrivals = [MagicMock(line="1", coordinates=[-3.7, 40.4])]
    return BusLineSensor(
        emt_client=mock_emt_client,
        stop=mock_stop,
        line=mock_line,
        name="Test Sensor",
        icon=DEFAULT_ICON,
        stop_id=1234,
    )


async def test_async_update_no_arrivals_clears_stale_state(hass: HomeAssistant, caplog) -> None:
    """No bus scheduled: the last arrival must not be kept, and the sensor stays available."""
    mock_emt_client = AsyncMock()
    sensor = _sensor_with_arrival(mock_emt_client)
    mock_emt_client.get_arrivals.side_effect = _wrapped_error(
        ArrivalsNotFoundError(1234, "No arrival information found for stop 1234")
    )

    await sensor.async_update()

    assert sensor.state is None
    assert sensor.available is True
    attributes = sensor.extra_state_attributes
    assert attributes[ATTR_NEXT_UP] is None
    assert attributes[ATTR_BUS_LATITUDE] is None
    assert "unavailable" not in caplog.text


async def test_async_update_api_error_marks_unavailable(hass: HomeAssistant, caplog) -> None:
    """Any other failure makes the sensor unavailable, logged once per outage, and it recovers."""
    mock_emt_client = AsyncMock()
    sensor = _sensor_with_arrival(mock_emt_client)
    mock_emt_client.get_arrivals.side_effect = _wrapped_error(TimeoutError("read timed out"))

    await sensor.async_update()
    await sensor.async_update()

    assert sensor.available is False
    assert caplog.text.count("EMT Madrid API unavailable for stop 1234") == 1

    mock_updated_line = MagicMock()
    mock_updated_line.line_number = "1"
    mock_updated_line.arrival = 3
    mock_updated_line.next_arrival = None
    mock_updated_stop = MagicMock()
    mock_updated_stop.stop_lines = [mock_updated_line]
    mock_updated_stop.bus_arrivals = []
    mock_emt_client.get_arrivals.side_effect = None
    mock_emt_client.get_arrivals.return_value = mock_updated_stop

    await sensor.async_update()

    assert sensor.available is True
    assert sensor.state == 3
    assert caplog.text.count("EMT Madrid API available again for stop 1234") == 1

