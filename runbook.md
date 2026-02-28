# Recruitment Assistant Operational Runbook

## Purpose
- Support DevOps, SRE, and on-call engineers with everything needed to bring the Recruitment Assistant stack online, observe it, and recover it when issues emerge.
- Provide a concise, actionable summary that complements the longer-form PRD/SAD/deployment documentation located under `project-context/`.

## Overview
- Recruitment Assistant AI combines a FastAPI backend, an in-memory `CampaignStore`, and a Streamlit UI to orchestrate CrewAI agents (researcher → evaluator → recommender → writer) for sourcing, ranking, and outreach workflows.
- Observability relies on a shared `loguru`/`structlog` stack (see `recruitment_assistant/logging_config.py`) that redirects stdout/stderr into JSON logs with rotation, redacts secrets, and optionally enables CrewAI tracing when `CREWAI_AOP_*` credentials are set.

## Prerequisites & Dependencies
- Python 3.12.5+ managed by `uv` (project-local `.venv/` inside project root `recruitment_assistant/`).
- Dependencies defined in `pyproject.toml` and `requirements.txt`, including `CrewAI`, `Loguru`, `Structlog`, `FastAPI`, `Streamlit`, `Pydantic`, `Plotly`, and `Server-side FPDF2`.
- Optional external services: OpenAI/Claude API (LLM), Serper.dev search, Browserless scraping, SendGrid/SMTP, and CrewAI AOP account for tracing (set `CREWAI_AOP_ACCOUNT`/`CREWAI_AOP_API_KEY`).
- uv CLI for environment management: `uv venv`, `uv run ...`, `uv pip install ...`.

## Installation
1. From repo root (`C:\Program Files\myRepos\recruitment-assistant\recruitment_assistant`), create the project environment: `uv venv`.
2. Install dependencies: `uv run pip install -e .` (editable) or `uv run pip install -r ./requirements.txt` for locked installs.
3. Confirm logging dependencies exist: `uv run python -c "import loguru; print(loguru.__version__)"` should print `0.7.x`.
4. Copy `.env.example` to `.env` and populate required keys (`OPENAI_API_KEY`, `SERPER_API_KEY`, logging/tracing toggles, etc.). See README and deployment plan for full variable list.

## Configuration
- `.env` entries include:
  - **LLM & tools**: `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4o`, `SERPER_API_KEY`, `BROWSERLESS_API_KEY`, `SENDGRID_API_KEY`.
  - **Environment tags**: `APP_ENV` (`development`/`staging`/`production`), `APP_NAME`, `FEATURE_FLAG_BIAS_ALERTS`, `API_BASE_URL`.
  - **Persistence**: `DATABASE_URL` (defaults to `sqlite:///./data/dev.db`).
  - **Logging**: `DEV_LOG_LEVEL`, `DEV_FILE_LOG_LEVEL`, `DEV_ERROR_LOG_LEVEL` (DEBUG/DEBUG/ERROR for dev) and `PROD_LOG_LEVEL`, `PROD_FILE_LOG_LEVEL`, `PROD_ERROR_LOG_LEVEL` (INFO/INFO/ERROR for prod). The runtime chooses the appropriate trio based on `APP_ENV`.
  - **CrewAI tracing**: `CREWAI_AOP_ACCOUNT`, `CREWAI_AOP_API_KEY`, `CREWAI_AOP_PROJECT`, `CREWAI_DASHBOARD_URL` (default `https://app.crewai.ai/aop`). Logs emit `crewai_tracing_enabled` to confirm authentication.
  - Documented in README Observability section and monitoring plan; QA plan ensures fields remain tested.

## Running the Application
- **API**: `uv run uvicorn recruitment_assistant.api.main:app --host 0.0.0.0 --port 8000 --reload` (or use `scripts/start-local-api.ps1`). REST endpoints include `/campaigns`, `/rank`, `/outreach`, `/audit-logs`, `/health`.
- **UI**: `uv run python -m streamlit run recruitment_assistant/ui/app.py` (or `scripts/start-local-ui.ps1`) to host the dashboard at `http://localhost:8501`. Set `API_BASE_URL` if backend lives elsewhere.
- **CLI helpers**: `python scripts/cli.py api` / `python scripts/cli.py ui` invoke the above commands via `uv` with repo-root detection.
- **Tests**: `uv run pytest` validates CrewAI agents, CampaignStore, API, and UI components. Run before deployments.

## Monitoring & Logs
- Logs written to `recruitment_assistant/logs/recruitment_assistant.log` (JSON) and `recruitment_assistant/error.log`. Rotation: 10 MB/14 days for main log, 5 MB/30 days for errors (compressed as ZIP).
- Console output is colorized for devs; `LOG_LEVEL` switching controls verbosity (DEBUG for dev, INFO for prod).
- Tail logs: `uv run tail -f recruitment_assistant/logs/recruitment_assistant.log` (or `docker-compose exec api tail -f /app/logs/...`).
- Monitoring plan mandates verifying `logging_initialized`, `http_request_start/complete/error`, `crew_campaign_*` events, and `crewai_tracing_enabled` when tracing enabled.
- CrewAI traces: Look for `crewai_tracing_enabled` log which includes `CREWAI_DASHBOARD_URL`; use that dashboard to review traces of agent operations and correlate with request IDs.

## Troubleshooting & Common Issues
1. `ModuleNotFoundError: loguru` — run via `uv` or reinstall `loguru` inside `.venv` (`uv run pip install loguru`).
2. Missing CrewAI tracing logs — ensure `CREWAI_AOP_ACCOUNT`/`CREWAI_AOP_API_KEY` are set; the log entry `crewai_tracing_enabled` confirms the account is authenticated.
3. FastAPI errors (term/timeouts) — look for `http_request_failed` or `crew_campaign_error` lines in logs; `response.headers[x-request-id]` correlates requests across logs.
4. Streamlit can't reach backend — confirm `API_BASE_URL` matches backend host, check CORS and run backend first.
5. CampaignStore issues — inspect JSON logs for `record_audit` entries and run `/campaigns/{id}/status` to ensure candidates/metrics exist.

## Stop/Restart Procedures
- Stop each service with `Ctrl+C`; uvicorn/Streamlit handle signals gracefully.
- To restart after config updates, stop services, adjust `.env`, then rerun the start commands above.
- Containers: `docker-compose down && docker-compose up` (see deployment plan for Compose details).
- Supervisor-managed setups should restart the `uv` commands on failure; ensure environment variables passed to the service (especially logging/tracing) are updated before restart.

## Health Checks & Diagnostics
- `/health` returns `status=healthy`, `version`, `app_env`, and `openai_model`. Hit it manually or via automation to confirm the backend is healthy.
- `/campaigns/{id}/status` shows campaign metrics/bias flags; verifying this ensures the CrewAI pipeline completed successfully.
- Logs include `logging_initialized` and `CrewAI` trace entries—if those disappear, the process failed during startup.
- Use `uv run pytest` after configuration changes to validate the full stack.

## Contacts & Escalation
- Refer to the AAMAD agent roles (PRD Section 2) for owners: @product-mgr, @system.arch, @backend.eng, @frontend.eng, @integration.eng, @qa.eng.
- For urgent issues, notify the `#recruitment-assistant` channel and reference `project-context/3.deliver/runbook.md` for incident context.
- Document any updates to this runbook or incident postmortems in `project-context/3.deliver/runbook.md` and mention them in QA summaries.
