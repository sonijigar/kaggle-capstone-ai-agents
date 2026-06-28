import os

# Shared flight-search MCP service (Streamable HTTP, served by `fli-mcp-http`).
# Local default; override with FLIGHTS_MCP_URL for a deployed server (e.g. Cloud Run).
FLIGHTS_MCP_URL = os.getenv("FLIGHTS_MCP_URL", "http://127.0.0.1:8000/mcp")
