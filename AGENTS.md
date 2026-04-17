# AGENTS.md

## Workflows

### Local development
- Install dependencies: `uv sync` and `cd frontend && npm install`
- Bootstrap Codex environment: `./codex_setup.sh`
- Bootstrap Jules environment: `./jules_setup.sh`
- Run both services: `./start.sh`
- Run backend only: `uv run python -m backend.main`
- Run frontend only: `cd frontend && npm run dev`

### Validation
- Run backend tests: `uv run pytest`
- Lint frontend: `cd frontend && npm run lint`
- Build frontend: `cd frontend && npm run build`
- Preview production frontend build: `cd frontend && npm run preview`

### Utility scripts
- Export benchmark script: `python scripts/benchmark_export.py`
- Retrieval benchmark script: `python scripts/measure_retrieval.py`
- Add DB index migration: `uv run python scripts/add_index.py`
- Scout assigned GitHub issues into `.agent/passports`: `gh auth login && ./scripts/scout_agent.py`

### Agentic workflow bootstrap
- Create a new feature passport: `cp .agent/templates/feature_passport.md .agent/passports/my_feature.md`

### Container workflow
- Build and run with Docker Compose: `docker compose up --build`

## TODO
- Confirm whether utility scripts should be run via `uv run python ...` for environment consistency.
