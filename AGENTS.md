# AGENTS.md — guidance for AI coding agents

This repo is the **Flight Disruption Concierge** capstone (see **[docs/DESIGN.md](docs/DESIGN.md)**
for the full design — read it before writing code).

## Current task
Build **MVP-1a** exactly as specified in **[docs/MVP1_BUILD.md](docs/MVP1_BUILD.md)**.
That file is the source of truth for scope, agents, contracts, and definition of done.

**MVP-1a = the A2A flow only, with Prior returning a STUB risk number.**
No data, no SQLite, no model, no training, no backtest — those are MVP-1b.
Do NOT generate synthetic data. Do not build anything outside MVP-1a scope.

## Tech & conventions
- **Language:** Python 3.11+.
- **Framework:** Google **ADK** (`pip install "google-adk[a2a]"`). Scaffold with `agents-cli` —
  do not hand-roll project structure if a scaffold template fits.
- **Inter-agent:** real **A2A** — expose with `to_a2a(...)`, consume with `RemoteA2aAgent(...)`.
- **Models:** default to `gemini-flash-latest` unless told otherwise.
- **Contracts:** Pydantic models in `common/contracts.py`; agents exchange these, not loose dicts.
- Keep each agent thin and single-purpose. Match the existing repo style.

## Hard constraints (do not violate)
- **No real money, no real ticketing.** (Not in MVP-1 at all; later phases use sandbox only.)
- Keep large data files out of git — download into `data/` (gitignored).
- Every step must be runnable/verifiable locally before moving on.

## Definition of done for MVP-1a
`app/cli.py "<flight query>"` runs the full Concierge → Prediction → Prior A2A chain and prints a
`RiskAssessment` (Prior is a stub, so `dominant_cause: historical(STUB)`).

(MVP-1b adds the real model + DB and the `eval/backtest.py` AUC — separate milestone.)

See docs/MVP1_BUILD.md for the step-by-step build order.
