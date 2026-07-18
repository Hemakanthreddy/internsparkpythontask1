"""
Weather Explorer
-----------------
Fetches current weather data using the `requests` module and the free
Open-Meteo API (no API key required), parses the JSON response, and lets
you search for a city and filter matches by country/region when a city
name is ambiguous (e.g. "Springfield" matches many places).

Two API calls are made:
  1. Geocoding API  -> turns a city name into lat/lon (+ search/filter step)
  2. Forecast API   -> turns lat/lon into current weather conditions

Usage examples:
    python weather_explorer.py Hyderabad
    python weather_explorer.py Springfield --country US
    python weather_explorer.py London --units imperial
    python weather_explorer.py Paris --admin1 Texas
"""

import argparse
import sys
import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes -> human-readable description
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def search_city(name: str, country: str = None, admin1: str = None) -> list[dict]:
    """Search for a city by name, optionally filtered by country or region."""
    params = {"name": name, "count": 10, "language": "en", "format": "json"}
    response = requests.get(GEOCODE_URL, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()  # parse JSON response
    results = data.get("results", [])

    if not results:
        print(f"No location found matching '{name}'.")
        sys.exit(1)

    if country:
        results = [r for r in results if r.get("country_code", "").lower() == country.lower()]
    if admin1:
        results = [r for r in results if admin1.lower() in (r.get("admin1") or "").lower()]

    if not results:
        print(f"No match for '{name}' with the given country/region filter.")
        sys.exit(1)

    return results


def fetch_weather(latitude: float, longitude: float, units: str = "metric") -> dict:
    """Fetch current weather for given coordinates."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": True,
        "temperature_unit": "fahrenheit" if units == "imperial" else "celsius",
        "windspeed_unit": "mph" if units == "imperial" else "kmh",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()  # parse JSON response


def display_weather(place: dict, weather_data: dict, units: str) -> None:
    """Pretty-print the location + current weather."""
    current = weather_data.get("current_weather", {})
    temp_unit = "°F" if units == "imperial" else "°C"
    wind_unit = "mph" if units == "imperial" else "km/h"

    label = place.get("name", "Unknown")
    region = place.get("admin1")
    country = place.get("country", "")
    location = f"{label}, {region + ', ' if region else ''}{country}"

    code = current.get("weathercode")
    description = WEATHER_CODES.get(code, "Unknown conditions")

    print("=" * 44)
    print(f"Weather for: {location}")
    print("=" * 44)
    print(f"Condition:    {description}")
    print(f"Temperature:  {current.get('temperature')}{temp_unit}")
    print(f"Wind speed:   {current.get('windspeed')} {wind_unit}")
    print(f"Wind dir:     {current.get('winddirection')}°")
    print(f"Observed at:  {current.get('time')}")
    print("=" * 44)


def choose_match(matches: list[dict]) -> dict:
    """If multiple cities match, let the user pick one; else auto-select."""
    if len(matches) == 1:
        return matches[0]

    print(f"Found {len(matches)} matching locations:")
    for i, m in enumerate(matches, start=1):
        region = m.get("admin1")
        print(f"  {i}. {m.get('name')}, {region + ', ' if region else ''}{m.get('country')}")

    while True:
        choice = input(f"Select a location [1-{len(matches)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            return matches[int(choice) - 1]
        print("Invalid choice, try again.")


def main():
    parser = argparse.ArgumentParser(
        description="Search for a city and fetch its current weather."
    )
    parser.add_argument("city", help="City name to search for")
    parser.add_argument("--country", help="Filter by ISO country code (e.g. US, IN, GB)")
    parser.add_argument("--admin1", help="Filter by state/region name (e.g. Texas)")
    parser.add_argument("--units", choices=["metric", "imperial"], default="metric",
                         help="Units for temperature/wind speed (default: metric)")

    args = parser.parse_args()

    print(f"Searching for '{args.city}'...\n")
    matches = search_city(args.city, country=args.country, admin1=args.admin1)
    place = choose_match(matches)

    print(f"\nFetching current weather for {place.get('name')}...\n")
    weather_data = fetch_weather(place["latitude"], place["longitude"], units=args.units)

    display_weather(place, weather_data, args.units)


if __name__ == "__main__":
    main()
