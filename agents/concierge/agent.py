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

def build_concierge_agent(prediction_specialist) -> Agent:
    return Agent(
        name="concierge",
        description="User-facing Flight Disruption Concierge agent.",
        model=Gemini(
            model="gemini-3.1-flash-lite",
            retry_options=types.HttpRetryOptions(attempts=6),
        ),
        instruction=(Path(__file__).parent / "instruction.md").read_text(),
        tools=[HighlightAgentTool(prediction_specialist)],
        sub_agents=[prediction_specialist],
        output_key="final_answer"
    )

prediction_remote = RemoteA2aAgent(
    name="prediction",
    agent_card="http://localhost:8002" + AGENT_CARD_WELL_KNOWN_PATH,
    description="Predicts delay and cancellation risk for a flight by consulting the prior risk specialist."
)
concierge_agent = build_concierge_agent(prediction_remote)
