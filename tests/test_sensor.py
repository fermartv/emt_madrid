"""The tests for the EMT Madrid sensor platform."""


from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

VALID_LOGIN = {
    "code": "01",
    "description": "Token 3bd5855a-ed3d-41d5-8b4b-182726f86031 extend into control-cache Data recovered OK, (lapsed: 468 millsecs)",
    "datetime": "2023-06-29T19:50:08.307475",
    "data": [
        {
            "nameApp": "OPENAPI MobilityLabs",
            "levelApp": 0,
            "updatedAt": "2022-11-26T21:05:55.5600000",
            "userName": "yourusername",
            "lastUpdate": {"$date": 1688057414194},
            "idUser": "2f104b08-f8bf-4199-a4bc-c6ecc42ad6ba",
            "priv": "U",
            "tokenSecExpiration": 86399,
            "email": "yourmail@mail.com",
            "tokenDteExpiration": {"$date": 1688151013194},
            "flagAdvise": True,
            "accessToken": "3bd5855a-ed3d-41d5-8b4b-182726f86031",
            "apiCounter": {
                "current": 96,
                "dailyUse": 20000,
                "owner": 0,
                "licenceUse": "Please mention EMT Madrid MobilityLabs as data source. Thank you and enjoy!",
                "aboutUses": "If you need to extend the daily use of this API, please, register your App in Mobilitylabs and use your own X-ClientId and passKey instead of generic login (more info in https://mobilitylabs.emtmadrid.es/doc/new-app and https://apidocs.emtmadrid.es/#api-Block_1_User_identity-login)",
            },
            "username": "yourusername",
        }
    ],
}

INVALID_USER_LOGIN = {
    "code": "92",
    "description": "Error: User not found (lapsed: 776 millsecs)",
    "datetime": "2023-06-29T20:01:09.441986",
    "data": [],
}

INVALID_PASSWORD_LOGIN = {
    "code": "89",
    "description": "Error: Invalid user or Password (lapsed: 415 millsecs)",
    "datetime": "2023-06-29T20:02:41.901955",
    "data": [],
}

VALID_STOP_AND_LINE_ARRIVALS = {
    "code": "00",
    "description": "Data recovered OK (lapsed: 1155 millsecs)",
    "datetime": "2023-06-29T18:50:13.968932",
    "data": [
        {
            "Arrive": [
                {
                    "line": "27",
                    "stop": "72",
                    "isHead": "False",
                    "destination": "PLAZA CASTILLA",
                    "deviation": 0,
                    "bus": 528,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.69295437941713, 40.41338567959594],
                    },
                    "estimateArrive": 233,
                    "DistanceBus": 674,
                    "positionTypeBus": "0",
                },
                {
                    "line": "5",
                    "stop": "72",
                    "isHead": "False",
                    "destination": "CHAMARTIN",
                    "deviation": 0,
                    "bus": 51,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.6950488592789854, 40.40415447211867],
                    },
                    "estimateArrive": 345,
                    "DistanceBus": 1777,
                    "positionTypeBus": "0",
                },
                {
                    "line": "27",
                    "stop": "72",
                    "isHead": "False",
                    "destination": "PLAZA CASTILLA",
                    "deviation": 0,
                    "bus": 515,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.6950488592789865, 40.40415447211869],
                    },
                    "estimateArrive": 1556,
                    "DistanceBus": 1777,
                    "positionTypeBus": "0",
                },
            ],
            "StopInfo": [],
            "ExtraInfo": [],
            "Incident": {},
        }
    ],
}

INVALID_STOP_ARRIVALS = {
    "code": "80",
    "description": [
        {"ES": "Parada no disponible actualmente o inexistente"},
        {"EN": "Bus Stop disabled or not exists"},
    ],
    "datetime": "2023-06-29T21:34:48.886037",
    "data": [{"Arrive": [], "StopInfo": [], "ExtraInfo": [], "Incident": {}}],
}

