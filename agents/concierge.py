from dotenv import load_dotenv
load_dotenv()

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
        instruction="""You are the Flight Disruption Concierge.
        When a user asks about a flight's delay or cancellation risk (e.g. "DL ORD->ATL Monday 7am"), parse their query into flight details:
        - carrier: OP_UNIQUE_CARRIER, e.g. "DL" (always uppercase)
        - flight_no: flight number if provided (e.g. "2419" or null if not mentioned)
        - origin: origin airport code, e.g. "ORD" (always uppercase)
        - dest: destination airport code, e.g. "ATL" (always uppercase)
        - day_of_week: day of week (1=Monday ... 7=Sunday)
        - dep_time_blk: departure time block, e.g. "0700-0759"
        
        You MUST call the 'prediction' tool, passing a JSON string representing this FlightContext as the 'request' parameter. Never attempt to guess, stub, or generate the risk assessment values yourself without calling the 'prediction' tool.
        Once you receive the response back from the 'prediction' tool, unwrap any nested structures or wrapper keys.
        Respond to the user in friendly, helpful, human-readable language explaining the flight's delay and cancellation risk details clearly and politely.
        At the end of your response, you MUST append a structured JSON block enclosed in markdown code blocks (```json ... ```) strictly matching the RiskAssessment schema:
        ```json
        {
            "p_delay15": float,
            "p_cancel": float,
            "confidence": float,
            "dominant_cause": "historical(STUB)",
            "explanation": "string explaining the risk details clearly and politely to the user"
        }
        ```
        Ensure the JSON object is valid and flat. Do not include any text inside the code block other than the raw JSON.
        """,
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
