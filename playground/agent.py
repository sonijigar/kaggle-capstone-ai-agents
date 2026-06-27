import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from google.adk.apps import App
from agents.prior.agent import build_prior_agent
from agents.weather.agent import build_weather_agent
from agents.prediction.agent import build_prediction_agent
from agents.concierge.agent import build_concierge_agent

# Build in-process agents and wire them hierarchically using native AgentTool
prior = build_prior_agent()
weather = build_weather_agent()
prediction = build_prediction_agent(prior, weather)
concierge = build_concierge_agent(prediction)

# Define the ADK application with the in-process root concierge agent
app = App(
    root_agent=concierge,
    name="playground"
)