VALID_STOP_INFO = {
    "code": "00",
    "description": "Data recovered  OK, (lapsed: 463 millsecs)",
    "datetime": "2023-07-02T15:41:44.008245",
    "data": [
        {
            "stops": [
                {
                    "stop": "72",
                    "name": "Cibeles-Casa de América",
                    "postalAddress": "Pº de Recoletos, 2 (Pza. de Cibeles)",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.69214452424823, 40.4203613685499],
                    },
                    "pmv": "60996",
                    "dataLine": [
                        {
                            "line": "005",
                            "label": "5",
                            "direction": "B",
                            "maxFreq": "33",
                            "minFreq": "16",
                            "headerA": "SOL/SEVILLA",
                            "headerB": "CHAMARTIN",
                            "startTime": "07:00",
                            "stopTime": "22:58",
                            "dayType": "FE",
                        },
                        {
                            "line": "027",
                            "label": "27",
                            "direction": "B",
                            "maxFreq": "25",
                            "minFreq": "11",
                            "headerA": "EMBAJADORES",
                            "headerB": "PLAZA CASTILLA",
                            "startTime": "07:00",
                            "stopTime": "00:01",
                            "dayType": "FE",
                        },
                        {
                            "line": "526",
                            "label": "N26",
                            "direction": "A",
                            "maxFreq": "60",
                            "minFreq": "20",
                            "headerA": "ALONSO MARTINEZ",
                            "headerB": "ALUCHE",
                            "startTime": "00:00",
                            "stopTime": "05:10",
                            "dayType": "FE",
                        },
                    ],
                }
            ]
        }
    ],
}

INVALID_STOP_INFO = {
    "code": "90",
    "description": "Error managing internal services",
    "datetime": "2023-07-02T15:42:55.210432",
    "data": [],
}


def make_request_mock(url, headers=None, data=None, method="POST"):
    """Mock the API request."""
    if url == "https://openapi.emtmadrid.es/v1/mobilitylabs/user/login/":
        if headers["email"] == "invalid@email.com":
            return INVALID_USER_LOGIN
        if headers["password"] == "invalid_password":
            return INVALID_PASSWORD_LOGIN
        return VALID_LOGIN
    if (
        "stopId" in data
        and url
        == f"https://openapi.emtmadrid.es/v2/transport/busemtmad/stops/{data['stopId']}/arrives/"
    ):
        if data["stopId"] == 123456:
            return INVALID_STOP_ARRIVALS
        return VALID_STOP_AND_LINE_ARRIVALS
    if (
        "idStop" in data
        and url
        == f"https://openapi.emtmadrid.es/v1/transport/busemtmad/stops/{data['idStop']}/detail/"
    ):
        if data["idStop"] == 123456:
            return INVALID_STOP_INFO
        return VALID_STOP_INFO
    raise ValueError(f"Invalid URL ({url}) or data ({data})")


@patch(
    "homeassistant.components.emt_madrid.sensor.APIEMT._make_request",
    side_effect=make_request_mock,
)
async def test_valid_config(setup_component, hass: HomeAssistant) -> None:
    """Test the configuration of the emt_madrid component with valid settings."""

    config = {
        "sensor": {
            "platform": "emt_madrid",
            "email": "test@mail.com",
            "password": "password123",
            "stop": 72,
            "lines": ["27"],
            "icon": "mdi:fountain",
        }
    }
    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.bus_27_cibeles_casa_de_america")

    assert state.state == "3"
    assert state.attributes["next_bus"] == 25
    assert state.attributes["stop_id"] == 72
    assert state.attributes["line"] == "27"
    assert state.attributes["attribution"] == "Data provided by EMT Madrid MobilityLabs"
    assert state.attributes["unit_of_measurement"] == "min"
    assert state.attributes["icon"] == "mdi:fountain"
    assert state.attributes["distance"] == 674
    assert state.attributes["destination"] == "PLAZA CASTILLA"
    assert state.attributes["origin"] == "EMBAJADORES"
    assert state.attributes["start_time"] == "07:00"
    assert state.attributes["end_time"] == "00:01"
    assert state.attributes["max_frequency"] == 25
    assert state.attributes["min_frequency"] == 11
    assert state.attributes["stop_name"] == "Cibeles-Casa de América"
    assert state.attributes["stop_address"] == "Pº de Recoletos, 2 (Pza. de Cibeles)"


