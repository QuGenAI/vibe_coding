# METAR Reader

A Flask web app that fetches live METAR aviation weather reports and translates them into plain English.

## What it does

Enter a 4-letter ICAO airport code (e.g. `KLAX`, `KJFK`, `EGLL`) and the app:

1. Fetches the latest METAR from the [Aviation Weather Center API](https://aviationweather.gov/api/data/metar)
2. Parses every field — wind, visibility, sky conditions, temperature, dewpoint, altimeter, weather phenomena, remarks
3. Displays a plain-English summary alongside structured detail cards

## Project structure

```
project/
├── app.py              # Flask app — one route (GET/POST /)
├── metar_parser.py     # Pure-Python METAR parser (no external deps)
├── templates/
│   └── index.html      # Jinja2 template — dark-theme UI
├── test_app.py         # pytest unit tests (mocks requests + parse_metar)
├── requirements.txt    # Runtime + dev dependencies
└── CLAUDE.md           # Claude Code project instructions
```

## Requirements

- Python 3.10+
- See `requirements.txt` for package dependencies

## Installation

```bash
pip install -r requirements.txt
```

## Running the app

```bash
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Running the tests

```bash
python -m pytest test_app.py -v
```

Tests mock both `requests.get` and `parse_metar` so no network calls are made.

### Test coverage

| Test | Scenario |
|---|---|
| `test_get_index_returns_200` | GET `/` returns HTTP 200 |
| `test_get_index_no_result_or_error` | GET `/` renders no error |
| `test_post_empty_airport_code_returns_error` | Empty input → validation error |
| `test_post_whitespace_only_airport_code_returns_error` | Whitespace-only input → validation error |
| `test_post_valid_airport_returns_result` | Happy path — correct API URL and parser called |
| `test_post_airport_code_uppercased` | Lowercase input is upper-cased before API call |
| `test_post_empty_api_response_returns_error` | Blank API response → "No METAR data found" |
| `test_post_parse_returns_none_returns_error` | Unparseable data → "Could not parse METAR data" |
| `test_post_timeout_returns_error` | `requests.Timeout` → "Request timed out" |
| `test_post_request_exception_returns_error` | `requests.RequestException` → "Failed to fetch weather data" |

## METAR field parsing (`metar_parser.py`)

The parser handles standard METAR format tokens in order:

| Field | Example token | Output |
|---|---|---|
| Report type | `METAR` / `SPECI` | skipped |
| Station ID | `KHIO` | `station` |
| Date/time (UTC) | `121553Z` | `time_utc` |
| Auto/correction flag | `AUTO` / `COR` | skipped |
| Wind | `27008KT`, `VRB05KT`, `18015G25KT` | `wind` (knots + mph, cardinal direction) |
| Variable wind direction | `160V220` | skipped |
| Visibility | `10SM`, `3/4SM`, `9999`, `CAVOK` | `visibility` |
| Runway visual range | `R28L/2400FT` | skipped |
| Present weather | `-RA`, `+TSRA`, `FZFG` | `weather` (human-readable) |
| Sky conditions | `FEW030`, `BKN010CB`, `OVC025`, `SKC` | `sky` |
| Temp / dewpoint | `15/03`, `M02/M08` | `temperature_*`, `dewpoint_*` (°C and °F) |
| Altimeter | `A2992`, `Q1013` | `altimeter` (inHg or hPa) |
| Remarks | `RMK AO2 SLP012` | `remarks` |

The `build_summary` function combines sky condition, weather phenomena, temperature, wind, and visibility into a single readable sentence.

## ICAO airport code examples

| Code | Airport |
|---|---|
| `KLAX` | Los Angeles International |
| `KJFK` | John F. Kennedy International |
| `KHIO` | Portland / Hillsboro |
| `EGLL` | London Heathrow |
| `YSSY` | Sydney Kingsford Smith |
