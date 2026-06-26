# MVP-1 Build Spec

> Executable spec for an AI coding agent (e.g. Antigravity + Google ADK).
> Build **only** what is listed here. Read [DESIGN.md](DESIGN.md) first for context.

## Objective
A 3-agent vertical slice that proves the **A2A flow** and produces a **backtestable**
flight delay-risk prediction.

```
Concierge  ──A2A──►  Prediction  ──A2A──►  Historical/Prior  ──►  model + DB
```

- **Concierge** — parse the user's flight reference into `FlightContext`, call Prediction, format the answer.
- **Prediction** — take `FlightContext`, call its specialist(s), return `RiskAssessment`. In MVP-1 it has **one** specialist (Prior); the fan-out structure exists but isn't crowded.
- **Historical/Prior** — wrap the trained model + base-rate lookups; return prior risk.

In scope: 3 agents, one specialist, real A2A, trained model, backtest.
**Out of scope (later phases):** Weather/NAS agents, MCP, Rebooking Planner/Manager, HITL, live APIs, frontend.

## Data
- Dataset: Kaggle `divyansh22/flight-delay-prediction` — `Jan_2019_ontime.csv` (train), `Jan_2020_ontime.csv` (holdout). Download into `data/` (gitignored).
- Target: `ARR_DEL15` (arrival delayed ≥15 min). Also expose `CANCELLED`.
- Features for the model: `OP_UNIQUE_CARRIER`, `ORIGIN`, `DEST`, `DAY_OF_WEEK`, `DEP_TIME_BLK`, `DISTANCE`. (Drop the empty trailing `column21`.)

## Contracts (`common/contracts.py`, Pydantic)
```python
class FlightContext(BaseModel):
    carrier: str            # OP_UNIQUE_CARRIER, e.g. "DL"
    flight_no: str | None = None
    origin: str             # e.g. "ORD"
    dest: str               # e.g. "ATL"
    day_of_week: int        # 1=Mon … 7=Sun
    dep_time_blk: str       # e.g. "0700-0759"
    distance: float | None = None

class RiskAssessment(BaseModel):
    p_delay15: float        # 0..1
    p_cancel: float         # 0..1
    confidence: float       # 0..1
    dominant_cause: str = "historical"   # MVP-1: prior only
    explanation: str
```

## ADK / A2A specifics
Install: `pip install "google-adk[a2a]"`. Prefer `agents-cli scaffold create` for the project skeleton.

```python
# A leaf agent's tool (Prior) — a plain typed function is a FunctionTool
def predict_prior(carrier: str, origin: str, dest: str,
                  day_of_week: int, dep_time_blk: str) -> dict:
    """Return prior delay/cancel risk from the trained model + base rates."""
    ...

# Expose any agent as an A2A service
from google.adk.a2a.utils.agent_to_a2a import to_a2a
to_a2a(root_agent, port=8001)          # Prior on 8001, Prediction on 8002

# Consume a remote A2A agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
prior = RemoteA2aAgent(
    name="prior",
    description="Historical delay-risk prior",
    agent_card=f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}",
)
```

**Topology:** Prior served on `:8001`. Prediction served on `:8002`, holds a `RemoteA2aAgent`
pointing at Prior. Concierge holds a `RemoteA2aAgent` pointing at Prediction and is driven by `app/cli.py`.

## Build order (verify each step before the next)
1. **Data + model** (`data/load_data.py`, `data/train_model.py`) — load CSVs → SQLite (`data/flights.db`),
   train a simple classifier (logistic regression or gradient boosting) on Jan 2019, save `data/model.pkl`,
   build base-rate views (delay rate by carrier / route / time-block). *Verify with a standalone script — no agents yet.*
2. **Prior agent** (`agents/prior.py`) — `predict_prior` reads `model.pkl` + `flights.db`; serve via `to_a2a` on `:8001`.
3. **Prediction agent** (`agents/prediction.py`) — calls Prior over A2A, maps result → `RiskAssessment`; serve on `:8002`.
4. **Concierge** (`agents/concierge.py`) — NL flight ref → `FlightContext` → call Prediction → format answer.
5. **CLI + smoke test** (`app/cli.py`) — one command runs the whole chain end to end.
6. **Backtest** (`eval/backtest.py`) — score the Prior model over Jan 2020, report **AUC + calibration**.

## Definition of done
- **Flow test:** `python app/cli.py "DL ORD->ATL Monday 7am"` traverses Concierge → Prediction → Prior and prints a populated `RiskAssessment`.
- **Backtest:** `python eval/backtest.py` prints AUC (and a calibration summary) on the Jan-2020 holdout.
- A short `README` note in the project root explaining how to start the two A2A services and run the CLI.

## Target file layout
```
data/      load_data.py  train_model.py  (model.pkl, flights.db — gitignored)
agents/    prior.py  prediction.py  concierge.py
common/    contracts.py  config.py
eval/      backtest.py
app/       cli.py
```
