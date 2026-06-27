import sys
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from agents.model import build_model
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types

_SKILL = load_skill_from_dir(Path(__file__).parent.parent / "skills" / "weather")
_METAR_SERVER = str(Path(__file__).parent.parent / "mcp_servers" / "metarmcp" / "server.py")


def build_weather_agent() -> Agent:
    return Agent(
        name=_SKILL.frontmatter.name,
        description=_SKILL.frontmatter.description,
        model=build_model(),
        instruction=_SKILL.instructions,
        tools=[
            McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command=sys.executable,
                        args=[_METAR_SERVER],
                    ),
                ),
                tool_filter=["fetch_metar", "fetch_taf"],
            )
        ],
        output_key="weather_signal",
    )
