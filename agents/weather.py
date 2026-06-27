from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types

_SKILL = load_skill_from_dir(Path(__file__).parent.parent / "skills" / "weather")


def build_weather_agent() -> Agent:
    return Agent(
        name=_SKILL.frontmatter.name,
        description=_SKILL.frontmatter.description,
        model=Gemini(
            model="gemini-3.1-flash-lite",
            retry_options=types.HttpRetryOptions(attempts=6),
        ),
        instruction=_SKILL.instructions,
        tools=[
            # Keyless weather MCP (NOAA/NWS + Open-Meteo) run on demand via npx — no vendored code.
            McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="npx",
                        args=["-y", "@dangahagan/weather-mcp@1.8.0"],
                    ),
                ),
                tool_filter=["get_forecast", "get_current_conditions", "search_location"],
            )
        ],
        output_key="weather_signal",
    )
