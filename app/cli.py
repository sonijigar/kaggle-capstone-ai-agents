import sys
import json
import asyncio
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agents.concierge import concierge_agent
from common.contracts import RiskAssessment

async def run_query(query: str):
    session_service = InMemorySessionService()
    # App name must match the agent directory name ("agents") to align with ADK session management
    app_name = "agents"
    user_id = "user-cli"
    session_id = "session-cli"

    await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    runner = Runner(agent=concierge_agent, app_name=app_name, session_service=session_service)

    response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=query)])
    ):
        if event.error_message:
            print(f"Error from agent '{event.author}': {event.error_message}", file=sys.stderr)
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text and event.is_final_response() and event.author == "concierge":
                    response_text += part.text

    # Parse and validate the response against the RiskAssessment Pydantic model
    import re
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    conversational_part = ""
    if json_match:
        text = json_match.group(1).strip()
        conversational_part = response_text[:json_match.start()].strip()
    else:
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end != -1:
            text = response_text[start:end+1].strip()
            conversational_part = (response_text[:start] + response_text[end+1:]).strip()
        else:
            text = response_text.strip()

    if conversational_part:
        print("\n--- Concierge Response ---")
        print(conversational_part)
        print("--------------------------")


    try:
        data = json.loads(text)
        # Unwrap nested response if present (e.g. from A2A sub-agent wrapper)
        if isinstance(data, dict):
            for key in ["predict_prior_response", "prediction_response", "prior_response"]:
                if key in data and isinstance(data[key], dict):
                    data = data[key]
                    break
            # Also check if there's any single-key wrapper containing our expected fields
            if len(data) == 1 and isinstance(list(data.values())[0], dict) and "p_delay15" in list(data.values())[0]:
                data = list(data.values())[0]

        assessment = RiskAssessment.model_validate(data)
        print("\n--- Risk Assessment Result ---")
        print(f"p_delay15:      {assessment.p_delay15}")
        print(f"p_cancel:       {assessment.p_cancel}")
        print(f"confidence:     {assessment.confidence}")
        print(f"dominant_cause: {assessment.dominant_cause}")
        print(f"explanation:    {assessment.explanation}")
        print("------------------------------")
    except Exception as e:
        print(f"\nFailed to parse response as RiskAssessment: {e}")
        print("Raw response received:")
        print(response_text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python app/cli.py \"<flight query>\"")
        sys.exit(1)

    query = sys.argv[1]
    asyncio.run(run_query(query))