@patch(
    "homeassistant.components.emt_madrid.sensor.APIEMT._make_request",
    side_effect=make_request_mock,
)
async def test_valid_config_no_lines_specified(
    setup_component, hass: HomeAssistant
) -> None:
    """Test the basic configuration of the emt_madrid component with valid settings."""

    config = {
        "sensor": {
            "platform": "emt_madrid",
            "email": "test@mail.com",
            "password": "password123",
            "stop": 72,
        }
    }
    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.bus_27_cibeles_casa_de_america")

    assert state.state == "3"
    assert state.attributes["next_bus"] == 25
    assert state.attributes["stop_id"] == 72
    assert state.attributes["line"] == "27"
    assert state.attributes["attribution"] == "Data provided by EMT Madrid MobilityLabs"
    assert state.attributes["unit_of_measurement"] == "min"
    assert state.attributes["icon"] == "mdi:bus"
    assert state.attributes["distance"] == 674
    assert state.attributes["destination"] == "PLAZA CASTILLA"
    assert state.attributes["origin"] == "EMBAJADORES"
    assert state.attributes["start_time"] == "07:00"
    assert state.attributes["end_time"] == "00:01"
    assert state.attributes["max_frequency"] == 25
    assert state.attributes["min_frequency"] == 11
    assert state.attributes["stop_name"] == "Cibeles-Casa de América"
    assert state.attributes["stop_address"] == "Pº de Recoletos, 2 (Pza. de Cibeles)"

    state = hass.states.get("sensor.bus_5_cibeles_casa_de_america")

    assert state.state == "5"
    assert state.attributes["next_bus"] is None
    assert state.attributes["stop_id"] == 72
    assert state.attributes["line"] == "5"
    assert state.attributes["attribution"] == "Data provided by EMT Madrid MobilityLabs"
    assert state.attributes["unit_of_measurement"] == "min"
    assert state.attributes["icon"] == "mdi:bus"
    assert state.attributes["distance"] == 1777
    assert state.attributes["destination"] == "CHAMARTIN"
    assert state.attributes["origin"] == "SOL/SEVILLA"
    assert state.attributes["start_time"] == "07:00"
    assert state.attributes["end_time"] == "22:58"
    assert state.attributes["max_frequency"] == 33
    assert state.attributes["min_frequency"] == 16
    assert state.attributes["stop_name"] == "Cibeles-Casa de América"
    assert state.attributes["stop_address"] == "Pº de Recoletos, 2 (Pza. de Cibeles)"

    state = hass.states.get("sensor.bus_n26_cibeles_casa_de_america")

    assert state.state == "unknown"
    assert state.attributes["next_bus"] is None
    assert state.attributes["stop_id"] == 72
    assert state.attributes["line"] == "N26"
    assert state.attributes["attribution"] == "Data provided by EMT Madrid MobilityLabs"
    assert state.attributes["unit_of_measurement"] == "min"
    assert state.attributes["icon"] == "mdi:bus"
    assert state.attributes["distance"] is None
    assert state.attributes["destination"] == "ALONSO MARTINEZ"
    assert state.attributes["origin"] == "ALUCHE"
    assert state.attributes["start_time"] == "00:00"
    assert state.attributes["end_time"] == "05:10"
    assert state.attributes["max_frequency"] == 60
    assert state.attributes["min_frequency"] == 20
    assert state.attributes["stop_name"] == "Cibeles-Casa de América"
    assert state.attributes["stop_address"] == "Pº de Recoletos, 2 (Pza. de Cibeles)"


@patch(
    "homeassistant.components.emt_madrid.sensor.APIEMT._make_request",
    side_effect=make_request_mock,
)
async def test_invalid_user(
    setup_component, hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the configuration of the emt_madrid component with an invalid user."""

    config = {
        "sensor": {
            "platform": "emt_madrid",
            "email": "invalid@email.com",
            "password": "password123",
            "stop": 72,
            "lines": ["27"],
            "icon": "mdi:fountain",
        }
    }
    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()
    assert "Invalid email or password" in caplog.text


@patch(
    "homeassistant.components.emt_madrid.sensor.APIEMT._make_request",
    side_effect=make_request_mock,
)
async def test_invalid_password(
    setup_component, hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the configuration of the emt_madrid component with an invalid password."""

    config = {
        "sensor": {
            "platform": "emt_madrid",
            "email": "test@email.com",
            "password": "invalid_password",
            "stop": 72,
            "lines": ["27"],
            "icon": "mdi:fountain",
        }
    }
    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()
    assert "Invalid email or password" in caplog.text


@patch(
    "homeassistant.components.emt_madrid.sensor.APIEMT._make_request",
    side_effect=make_request_mock,
)
async def test_invalid_stop(
    setup_component, hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the configuration of the emt_madrid component with an invalid bus stop."""

    config = {
        "sensor": {
            "platform": "emt_madrid",
            "email": "test@email.com",
            "password": "password123",
            "stop": 123456,
            "lines": ["27"],
            "icon": "mdi:fountain",
        }
    }
    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()
    assert "Bus stop disabled or does not exist" in caplog.text
