"""Unit tests for nws_client.py. These tests do not require live NWS access."""

import unittest
from unittest.mock import patch, Mock

import nws_client


class TestFetchAlerts(unittest.TestCase):
    @patch("nws_client.fetch_json")
    def test_fetch_alerts_parses_active_alert(self, mock_fetch_json):
        mock_fetch_json.return_value = {
            "features": [{
                "id": "https://api.weather.gov/alerts/TEST-123",
                "properties": {
                    "event": "Winter Storm Warning",
                    "headline": "Heavy snow expected",
                    "description": "Heavy snow may affect travel.",
                    "instruction": "Avoid unnecessary travel.",
                    "severity": "Severe",
                    "urgency": "Expected",
                    "certainty": "Likely",
                    "status": "Actual",
                    "messageType": "Alert",
                    "areaDesc": "Test County",
                    "effective": "2026-10-10T12:00:00-05:00",
                    "onset": "2026-10-10T14:00:00-05:00",
                    "expires": "2026-10-10T20:00:00-05:00",
                    "sent": "2026-10-10T11:00:00-05:00",
                    "senderName": "National Weather Service",
                },
            }]
        }

        alerts = nws_client.fetch_alerts(40.8, -96.7)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["event"], "Winter Storm Warning")
        self.assertEqual(alerts[0]["severity"], "Severe")
        self.assertEqual(alerts[0]["affected_areas"], "Test County")
        mock_fetch_json.assert_called_once_with(
            f"{nws_client.NWS_BASE_URL}/alerts/active",
            params={"point": "40.8,-96.7"},
        )

    @patch("nws_client.fetch_json")
    def test_fetch_alerts_returns_empty_list(self, mock_fetch_json):
        mock_fetch_json.return_value = {"features": []}

        self.assertEqual(nws_client.fetch_alerts(40.8, -96.7), [])


class TestFetchWeather(unittest.TestCase):
    @patch("nws_client.fetch_json")
    def test_fetch_weather_uses_location_and_parses_responses(self, mock_fetch_json):
        mock_fetch_json.side_effect = [
            {
                "properties": {
                    "forecast": "https://api.weather.gov/forecast/test",
                    "forecastHourly": "https://api.weather.gov/forecast/hourly/test",
                    "observationStations": "https://api.weather.gov/stations/test",
                    "gridId": "TEST",
                    "gridX": 10,
                    "gridY": 20,
                    "forecastOffice": "https://api.weather.gov/offices/TEST",
                    "forecastZone": "https://api.weather.gov/zones/forecast/TEST001",
                    "county": "https://api.weather.gov/zones/county/TEST001",
                }
            },
            {"properties": {"periods": [{"name": "Today", "shortForecast": "Rain"}]}},
            {"properties": {"periods": [{"shortForecast": "Rain", "temperature": 44}]}},
            {
                "features": [{
                    "id": "https://api.weather.gov/stations/KTST",
                    "properties": {
                        "stationIdentifier": "KTST",
                        "name": "Test Airport",
                        "@id": "https://api.weather.gov/stations/KTST",
                    },
                }]
            },
            {
                "properties": {
                    "timestamp": "2026-10-10T12:00:00-05:00",
                    "temperature": {"value": 7.2, "unitCode": "wmoUnit:degC"},
                    "windSpeed": {"value": 15, "unitCode": "wmoUnit:km_h-1"},
                    "windGust": None,
                    "visibility": {"value": 8000, "unitCode": "wmoUnit:m"},
                    "textDescription": "Rain",
                    "precipitationLastHour": {"value": 1.5, "unitCode": "wmoUnit:mm"},
                }
            },
        ]

        weather = nws_client.fetch_weather(40.8, -96.7)

        self.assertEqual(
            mock_fetch_json.call_args_list[0].args[0],
            f"{nws_client.NWS_BASE_URL}/points/40.8,-96.7",
        )
        self.assertEqual(weather["location"]["grid_id"], "TEST")
        self.assertEqual(weather["forecast"][0]["shortForecast"], "Rain")
        self.assertEqual(weather["hourly_forecast"][0]["temperature"], 44)
        self.assertEqual(weather["observation"]["conditions"], "Rain")
        self.assertEqual(weather["observation"]["temperature"], 7.2)
        self.assertEqual(weather["observation_stations"][0]["id"], "KTST")
        self.assertEqual(mock_fetch_json.call_count, 5)

    @patch("nws_client.fetch_json")
    def test_fetch_weather_raises_if_required_urls_missing(self, mock_fetch_json):
        mock_fetch_json.return_value = {"properties": {"gridId": "TEST"}}

        with self.assertRaises(ValueError):
            nws_client.fetch_weather(40.8, -96.7)


class TestBuildWeatherReport(unittest.TestCase):
    @patch("nws_client.fetch_weather")
    @patch("nws_client.fetch_alerts")
    def test_report_combines_facility_and_weather_data(
        self, mock_fetch_alerts, mock_fetch_weather
    ):
        facility = {
            "id": "USDA-TEST-001",
            "name": "Example USDA Facility",
            "address": "100 Main Street, Lincoln, NE",
            "latitude": 40.8,
            "longitude": -96.7,
        }
        manager_inputs = {
            "employees_expected_soon": True,
            "reported_issues": ["Blocked road"],
            "additional_notes": "Use the north entrance.",
        }
        mock_fetch_alerts.return_value = [{"event": "Flood Warning"}]
        mock_fetch_weather.return_value = {
            "location": {"grid_id": "TEST"},
            "forecast": [],
            "hourly_forecast": [],
            "observation": None,
            "observation_stations": [],
            "sources": ["https://api.weather.gov/points/40.8,-96.7"],
        }

        report = nws_client.build_weather_report(facility, manager_inputs)

        self.assertIn("captured_at", report)
        self.assertEqual(report["facility"]["id"], "USDA-TEST-001")
        self.assertEqual(report["alerts"][0]["event"], "Flood Warning")
        self.assertEqual(report["manager_update"], manager_inputs)
        self.assertIn("weather", report)
        mock_fetch_alerts.assert_called_once_with(40.8, -96.7)
        mock_fetch_weather.assert_called_once_with(40.8, -96.7)

    def test_report_requires_facility_coordinates(self):
        with self.assertRaises(ValueError):
            nws_client.build_weather_report({"id": "missing-coordinates"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
