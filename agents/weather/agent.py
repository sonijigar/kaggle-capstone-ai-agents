from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

async def get_weather(origin: str, dest: str) -> dict:
    """STUB weather until MCP lands (Part 2)."""
    try:
        from agents.custom_agent_tool import parent_ic_var, parent_path_var
        from google.adk.events import Event, EventActions
        
        ic = parent_ic_var.get()
        parent_path = parent_path_var.get()
        if ic and getattr(ic, "_event_queue", None) is not None:
            # ADK natively expects tool call events to use the calling agent's exact path
            tool_node_path = parent_path
            
            tool_event = Event(
                invocation_id=ic.invocation_id,
                author="weather",
                node_path=tool_node_path,
                actions=EventActions(),
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_function_call(
                        name="get_weather",
                        args={"origin": origin, "dest": dest}
                    )]
                )
            )
            import asyncio
            asyncio.create_task(ic._enqueue_event(tool_event))
    except Exception as e:
        print(f"Failed to inject tool event: {e}")

    return {"origin_risk": 0.10, "dest_risk": 0.10,
            "summary": "STUB: clear, light wind", "confidence": 0.4}

def build_weather_agent() -> Agent:
    return Agent(
        name="weather",
        description="Provides weather signals for origin and destination.",
        model=Gemini(
            model="gemini-3.1-flash-lite",
            retry_options=types.HttpRetryOptions(attempts=6),
        ),
        instruction=(Path(__file__).parent / "instruction.md").read_text(),
        tools=[get_weather],
        output_key="weather_signal"
    )
