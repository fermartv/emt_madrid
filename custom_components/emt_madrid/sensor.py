import requests
import json
import math

import logging

import voluptuous as vol

"""Platform for sensor integration."""
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_EMAIL,
    CONF_ICON,
    CONF_MODE,
    CONF_NAME,
    CONF_PASSWORD,
    HTTP_OK,
    TIME_MINUTES,
)

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

ATTRIBUTION = "Data provided by EMT Madrid MobilityLabs"

CONF_STOP = "stop"
CONF_LINE = "line"

DEFAULT_NAME = "EMT Madrid"
DEFAULT_ICON = "mdi:bus"

ATTR_NEXT_UP = "later_bus"
ATTR_BUS_STOP = "bus_stop_id"
ATTR_BUS_LINE = "bus_line"

BASE_URL = "https://openapi.emtmadrid.es/"
ENDPOINT_LOGIN = "v1/mobilitylabs/user/login/"
ENDPOINT_ARRIVAL_TIME = "v2/transport/busemtmad/stops/"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_STOP): cv.string,
        vol.Required(CONF_LINE): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    email = config.get(CONF_EMAIL)
    password = config.get(CONF_PASSWORD)
    bus_stop = config.get(CONF_STOP)
    line = config.get(CONF_LINE)
    name = config.get(CONF_NAME)
    icon = config.get(CONF_ICON)
    api_emt = APIEMT(email, password)
    api_emt.update(bus_stop, line)
    add_entities([BusStopSensor(api_emt, bus_stop, line, name, icon)])


class BusStopSensor(Entity):
    """Implementation of an EMT-Madrid bus stop sensor."""

    def __init__(self, api_emt, bus_stop, line, name, icon):
        """Initialize the sensor."""
        self._state = None
        self._api_emt = api_emt
        self._bus_stop = bus_stop
        self._bus_line = line
        self._icon = icon
        self._name = name
        if self._name == DEFAULT_NAME:
            self._name = "Next {} at {}".format(self._bus_line, self._bus_stop)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._api_emt.get_stop_data(self._bus_line, "arrival")

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TIME_MINUTES

    @property
    def icon(self):
        """Return sensor specific icon."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        return {
            ATTR_NEXT_UP: self._api_emt.get_stop_data(self._bus_line, "next_arrival"),
            ATTR_BUS_STOP: self._bus_stop,
            ATTR_BUS_LINE: self._bus_line,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    def update(self):
        """Fetch new state data for the sensor."""
        self._api_emt.update(self._bus_stop, self._bus_line)


class APIEMT:
    """
    Interface for the EMT REST API from https://apidocs.emtmadrid.es/
    """

    def __init__(self, user, password):
        self._user = user
        self._password = password
        self.token = self.update_token()

    def update(self, stop, line=None):
        url = "{}{}{}/arrives/{}/".format(BASE_URL, ENDPOINT_ARRIVAL_TIME, stop, line)
        headers = {"accessToken": self.token}
        data = {"stopId": stop, "lineArrive": line, "Text_EstimationsRequired_YN": "Y"}
        response = self.api_call(url, headers, data)
        self.set_stop_data(response)

    def set_stop_data(self, data):
        arrival_data = {}

        for bus in data["data"][0]["Arrive"]:
            estimated_time = math.trunc(bus["estimateArrive"] / 60)
            if estimated_time > 30:
                estimated_time = 30
            line = bus["line"]
            if line not in arrival_data:
                arrival_data[line] = {"arrival": estimated_time}
            elif "next_arrival" not in arrival_data[line]:
                arrival_data[line]["next_arrival"] = estimated_time
        self._arrival_time = arrival_data

    def get_stop_data(self, line, bus):
        """ Get the data of the next bus ("arrival") or the one after that ("next_arrival") """
        return self._arrival_time[str(line)][bus]

    def api_call(self, url, headers, payload=None, method="POST"):
        if method == "POST":
            payload = json.dumps(payload)
            response = requests.post(url, data=payload, headers=headers)

        elif method == "GET":
            response = requests.get(url, headers=headers)

        else:
            raise Exception("Invalid HTTP method: " + method)

        if response.status_code != 200:
            _LOGGER.error("Invalid response: %s", response.status_code)
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

