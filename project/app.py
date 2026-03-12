import requests
from flask import Flask, render_template, request
from metar_parser import parse_metar

app = Flask(__name__)

API_URL = "https://aviationweather.gov/api/data/metar?ids={}"


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    airport_code = ""

    if request.method == "POST":
        airport_code = request.form.get("airport_code", "").strip().upper()
        if not airport_code:
            error = "Please enter an airport code."
        else:
            try:
                resp = requests.get(API_URL.format(airport_code), timeout=10)
                resp.raise_for_status()
                raw = resp.text.strip()
                if raw:
                    result = parse_metar(raw)
                    if result is None:
                        error = f"Could not parse METAR data for '{airport_code}'."
                else:
                    error = (
                        f"No METAR data found for '{airport_code}'. "
                        "Please check the airport code (use ICAO format, e.g. KHIO, KLAX, EGLL)."
                    )
            except requests.Timeout:
                error = "Request timed out. Please try again."
            except requests.RequestException as exc:
                error = f"Failed to fetch weather data: {exc}"

    return render_template("index.html", result=result, error=error, airport_code=airport_code)


if __name__ == "__main__":
    app.run(debug=True)
