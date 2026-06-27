.PHONY: install setup prewarm playground train backtest test

PORT ?= 8080

# Install Python deps.
install:
	uv sync

# One-time setup: deps + pre-warm/verify the MCP servers (first run downloads them).
setup: install prewarm
	@echo ""
	@echo "Setup complete. Next: 'make train' (optional, needs CSVs in data/) then 'make playground'."

# Download + verify the package-runner MCP servers (weather=npx, flights=uvx).
prewarm:
	@command -v uv  >/dev/null || { echo "ERROR: 'uv' not found  -> curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	@command -v npx >/dev/null || { echo "ERROR: 'npx'/Node not found -> https://nodejs.org"; exit 1; }
	uv run python scripts/prewarm.py

# Launch the ADK dev UI. In the browser, select the 'playground' app.
playground:
	@echo "Open http://127.0.0.1:$(PORT)  and select the 'playground' app in the dropdown."
	uv run adk web . --host 127.0.0.1 --port $(PORT) --allow_origins '*' --reload_agents

# Train the delay model on Jan-2019 BTS (needs data/Jan_2019_ontime.csv).
train:
	uv run python data/train_model.py

# Backtest on the Jan-2020 holdout (needs data/model.pkl + data/Jan_2020_ontime.csv).
backtest:
	uv run python eval/backtest.py

test:
	uv run pytest tests/unit -q
