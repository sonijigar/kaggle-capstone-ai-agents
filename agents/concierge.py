from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.agents import Agent
from agents.custom_agent_tool import HighlightAgentTool
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.models import Gemini
from google.genai import types
from agents.concierge_tools import resolve_date, resolve_flight_query, book_flight
from agents.planner import build_planner_agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from common.config import FLIGHTS_MCP_URL

_SKILL = load_skill_from_dir(Path(__file__).parent.parent / "skills" / "concierge")

def build_concierge_agent(prediction_specialist, planner_specialist) -> Agent:
    return Agent(
        name=_SKILL.frontmatter.name,
        description=_SKILL.frontmatter.description,
        model=Gemini(
            model="gemini-3.1-flash-lite",
            retry_options=types.HttpRetryOptions(attempts=6),
        ),
        instruction=_SKILL.instructions,
        tools=[
            # Cheap, deterministic lookups go straight to the shared flight-search MCP — no
            # extra agent hop. Used to VALIDATE the user's flight exists (search_flights) and
            # resolve city -> airport code (find_airports).
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(url=FLIGHTS_MCP_URL),
                tool_filter=["search_flights", "find_airports"],
            ),
            # Judgment-heavy search (curate good rebooking alternatives) delegated to the Planner.
            HighlightAgentTool(planner_specialist),
            resolve_date,
            resolve_flight_query,
            HighlightAgentTool(prediction_specialist),
            # HITL gate: pauses for human approval before the (simulated) booking runs.
            FunctionTool(book_flight, require_confirmation=True),
        ],
        sub_agents=[prediction_specialist, planner_specialist],
        output_key="final_answer"
    )

prediction_remote = RemoteA2aAgent(
    name="prediction",
    agent_card="http://localhost:8002" + AGENT_CARD_WELL_KNOWN_PATH,
    description="Predicts delay and cancellation risk for a flight by consulting the prior risk specialist."
)
concierge_agent = build_concierge_agent(prediction_remote, build_planner_agent())
