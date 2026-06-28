import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.apps import App, ResumabilityConfig
from agents.prior import build_prior_agent
from agents.weather import build_weather_agent
from agents.planner import build_planner_agent
from agents.prediction import build_prediction_agent
from agents.concierge import build_concierge_agent

# Build in-process agents and wire them hierarchically using native AgentTool
prior = build_prior_agent()
weather = build_weather_agent()
planner = build_planner_agent()
prediction = build_prediction_agent(prior, weather)
concierge = build_concierge_agent(prediction, planner)

# Resumable sessions are required for the human-in-the-loop booking confirmation
# (FunctionTool(book_flight, require_confirmation=True) pauses the run until approval).
app = App(
    root_agent=concierge,
    name="playground",
    resumability_config=ResumabilityConfig(is_resumable=True),
)
