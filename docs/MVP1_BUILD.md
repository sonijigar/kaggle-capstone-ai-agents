# MVP-1 Build Spec

> Executable spec for an AI coding agent (e.g. Antigravity + Google ADK).
> Build **only** what is listed here. Read [DESIGN.md](DESIGN.md) first for context.

## Objective
A 3-agent vertical slice that proves the **A2A flow**. Split into two milestones —
**build 1a first, get it green, then do 1b.**

```
Concierge  ──A2A──►  Prediction  ──A2A──►  Historical/Prior
```

- **MVP-1a (do this now):** the full A2A chain working, with **Prior returning a STUB** risk
  number. **No data, no SQLite, no model, no training, no backtest.** Goal: prove the agents talk.
- **MVP-1b (next):** swap the stub's *internals* for a real trained model + DB, then add the
  backtest. **Nothing else changes** — Prediction, Concierge, contracts, and A2A stay untouched.

- **Concierge** — parse the user's flight reference into `FlightContext`, call Prediction, format the answer.
- **Prediction** — take `FlightContext`, call its specialist(s), return `RiskAssessment`. One specialist (Prior) for now; the fan-out structure exists but isn't crowded.
- **Historical/Prior** — returns prior risk. STUB in 1a; real model + base-rate lookups in 1b.

**Out of scope (later phases):** Weather/NAS agents, MCP, Rebooking Planner/Manager, HITL, live APIs, frontend.

## Contracts (`common/contracts.py`, Pydantic) — used in both 1a and 1b
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
    dominant_cause: str = "historical"
    explanation: str
```

## ADK / A2A specifics
Install: `pip install "google-adk[a2a]"`. Prefer `agents-cli scaffold create` for the project skeleton.

```python
# Prior's tool — MVP-1a STUB (rule-of-thumb; no data). Clearly marked as a stub.
def predict_prior(carrier: str, origin: str, dest: str,
                  day_of_week: int, dep_time_blk: str) -> dict:
    """STUB risk until the real model lands (MVP-1b). Evenings ~ riskier."""
    hour = int(dep_time_blk[:2])
    p = 0.18 + (0.10 if hour >= 17 else 0.05 if hour >= 12 else 0.0)
    return {"p_delay15": round(p, 2), "p_cancel": 0.03, "confidence": 0.5,
            "dominant_cause": "historical(STUB)", "explanation": f"stub risk for {dep_time_blk}"}

# Expose any agent as an A2A service
from google.adk.a2a.utils.agent_to_a2a import to_a2a
app = to_a2a(root_agent, port=8001)    # Prior :8001, Prediction :8002 — port here MUST match uvicorn --port

# Consume a remote A2A agent — use the constant, do NOT hardcode the well-known path
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
prior = RemoteA2aAgent(
    name="prior",
    description="Historical delay-risk prior",
    agent_card=f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}",   # not "/.well-known/agent.json"
)
```

> **Correctness:** the A2A well-known card path is `agent-card.json` in current ADK, exposed as
> `AGENT_CARD_WELL_KNOWN_PATH`. Hardcoding `/.well-known/agent.json` will 404. Always use the constant,
> and confirm the served URL before wiring the consumer.

**Topology:** Prior served on `:8001`. Prediction served on `:8002`, holds a `RemoteA2aAgent`
pointing at Prior. Concierge holds a `RemoteA2aAgent` pointing at Prediction and is driven by `app/cli.py`.

## MVP-1a build order (do now — no data)
1. **Contracts** (`common/contracts.py`) — the two Pydantic models above.
2. **Prior agent** (`agents/prior.py`) — the STUB `predict_prior`; serve via `to_a2a` on `:8001`.
3. **Prediction agent** (`agents/prediction.py`) — call Prior over A2A, map result → `RiskAssessment`; serve on `:8002`.
4. **Concierge** (`agents/concierge.py`) — NL flight ref → `FlightContext` → call Prediction → format answer.
5. **CLI smoke test** (`app/cli.py`) — one command runs the whole chain end to end.

**MVP-1a definition of done:** `python app/cli.py "DL ORD->ATL Monday 7am"` traverses
Concierge → Prediction → Prior and prints a populated `RiskAssessment` (with `dominant_cause: historical(STUB)`).
Plus a short root README on how to start the two A2A services and run the CLI.

## MVP-1b build order (next — make the prediction real)
Real data is available locally — both CSVs (`Jan_2019_ontime.csv`, `Jan_2020_ontime.csv`) will be
placed in `data/` (gitignored). Do **not** generate synthetic data; the backtest is only meaningful on real labels.

- Target `ARR_DEL15`; features `OP_UNIQUE_CARRIER, ORIGIN, DEST, DAY_OF_WEEK, DEP_TIME_BLK, DISTANCE` (drop empty `column21`).
6. **Data + model** (`data/load_data.py`, `data/train_model.py`) — CSVs → SQLite (`data/flights.db`); train a simple classifier (logistic regression) on Jan 2019; save `data/model.pkl`; build base-rate views (carrier / route / time-block).
7. **Swap Prior internals** — replace the stub body of `predict_prior` with model + DB lookups. Signature and return shape unchanged.
8. **Backtest** (`eval/backtest.py`) — score over Jan 2020; report **AUC + Brier/calibration**.

**MVP-1b definition of done:** `python eval/backtest.py` prints AUC + calibration on the real Jan-2020 holdout.

## Target file layout
```
common/    contracts.py  config.py          # 1a
agents/    prior.py  prediction.py  concierge.py   # 1a
app/       cli.py                            # 1a
data/      load_data.py  train_model.py      # 1b  (model.pkl, flights.db, *.csv — gitignored)
eval/      backtest.py                       # 1b
```
