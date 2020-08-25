import requests
import json
import math

import logging

import voluptuous as vol

"""Platform for sensor integration."""
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_MODE, HTTP_OK, TIME_MINUTES
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

CONF_EMT_EMAIL = "emt_email"
CONF_EMT_PASSWORD = "emt_password"
CONF_STOP = "stop"
CONF_LINE = "line"

BASE_URL = "https://openapi.emtmadrid.es/"
ENDPOINT_LOGIN = "v1/mobilitylabs/user/login/"
ENDPOINT_ARRIVAL_TIME = "v2/transport/busemtmad/stops/"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_EMT_EMAIL): cv.string,
        vol.Required(CONF_EMT_PASSWORD): cv.string,
        vol.Required(CONF_STOP): cv.string,
        vol.Required(CONF_LINE): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    email = config.get(CONF_EMT_EMAIL)
    password = config.get(CONF_EMT_PASSWORD)
    stop = config.get(CONF_STOP)
    line = config.get(CONF_LINE)
    emt_api = EMTLogin(email, password)
    bus_stop = BusStop(emt_api, stop, line)
    add_entities([BusStopSensor(emt_api, bus_stop)])


class BusStopSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, emt_api, bus_stop):
        """Initialize the sensor."""
        self._state = None
        self._emt_api = emt_api
        self._bus_stop = bus_stop

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Example Temperature"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TIME_MINUTES

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._bus_stop.stop_arrival_time()[0]


class EMTLogin:
    """
    Interface for the EMT REST API from https://apidocs.emtmadrid.es/
    """

    def __init__(self, user, password):
        self._user = user
        self._password = password
        self.token = self.update_token()
        # self.token = Throttle(10000)(self.update_token)

    def api_call(self, url, headers, payload=None, method="POST"):
        if method == "POST":
            payload = json.dumps(payload)
            response = requests.post(url, data=payload, headers=headers)

        elif method == "GET":
            response = requests.get(url, headers=headers)

        else:
            raise Exception("Invalid method: " + method)

        if response.status_code != 200:
            raise Exception("HTTP status: " + str(response.status_code))
        return response.json()

    def update_token(self):
        headers = {"email": self._user, "password": self._password}
        url = BASE_URL + ENDPOINT_LOGIN
        response = self.api_call(url, headers, None, "GET")
        code = response["code"]
        if code == "01":
            self.token = response["data"][0]["accessToken"]
        return self.token

    def check_result(self, response):
        pass

    def check_token_expiration(self):
        pass


class BusStop:
    """
    Bus stop object
    """

    def __init__(self, emt_login, stop, line):
        self.emt_login = emt_login
        self.stop = stop
        self.line = line
        self.token = self.emt_login.token

    def stop_arrival_time(self):
        url = BASE_URL + ENDPOINT_ARRIVAL_TIME + self.stop + "/arrives/"
        headers = {"accessToken": self.emt_login.token}
        data = {"stopId": self.stop, "Text_EstimationsRequired_YN": "Y"}
        response = self.emt_login.api_call(url, headers, data)
        arrival_time = []

        for bus in response["data"][0]["Arrive"]:
            estimated_time = math.trunc(bus["estimateArrive"] / 60)
            if estimated_time > 30:
                estimated_time = 30
            arrival_time.append(estimated_time)
        return arrival_time
