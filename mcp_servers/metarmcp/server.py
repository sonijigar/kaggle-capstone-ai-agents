#!/usr/bin/env python3
"""
METAR Weather Parser MCP Server

Provides tools for fetching, parsing, and caching METAR weather data.
"""

import asyncio
import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configuration
CACHE_DB_PATH = Path.home() / ".metar_cache.db"
CACHE_TTL_MINUTES = 30
NOAA_METAR_API = "https://aviationweather.gov/api/data/metar"
NOAA_TAF_API = "https://aviationweather.gov/api/data/taf"


class MetarCache:
    """SQLite-based cache for METAR data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the cache database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metar_cache (
                icao_code TEXT PRIMARY KEY,
                raw_metar TEXT NOT NULL,
                parsed_data TEXT NOT NULL,
                cached_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS taf_cache (
                icao_code TEXT PRIMARY KEY,
                raw_taf TEXT NOT NULL,
                parsed_data TEXT NOT NULL,
                cached_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get(self, icao_code: str) -> Optional[dict]:
        """Get cached METAR data if fresh."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT raw_metar, parsed_data, cached_at FROM metar_cache WHERE icao_code = ?",
            (icao_code.upper(),)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        raw_metar, parsed_data, cached_at = row
        cached_time = datetime.fromisoformat(cached_at)

        # Check if cache is still fresh
        if datetime.now() - cached_time > timedelta(minutes=CACHE_TTL_MINUTES):
            return None

        return {
            "raw_metar": raw_metar,
            "parsed_data": json.loads(parsed_data),
            "cached_at": cached_at
        }

    def set(self, icao_code: str, raw_metar: str, parsed_data: dict):
        """Store METAR data in cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO metar_cache (icao_code, raw_metar, parsed_data, cached_at)
            VALUES (?, ?, ?, ?)
            """,
            (icao_code.upper(), raw_metar, json.dumps(parsed_data), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_taf(self, icao_code: str) -> Optional[dict]:
        """Get cached TAF data if fresh."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT raw_taf, parsed_data, cached_at FROM taf_cache WHERE icao_code = ?",
            (icao_code.upper(),)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        raw_taf, parsed_data, cached_at = row
        cached_time = datetime.fromisoformat(cached_at)

        if datetime.now() - cached_time > timedelta(minutes=CACHE_TTL_MINUTES):
            return None

        return {
            "raw_taf": raw_taf,
            "parsed_data": json.loads(parsed_data),
            "cached_at": cached_at
        }

    def set_taf(self, icao_code: str, raw_taf: str, parsed_data: dict):
        """Store TAF data in cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO taf_cache (icao_code, raw_taf, parsed_data, cached_at)
            VALUES (?, ?, ?, ?)
            """,
            (icao_code.upper(), raw_taf, json.dumps(parsed_data), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()


class MetarParser:
    """Parse raw METAR strings into structured data."""

    @staticmethod
    def parse(metar: str) -> dict:
        """Parse a METAR string into structured JSON."""
        metar = metar.strip()
        result = {
            "raw": metar,
            "station": None,
            "time": None,
            "wind": {},
            "visibility": None,
            "temperature": None,
            "dewpoint": None,
            "pressure_hPa": None,
            "clouds": []
        }

        parts = metar.split()
        if not parts:
            return result

        # Handle METAR keyword if present
        if parts and parts[0] == "METAR":
            parts = parts[1:]

        # Station code (ICAO)
        if parts and re.match(r'^[A-Z]{4}$', parts[0]):
            result["station"] = parts[0]
            parts = parts[1:]

        # Time
        if parts and re.match(r'^\d{6}Z$', parts[0]):
            result["time"] = parts[0]
            parts = parts[1:]

        # Wind
        if parts:
            wind_match = re.match(r'^(\d{3}|VRB)(\d{2,3})(G(\d{2,3}))?(KT|MPS|KMH)?$', parts[0])
            if wind_match:
                direction = wind_match.group(1)
                result["wind"]["direction"] = direction if direction == "VRB" else int(direction)
                result["wind"]["speed_kt"] = int(wind_match.group(2))
                if wind_match.group(4):
                    result["wind"]["gust_kt"] = int(wind_match.group(4))
                parts = parts[1:]

        # Visibility
        if parts:
            vis_match = re.match(r'^(\d{4})|(\d+SM)|(\d+KM)$', parts[0])
            if vis_match:
                result["visibility"] = parts[0]
                parts = parts[1:]

        # Weather phenomena, clouds, etc.
        temp_dew_found = False
        for i, part in enumerate(parts):
            # Temperature/Dewpoint
            temp_match = re.match(r'^(M?\d{2})/(M?\d{2})?$', part)
            if temp_match and not temp_dew_found:
                temp_str = temp_match.group(1)
                result["temperature"] = int(temp_str.replace('M', '-'))
                if temp_match.group(2):
                    dew_str = temp_match.group(2)
                    result["dewpoint"] = int(dew_str.replace('M', '-'))
                temp_dew_found = True
                continue

            # Pressure (QNH)
            pressure_match = re.match(r'^(Q|A)(\d{4})$', part)
            if pressure_match:
                pressure_value = int(pressure_match.group(2))
                if pressure_match.group(1) == 'Q':
                    result["pressure_hPa"] = pressure_value
                else:  # Altimeter setting in inHg
                    result["pressure_hPa"] = int(pressure_value * 0.33864)
                continue

            # Clouds
            cloud_match = re.match(r'^(FEW|SCT|BKN|OVC)(\d{3})', part)
            if cloud_match:
                result["clouds"].append(part)

        return result


class HumanReadableFormatter:
    """Format parsed METAR/TAF data into human-readable text."""

    @staticmethod
    def format_metar(parsed: dict) -> dict:
        """Convert parsed METAR to human-readable format."""
        result = {
            "raw": parsed.get("raw", ""),
            "station": parsed.get("station"),
            "observation_time": HumanReadableFormatter._format_time(parsed.get("time")),
            "wind": HumanReadableFormatter._format_wind(parsed.get("wind", {})),
            "visibility": HumanReadableFormatter._format_visibility(parsed.get("visibility")),
            "weather": HumanReadableFormatter._format_weather(parsed.get("weather", [])),
            "clouds": HumanReadableFormatter._format_clouds(parsed.get("clouds", [])),
            "temperature": HumanReadableFormatter._format_temperature(parsed.get("temperature")),
            "dewpoint": HumanReadableFormatter._format_temperature(parsed.get("dewpoint")),
            "pressure": HumanReadableFormatter._format_pressure(parsed.get("pressure_hPa")),
        }
        return result

    @staticmethod
    def _format_time(time_str: Optional[str]) -> str:
        """Format observation time."""
        if not time_str:
            return "Unknown"
        # Format: DDHHmmZ -> "Day DD at HH:mm UTC"
        if len(time_str) == 7 and time_str.endswith('Z'):
            day = time_str[0:2]
            hour = time_str[2:4]
            minute = time_str[4:6]
            return f"Day {day} at {hour}:{minute} UTC"
        return time_str

    @staticmethod
    def _format_wind(wind: dict) -> str:
        """Format wind information."""
        if not wind:
            return "Calm"

        direction = wind.get("direction")
        speed = wind.get("speed_kt")
        gust = wind.get("gust_kt")

        if direction == "VRB":
            wind_str = f"Variable at {speed} knots"
        elif isinstance(direction, int):
            wind_str = f"From {direction}° at {speed} knots"
        else:
            return "Unknown"

        if gust:
            wind_str += f", gusting to {gust} knots"

        return wind_str

    @staticmethod
    def _format_visibility(visibility: Optional[str]) -> str:
        """Format visibility."""
        if not visibility:
            return "Unknown"

        if visibility == "9999":
            return "Greater than 10 km (excellent)"
        elif "SM" in visibility:
            miles = visibility.replace("SM", "")
            return f"{miles} statute miles"
        elif "KM" in visibility:
            return visibility.replace("KM", " kilometers")
        elif visibility.isdigit():
            meters = int(visibility)
            if meters >= 1000:
                return f"{meters/1000:.1f} km"
            return f"{meters} meters"

        return visibility

    @staticmethod
    def _format_weather(weather: list) -> str:
        """Format weather phenomena."""
        if not weather:
            return "None reported"
        return ", ".join(weather)

    @staticmethod
    def _format_clouds(clouds: list) -> str:
        """Format cloud layers."""
        if not clouds:
            return "Clear skies"

        cloud_descriptions = {
            "FEW": "Few clouds",
            "SCT": "Scattered clouds",
            "BKN": "Broken clouds",
            "OVC": "Overcast"
        }

        formatted = []
        for cloud in clouds:
            match = re.match(r'(FEW|SCT|BKN|OVC)(\d{3})', cloud)
            if match:
                cover = match.group(1)
                altitude = int(match.group(2)) * 100
                desc = cloud_descriptions.get(cover, cover)
                formatted.append(f"{desc} at {altitude:,} feet")

        return ", ".join(formatted) if formatted else "Unknown"

    @staticmethod
    def _format_temperature(temp: Optional[int]) -> str:
        """Format temperature."""
        if temp is None:
            return "Unknown"
        return f"{temp}°C ({temp * 9/5 + 32:.1f}°F)"

    @staticmethod
    def _format_pressure(pressure: Optional[int]) -> str:
        """Format pressure."""
        if pressure is None:
            return "Unknown"
        inhg = pressure / 33.864
        return f"{pressure} hPa ({inhg:.2f} inHg)"


class TAFParser:
    """Parse raw TAF strings into structured data."""

    @staticmethod
    def parse(taf: str) -> dict:
        """Parse a TAF string into structured JSON."""
        taf = taf.strip()
        result = {
            "raw": taf,
            "station": None,
            "issue_time": None,
            "valid_period": None,
            "forecast_periods": []
        }

        lines = taf.split('\n')
        if not lines:
            return result

        # First line contains station, issue time, and valid period
        first_line = lines[0].split()

        # Handle TAF keyword if present
        if first_line and first_line[0] == "TAF":
            first_line = first_line[1:]

        # Station code
        if first_line and re.match(r'^[A-Z]{4}$', first_line[0]):
            result["station"] = first_line[0]
            first_line = first_line[1:]

        # Issue time (DDHHmmZ)
        if first_line and re.match(r'^\d{6}Z$', first_line[0]):
            result["issue_time"] = first_line[0]
            first_line = first_line[1:]

        # Valid period (DDDD/DDDD)
        if first_line and re.match(r'^\d{4}/\d{4}$', first_line[0]):
            result["valid_period"] = first_line[0]

        # Parse forecast periods (simplified - just store raw periods for now)
        full_text = ' '.join(lines)

        # Split by change indicators
        periods = re.split(r'\s+(FM\d{6}|TEMPO|BECMG|PROB\d{2})', full_text)

        if periods:
            # Base forecast is the first period
            result["forecast_periods"].append({
                "type": "BASE",
                "raw": periods[0].strip()
            })

        return result


async def fetch_metar(icao_code: str) -> str:
    """Fetch raw METAR data from NOAA API."""
    url = f"{NOAA_METAR_API}?ids={icao_code.upper()}&format=raw"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        # NOAA returns raw METAR text
        metar_text = response.text.strip()
        if not metar_text:
            raise ValueError(f"No METAR data found for {icao_code}")

        return metar_text


async def fetch_taf(icao_code: str) -> str:
    """Fetch raw TAF data from NOAA API."""
    url = f"{NOAA_TAF_API}?ids={icao_code.upper()}&format=raw"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        # NOAA returns raw TAF text
        taf_text = response.text.strip()
        if not taf_text:
            raise ValueError(f"No TAF data found for {icao_code}")

        return taf_text


# Initialize components
cache = MetarCache(CACHE_DB_PATH)
parser = MetarParser()
taf_parser = TAFParser()
formatter = HumanReadableFormatter()
app = Server("metar-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available METAR and TAF tools."""
    return [
        Tool(
            name="fetch_metar",
            description="Fetch raw METAR weather data for an airport by ICAO code",
            inputSchema={
                "type": "object",
                "properties": {
                    "icao_code": {
                        "type": "string",
                        "description": "ICAO airport code (e.g., EFHK, KJFK, EGLL)",
                        "pattern": "^[A-Z]{4}$"
                    }
                },
                "required": ["icao_code"]
            }
        ),
        Tool(
            name="parse_metar",
            description="Parse a raw METAR string into structured JSON data",
            inputSchema={
                "type": "object",
                "properties": {
                    "metar": {
                        "type": "string",
                        "description": "Raw METAR string to parse"
                    }
                },
                "required": ["metar"]
            }
        ),
        Tool(
            name="get_cached_metar",
            description="Get cached METAR data for an airport (fetches if cache is stale or missing). Cache TTL: 30 minutes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "icao_code": {
                        "type": "string",
                        "description": "ICAO airport code (e.g., EFHK, KJFK, EGLL)",
                        "pattern": "^[A-Z]{4}$"
                    }
                },
                "required": ["icao_code"]
            }
        ),
        Tool(
            name="get_metar_human_readable",
            description="Get METAR data in human-readable format with descriptions (e.g., 'From 180° at 12 knots' instead of '18012KT')",
            inputSchema={
                "type": "object",
                "properties": {
                    "icao_code": {
                        "type": "string",
                        "description": "ICAO airport code (e.g., EFHK, KJFK, EGLL)",
                        "pattern": "^[A-Z]{4}$"
                    }
                },
                "required": ["icao_code"]
            }
        ),
        Tool(
            name="fetch_taf",
            description="Fetch raw TAF (Terminal Aerodrome Forecast) data for an airport by ICAO code",
            inputSchema={
                "type": "object",
                "properties": {
                    "icao_code": {
                        "type": "string",
                        "description": "ICAO airport code (e.g., EFHK, KJFK, EGLL)",
                        "pattern": "^[A-Z]{4}$"
                    }
                },
                "required": ["icao_code"]
            }
        ),
        Tool(
            name="parse_taf",
            description="Parse a raw TAF string into structured JSON data",
            inputSchema={
                "type": "object",
                "properties": {
                    "taf": {
                        "type": "string",
                        "description": "Raw TAF string to parse"
                    }
                },
                "required": ["taf"]
            }
        ),
        Tool(
            name="get_cached_taf",
            description="Get cached TAF data for an airport (fetches if cache is stale or missing). Cache TTL: 30 minutes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "icao_code": {
                        "type": "string",
                        "description": "ICAO airport code (e.g., EFHK, KJFK, EGLL)",
                        "pattern": "^[A-Z]{4}$"
                    }
                },
                "required": ["icao_code"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    if name == "fetch_metar":
        icao_code = arguments["icao_code"].upper()
        try:
            raw_metar = await fetch_metar(icao_code)
            return [TextContent(type="text", text=raw_metar)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching METAR: {str(e)}")]

    elif name == "parse_metar":
        metar_string = arguments["metar"]
        try:
            parsed = parser.parse(metar_string)
            return [TextContent(type="text", text=json.dumps(parsed, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error parsing METAR: {str(e)}")]

    elif name == "get_cached_metar":
        icao_code = arguments["icao_code"].upper()
        try:
            # Check cache first
            cached = cache.get(icao_code)
            if cached:
                result = {
                    "source": "cache",
                    "cached_at": cached["cached_at"],
                    "raw_metar": cached["raw_metar"],
                    "parsed_data": cached["parsed_data"]
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            # Fetch fresh data
            raw_metar = await fetch_metar(icao_code)
            parsed = parser.parse(raw_metar)

            # Cache it
            cache.set(icao_code, raw_metar, parsed)

            result = {
                "source": "fresh",
                "raw_metar": raw_metar,
                "parsed_data": parsed
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting METAR: {str(e)}")]

    elif name == "get_metar_human_readable":
        icao_code = arguments["icao_code"].upper()
        try:
            # Check cache first
            cached = cache.get(icao_code)
            if cached:
                parsed = cached["parsed_data"]
            else:
                # Fetch fresh data
                raw_metar = await fetch_metar(icao_code)
                parsed = parser.parse(raw_metar)
                cache.set(icao_code, raw_metar, parsed)

            # Format to human-readable
            human_readable = formatter.format_metar(parsed)
            return [TextContent(type="text", text=json.dumps(human_readable, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting human-readable METAR: {str(e)}")]

    elif name == "fetch_taf":
        icao_code = arguments["icao_code"].upper()
        try:
            raw_taf = await fetch_taf(icao_code)
            return [TextContent(type="text", text=raw_taf)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching TAF: {str(e)}")]

    elif name == "parse_taf":
        taf_string = arguments["taf"]
        try:
            parsed = taf_parser.parse(taf_string)
            return [TextContent(type="text", text=json.dumps(parsed, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error parsing TAF: {str(e)}")]

    elif name == "get_cached_taf":
        icao_code = arguments["icao_code"].upper()
        try:
            # Check cache first
            cached = cache.get_taf(icao_code)
            if cached:
                result = {
                    "source": "cache",
                    "cached_at": cached["cached_at"],
                    "raw_taf": cached["raw_taf"],
                    "parsed_data": cached["parsed_data"]
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            # Fetch fresh data
            raw_taf = await fetch_taf(icao_code)
            parsed = taf_parser.parse(raw_taf)

            # Cache it
            cache.set_taf(icao_code, raw_taf, parsed)

            result = {
                "source": "fresh",
                "raw_taf": raw_taf,
                "parsed_data": parsed
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting TAF: {str(e)}")]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
