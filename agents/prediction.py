from dotenv import load_dotenv
load_dotenv()

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.agents import Agent
from agents.custom_agent_tool import HighlightAgentTool
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models import Gemini
from google.genai import types

from common.contracts import RiskAssessment

def build_prediction_agent(prior_specialist) -> Agent:
    return Agent(
        name="prediction",
        description="Predicts delay and cancellation risk for a flight by consulting the prior risk specialist.",
        model=Gemini(
            model="gemini-3.1-flash-lite",
            retry_options=types.HttpRetryOptions(attempts=6),
        ),
        instruction="""You are the Prediction Specialist.
        You will receive flight details.
        You MUST call the 'prior' tool, passing the received flight details as the 'request' parameter. Never attempt to guess, stub, or generate the predictions yourself without calling the 'prior' tool.
        Do not generate your own predictions or explanations; rely entirely on the response returned by the 'prior' tool.
        You MUST copy the exact numeric values from the prior specialist's response (such as p_delay15, p_cancel, confidence, dominant_cause, and explanation) and output them exactly as a RiskAssessment. Do not recompute, modify, or change the values.
        If the response from the 'prior' tool is nested under a key, you MUST unwrap/flatten it.
        Format your final response strictly as a flat JSON object matching the RiskAssessment schema at the root level:
        {
            "p_delay15": float,
            "p_cancel": float,
            "confidence": float,
            "dominant_cause": "historical(STUB)",
            "explanation": "string"
        }
        Do not add any other conversational text or markdown formatting around the JSON object.
        """,
        tools=[HighlightAgentTool(prior_specialist)],
        sub_agents=[prior_specialist],
        output_key="risk_assessment"
    )

prior_remote = RemoteA2aAgent(
    name="prior",
    agent_card="http://localhost:8001" + AGENT_CARD_WELL_KNOWN_PATH,
    description="Calculates historical/prior delay and cancellation risk for a flight query."
)
prediction_agent = build_prediction_agent(prior_remote)
app = to_a2a(prediction_agent, port=8002)
