"""Functions for retrieving weather data from the National Weather Service API."""

import os
from datetime import datetime, timezone

import requests

NWS_BASE_URL = "https://api.weather.gov"
DEFAULT_TIMEOUT = 25


def fetch_json(url, params=None, timeout=DEFAULT_TIMEOUT):
    """Fetch JSON from an NWS endpoint."""
    headers = {
        "User-Agent": os.getenv(
            "NWS_USER_AGENT",
            "USDAClosureCall/1.0 (replace-with-contact-email)",
        ),
        "Accept": "application/geo+json",
    }
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_alerts(latitude, longitude):
    """Return active NWS alerts affecting the supplied coordinates."""
    data = fetch_json(
        f"{NWS_BASE_URL}/alerts/active",
        params={"point": f"{latitude},{longitude}"},
    )

    alerts = []
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        alerts.append({
            "id": feature.get("id"),
            "event": properties.get("event"),
            "headline": properties.get("headline"),
            "description": properties.get("description"),
            "instruction": properties.get("instruction"),
            "severity": properties.get("severity"),
            "urgency": properties.get("urgency"),
            "certainty": properties.get("certainty"),
            "status": properties.get("status"),
            "message_type": properties.get("messageType"),
            "affected_areas": properties.get("areaDesc"),
            "effective": properties.get("effective"),
            "onset": properties.get("onset"),
            "expires": properties.get("expires"),
            "sent": properties.get("sent"),
            "sender": properties.get("senderName"),
        })

    return alerts


def _measurement_value(measurement):
    """Extract a measurement's value while preserving null readings."""
    if not isinstance(measurement, dict):
        return None
    return measurement.get("value")


def _parse_observation(properties):
    """Normalize a latest-observation response into useful fields."""
    return {
        "timestamp": properties.get("timestamp"),
        "temperature": _measurement_value(properties.get("temperature")),
        "temperature_unit": (
            properties.get("temperature", {}).get("unitCode")
            if isinstance(properties.get("temperature"), dict) else None
        ),
        "wind_speed": _measurement_value(properties.get("windSpeed")),
        "wind_gust": _measurement_value(properties.get("windGust")),
        "visibility": _measurement_value(properties.get("visibility")),
        "conditions": properties.get("textDescription"),
        "precipitation_last_hour": _measurement_value(
            properties.get("precipitationLastHour")
        ),
    }


def fetch_weather(latitude, longitude):
    """Retrieve forecast, hourly forecast, and latest available observation."""
    point_url = f"{NWS_BASE_URL}/points/{latitude},{longitude}"
    point_data = fetch_json(point_url)
    point_properties = point_data.get("properties", {})

    forecast_url = point_properties.get("forecast")
    hourly_forecast_url = point_properties.get("forecastHourly")
    stations_url = point_properties.get("observationStations")

    if not forecast_url or not hourly_forecast_url or not stations_url:
        raise ValueError(
            "The NWS points response did not include all required weather URLs."
        )

    forecast_data = fetch_json(forecast_url)
    hourly_data = fetch_json(hourly_forecast_url)
    station_data = fetch_json(stations_url)

    stations = []
    for feature in station_data.get("features", []):
        station_properties = feature.get("properties", {})
        stations.append({
            "id": station_properties.get("stationIdentifier"),
            "name": station_properties.get("name"),
            "url": feature.get("id") or station_properties.get("@id"),
        })

    observation = None
    if stations:
        station_url = stations[0]["url"]
        if station_url:
            observation_data = fetch_json(f"{station_url}/observations/latest")
            observation = _parse_observation(
                observation_data.get("properties", {})
            )

    return {
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "grid_id": point_properties.get("gridId"),
            "grid_x": point_properties.get("gridX"),
            "grid_y": point_properties.get("gridY"),
            "forecast_office": point_properties.get("forecastOffice"),
            "forecast_zone": point_properties.get("forecastZone"),
            "county": point_properties.get("county"),
        },
        "forecast": forecast_data.get("properties", {}).get("periods", []),
        "hourly_forecast": hourly_data.get("properties", {}).get("periods", []),
        "observation": observation,
        "observation_stations": stations,
        "sources": [
            point_url,
            forecast_url,
            hourly_forecast_url,
            stations_url,
        ],
    }


def build_weather_report(facility, manager_inputs=None):
    """
    Build a weather report for a selected facility.

    `facility` may be a dictionary or an object with matching attributes.
    Expected facility fields include id, name, address, latitude, and longitude.
    """
    manager_inputs = manager_inputs or {}

    def get_field(name, default=None):
        if isinstance(facility, dict):
            return facility.get(name, default)
        return getattr(facility, name, default)

    latitude = get_field("latitude")
    longitude = get_field("longitude")
    if latitude is None or longitude is None:
        raise ValueError("The selected facility must have latitude and longitude.")

    alerts = fetch_alerts(latitude, longitude)
    weather = fetch_weather(latitude, longitude)

    facility_data = {
        "id": get_field("id"),
        "name": get_field("name"),
        "address": get_field("address"),
        "latitude": latitude,
        "longitude": longitude,
    }

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "facility": facility_data,
        "manager_update": manager_inputs,
        "alerts": alerts,
        "weather": weather,
        "data_sources": [
            f"{NWS_BASE_URL}/alerts/active?point={latitude},{longitude}",
            *weather["sources"],
        ],
    }
