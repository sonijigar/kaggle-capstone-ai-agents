from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types

from common.config import FLIGHTS_MCP_URL

_SKILL = load_skill_from_dir(Path(__file__).parent.parent / "skills" / "planner")


def build_planner_agent() -> Agent:
    return Agent(
        name=_SKILL.frontmatter.name,
        description=_SKILL.frontmatter.description,
        model=Gemini(
            model="gemini-3.1-flash-lite",
            retry_options=types.HttpRetryOptions(attempts=6),
        ),
        instruction=_SKILL.instructions,
        tools=[
            # Shared flight-search MCP over HTTP — one server (fli-mcp-http), many clients.
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(url=FLIGHTS_MCP_URL),
                tool_filter=["search_flights", "find_airports"],
            )
        ],
        output_key="flight_search_result",
    )
