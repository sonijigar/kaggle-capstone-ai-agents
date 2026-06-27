from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.genai import types

_SKILL = load_skill_from_dir(Path(__file__).parent.parent / "skills" / "prior")

# Trained delay model (MVP-1b). Falls back to a rule-of-thumb if the artifact is missing.
import json
import joblib
import pandas as pd
_DATA = Path(__file__).parent.parent / "data"
try:
    _MODEL = joblib.load(_DATA / "model.pkl")
    _CANCEL = json.loads((_DATA / "cancel_rates.json").read_text())
except Exception:
    _MODEL, _CANCEL = None, {"by_carrier": {}, "global": 0.03}

async def predict_prior(carrier: str, origin: str, dest: str,
                  day_of_week: int, dep_time_blk: str) -> dict:
    """Delay/cancellation risk from the trained Jan-2019 model (rule-of-thumb fallback if model.pkl is missing).

    Args:
        carrier: OP_UNIQUE_CARRIER, e.g. "DL"
        origin: Origin airport, e.g. "ORD"
        dest: Destination airport, e.g. "ATL"
        day_of_week: Day of week (1=Monday ... 7=Sunday)
        dep_time_blk: Departure time block, e.g. "0700-0759"

    Returns:
        dict: A dictionary containing p_delay15, p_cancel, confidence, dominant_cause, and explanation.
    """
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
                author="prior",
                node_path=tool_node_path,
                actions=EventActions(),
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_function_call(
                        name="predict_prior",
                        args={"carrier": carrier, "origin": origin, "dest": dest, "day_of_week": day_of_week, "dep_time_blk": dep_time_blk}
                    )]
                )
            )
            import asyncio
            asyncio.create_task(ic._enqueue_event(tool_event))
    except Exception as e:
        print(f"Failed to inject tool event: {e}")

    if _MODEL is not None:
        X = pd.DataFrame([{
            "OP_UNIQUE_CARRIER": carrier, "ORIGIN": origin, "DEST": dest,
            "DAY_OF_WEEK": str(day_of_week), "DEP_TIME_BLK": dep_time_blk,
        }])
        p_delay = round(float(_MODEL.predict_proba(X)[0, 1]), 3)
        p_cancel = round(float(_CANCEL["by_carrier"].get(carrier, _CANCEL["global"])), 3)
        return {
            "p_delay15": p_delay,
            "p_cancel": p_cancel,
            "confidence": 0.6,
            "dominant_cause": "historical",
            "explanation": (
                f"Logistic-regression model trained on Jan-2019 BTS data: "
                f"{carrier} {origin}->{dest}, {dep_time_blk} block ~ "
                f"{p_delay:.0%} chance of a 15+ min arrival delay."
            ),
        }

    # Fallback rule-of-thumb if data/model.pkl is not present
    try:
        hour = int(dep_time_blk[:2])
    except (ValueError, TypeError, IndexError):
        hour = 12
    p = 0.18 + (0.10 if hour >= 17 else 0.05 if hour >= 12 else 0.0)
    return {
        "p_delay15": round(p, 2),
        "p_cancel": 0.03,
        "confidence": 0.5,
        "dominant_cause": "historical(STUB)",
        "explanation": f"stub risk for {dep_time_blk} (model.pkl not found)"
    }

from google.adk.agents.callback_context import CallbackContext

async def before_prior(callback_context: CallbackContext) -> None:
    callback_context.state["active_agent"] = "prior"
    callback_context.state["prior_status"] = "running"

async def after_prior(callback_context: CallbackContext):
    callback_context.state["prior_status"] = "completed"
    callback_context.state["active_agent"] = "prediction"
    return None

def build_prior_agent() -> Agent:
    return Agent(
        name=_SKILL.frontmatter.name,
        description=_SKILL.frontmatter.description,
        model=Gemini(
            model="gemini-3.1-flash-lite",
            retry_options=types.HttpRetryOptions(attempts=6),
        ),
        instruction=_SKILL.instructions,
        tools=[predict_prior],
        before_agent_callback=before_prior,
        after_agent_callback=after_prior,
        output_key="prior_result"
    )

prior_agent = build_prior_agent()
app = to_a2a(prior_agent, port=8001)
