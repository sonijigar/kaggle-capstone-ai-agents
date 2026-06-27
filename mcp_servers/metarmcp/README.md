# METAR MCP Server

MCP server for fetching and parsing METAR aviation weather data from NOAA's Aviation Weather Center.

## Installation

### Poetry (Development)

```bash
poetry install
```

### Docker (Production)

```bash
docker-compose up -d
```

## Usage

### MCP Client Configuration

#### Poetry

Add to your MCP client configuration file:

```json
{
  "mcpServers": {
    "metar": {
      "command": "poetry",
      "args": ["run", "python", "/path/to/metarmcp/server.py"],
      "cwd": "/path/to/metarmcp"
    }
  }
}
```

#### Docker

Add to your MCP client configuration file:

```json
{
  "mcpServers": {
    "metar": {
      "command": "docker",
      "args": ["exec", "-i", "metar-mcp-server", "python", "server.py"]
    }
  }
}
```

### Running Tests

```bash
poetry run pytest test_metar.py -v
```

### Docker Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild
docker-compose up -d --build
```

## Tools

### `fetch_metar`
Fetch raw METAR data for an airport by ICAO code.

**Parameters:**
- `icao_code` (string): Airport code (e.g., EFHK, KJFK, EGLL)

### `parse_metar`
Parse raw METAR string into structured JSON.

**Parameters:**
- `metar` (string): Raw METAR string

**Returns:**
```json
{
  "station": "EFHK",
  "time": "021720Z",
  "wind": {"direction": 180, "speed_kt": 12},
  "visibility": "9999",
  "temperature": 12,
  "dewpoint": 8,
  "pressure_hPa": 1013,
  "clouds": ["FEW020", "BKN050"]
}
```

### `get_cached_metar`
Get METAR data with 30-minute caching.

**Parameters:**
- `icao_code` (string): Airport code

**Returns:**
- Cached data if fresh (<30 min)
- Fresh data from API if cache expired

## Features

- Fetch real-time METAR and TAF data from NOAA
- Parse METAR/TAF into structured JSON
- Human-readable formatting with descriptions
- SQLite caching (30-minute TTL)
- Full test coverage
- Docker support with security best practices

## Data Source

NOAA Aviation Weather Center: https://aviationweather.gov/

## License

MIT
