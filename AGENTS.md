# AGENTS.md — guidance for AI coding agents

This repo is the **Flight Disruption Concierge** capstone (see **[docs/DESIGN.md](docs/DESIGN.md)**
for the full design — read it before writing code).

## Current task
Build **MVP-1** exactly as specified in **[docs/MVP1_BUILD.md](docs/MVP1_BUILD.md)**.
That file is the source of truth for scope, agents, contracts, and definition of done.
Do not build anything outside MVP-1 scope.

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

## Definition of done for MVP-1
1. `app/cli.py "<flight query>"` runs the full Concierge → Prediction → Prior A2A chain and prints a `RiskAssessment`.
2. `eval/backtest.py` reports AUC + calibration on the Jan-2020 holdout.

See docs/MVP1_BUILD.md for the step-by-step build order.
