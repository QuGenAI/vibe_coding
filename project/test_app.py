import pytest
from unittest.mock import patch, MagicMock
import requests

import app as flask_app


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# GET requests
# ---------------------------------------------------------------------------

def test_get_index_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_get_index_no_result_or_error(client):
    response = client.get("/")
    data = response.data.decode()
    # No error or result rendered on a plain GET
    assert "Please enter an airport code" not in data


# ---------------------------------------------------------------------------
# POST — input validation
# ---------------------------------------------------------------------------

def test_post_empty_airport_code_returns_error(client):
    response = client.post("/", data={"airport_code": ""})
    assert response.status_code == 200
    assert b"Please enter an airport code" in response.data


def test_post_whitespace_only_airport_code_returns_error(client):
    response = client.post("/", data={"airport_code": "   "})
    assert response.status_code == 200
    assert b"Please enter an airport code" in response.data


# ---------------------------------------------------------------------------
# POST — successful fetch and parse
# ---------------------------------------------------------------------------

SAMPLE_METAR = "KHIO 121553Z 27008KT 10SM CLR 15/03 A3001 RMK AO2"

SAMPLE_RESULT = {
    "raw": SAMPLE_METAR,
    "station": "KHIO",
    "time_utc": "Day 12, 15:53 UTC",
    "wind": "Wind from the West (270°) at 8 kt (9 mph)",
    "visibility": "10 miles (excellent)",
    "weather": [],
    "sky": ["Clear skies"],
    "temperature_c": 15,
    "temperature_f": 59,
    "dewpoint_c": 3,
    "dewpoint_f": 37,
    "altimeter": "30.01 inHg",
    "remarks": "AO2",
    "summary": "Clear skies, 59°F (15°C), wind from the West (270°) at 8 kt (9 mph).",
    "error": None,
}


@patch("app.parse_metar")
@patch("app.requests.get")
def test_post_valid_airport_returns_result(mock_get, mock_parse, client):
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_METAR
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    mock_parse.return_value = SAMPLE_RESULT

    response = client.post("/", data={"airport_code": "khio"})

    assert response.status_code == 200
    mock_get.assert_called_once_with(
        "https://aviationweather.gov/api/data/metar?ids=KHIO", timeout=10
    )
    mock_parse.assert_called_once_with(SAMPLE_METAR)


@patch("app.parse_metar")
@patch("app.requests.get")
def test_post_airport_code_uppercased(mock_get, mock_parse, client):
    """Airport code should be upper-cased before use."""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_METAR
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    mock_parse.return_value = SAMPLE_RESULT

    client.post("/", data={"airport_code": "klax"})

    url_called = mock_get.call_args[0][0]
    assert "KLAX" in url_called


# ---------------------------------------------------------------------------
# POST — empty API response
# ---------------------------------------------------------------------------

@patch("app.parse_metar")
@patch("app.requests.get")
def test_post_empty_api_response_returns_error(mock_get, mock_parse, client):
    mock_resp = MagicMock()
    mock_resp.text = "   "  # blank / whitespace only
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    response = client.post("/", data={"airport_code": "ZZZZ"})

    assert response.status_code == 200
    assert b"No METAR data found" in response.data
    mock_parse.assert_not_called()


# ---------------------------------------------------------------------------
# POST — parse_metar returns None
# ---------------------------------------------------------------------------

@patch("app.parse_metar")
@patch("app.requests.get")
def test_post_parse_returns_none_returns_error(mock_get, mock_parse, client):
    mock_resp = MagicMock()
    mock_resp.text = "SOME GARBAGE DATA"
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    mock_parse.return_value = None

    response = client.post("/", data={"airport_code": "XXXX"})

    assert response.status_code == 200
    assert b"Could not parse METAR data" in response.data


# ---------------------------------------------------------------------------
# POST — network errors
# ---------------------------------------------------------------------------

@patch("app.requests.get")
def test_post_timeout_returns_error(mock_get, client):
    mock_get.side_effect = requests.Timeout

    response = client.post("/", data={"airport_code": "KLAX"})

    assert response.status_code == 200
    assert b"Request timed out" in response.data


@patch("app.requests.get")
def test_post_request_exception_returns_error(mock_get, client):
    mock_get.side_effect = requests.RequestException("connection refused")

    response = client.post("/", data={"airport_code": "KLAX"})

    assert response.status_code == 200
    assert b"Failed to fetch weather data" in response.data
