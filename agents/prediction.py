from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.agents import Agent
from agents.custom_agent_tool import HighlightAgentTool
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models import Gemini
from google.genai import types

from common.contracts import RiskAssessment

def build_prediction_agent(prior_specialist, weather_specialist) -> Agent:
    return Agent(
        name="prediction",
        description="Predicts delay and cancellation risk for a flight by consulting the prior risk specialist and the weather specialist.",
        model=Gemini(
            model="gemini-3.1-flash-lite",
            retry_options=types.HttpRetryOptions(attempts=6),
        ),
        instruction=(Path(__file__).parent.parent / "skills" / "prediction" / "SKILL.md").read_text(),
        tools=[HighlightAgentTool(prior_specialist), HighlightAgentTool(weather_specialist)],
        sub_agents=[prior_specialist, weather_specialist],
        output_key="risk_assessment"
    )

prior_remote = RemoteA2aAgent(
    name="prior",
    agent_card="http://localhost:8001" + AGENT_CARD_WELL_KNOWN_PATH,
    description="Calculates historical/prior delay and cancellation risk for a flight query."
)
from agents.weather import build_weather_agent
weather_local = build_weather_agent()

prediction_agent = build_prediction_agent(prior_remote, weather_local)
app = to_a2a(prediction_agent, port=8002)
