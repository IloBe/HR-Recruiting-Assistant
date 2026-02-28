# Recruitment Assistant AI

## Table of Contents
- [What Is It For](#what-is-it-for)
- [Motivation](#motivation)
- [Project Status](#project-status)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Core Workflows](#core-workflows)
- [Data & Integrations](#data--integrations)
- [Privacy, Security, & Compliance](#privacy-security--compliance)
- [Fairness & Bias Mitigation](#fairness--bias-mitigation)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Installation & Running Locally](#installation--running-locally)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Key Artifacts](#key-artifacts)
- [Testing](#testing)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [DevOps & Deployment](#devops--deployment)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## What Is It For
Recruitment Assistant AI is an HR-focused multi-agent platform that accelerates sourcing, vetting, and outreach for technical roles. It is built for talent teams, agency recruiters, or hiring managers who need to find deeply qualified leaders faster without drowning in spreadsheets or manual sourcing. The core value proposition is delivering curated "Top 3" shortlists, reasoned candidate rationales, and personalized outreach drafts while keeping humans in the loop for governance and compliance.

## Motivation
Recruiters lose time on repetitive searches, suffer from unclear candidate signals, and risk sending out templated messaging that fails to differentiate the employer brand. This assistant solves those pain points by combining semantic search, evaluative reasoning, and outreach generation. It surfaces transparent rationale for ranking decisions, flags ambiguous or biased content, and lets humans steer the workflow before any outreach is sent.

## Project Status
- Current phase: Deliver phase completed. The deployment and runbook artifacts under [project-context/3.deliver](project-context/3.deliver/deployment-plan.md) document the final rollout, rollback, and handoff steps, so the repository is ready for operations and audits.
- Maintenance: updates to `.github/` instructions/prompts keep the automated agents aligned with the completed deliver scope, and the runbook under `recruitment_assistant/runbook.md` (root path `C:/Program Files/myRepos/recruitment-assistant/recruitment_assistant/runbook.md`) captures the remaining run/verify checklists.
- Next steps: continue keeping the deliverables (Doc and runbook) in sync with any CI/CD changes and share readiness notes with the QA/DevOps team.

## How It Works
At a high level: (1) a recruiter uploads a Job Description or pastes it into the UI; (2) a sequential CrewAI pipeline (researcher → evaluator → recommender → writer) executes asynchronous tasks, stores candidates, metrics, and audits in the `CampaignStore`, and persists ranked outputs; (3) the Streamlit frontend pulls status/candidate data, displays rationale, allows edits, and lets the recruiter download reports or send drafts. FastAPI exposes REST endpoints for campaigns, rankings, outreach, reports, audits, and purge operations.

## Tech Stack
- **Python 3.10+** with `uv` for dependency management and CLI.
- **CrewAI** agents implemented in `recruitment_assistant/agents/crew.py`.
- **FastAPI** serving `recruitment_assistant/api/main.py`, backed by an in-memory `CampaignStore` for the MVP.
- **Streamlit UI** under `recruitment_assistant/ui/` (components, API client, report utilities).
- **FPDF2** for PDF export, `structlog` for structured logging, and `pytest`/`uv` for testing.

## Observability & Logging Guidance
- All runtime modules import the shared logger via `from loguru import logger as loguru_logger` so the configured sinks, rotation, and redaction filters from `recruitment_assistant/logging_config.py` are consistently applied.
- To keep type checkers happy, `Logger` is imported only inside `if TYPE_CHECKING`, while `configure_logging` and `get_app_logger` still use `Logger` annotations thanks to `from __future__ import annotations`—this avoids pulling in non-exported symbols during pytest/runtime runs.
- `_REDACT_FILTER: Callable[[Any], bool] = cast(...)` exists solely so Pylance recognizes the Loguru `filter` overloads without breaking runtime execution, and each `loguru_logger.add(...)` sink already uses `# type: ignore[call-overload]` to silence the remaining stub mismatch while keeping structured JSON output.
- CrewAI tracing requires `CREWAI_AOP_ACCOUNT` and `CREWAI_AOP_API_KEY` (plus optional `CREWAI_AOP_PROJECT`) to be configured; once provided, `logging_config.enable_crewai_tracing()` marks `CREWAI_TRACING_ENABLED` and logs `crewai_tracing_enabled` with the dashboard URL, proving the account is authenticated and linking you directly to the trace viewer.
- Documentation Alignment Checklist:
	1. README covers the runtime log import/typing strategy and structured sinks (this section).
	2. Monitoring plan reiterates the runtime import details, Pylance filters, and CrewAI tracing enablement/URL log for operations staff.
	3. QA plan adds verification steps for the logging/tracing codepaths, including CrewAI credentials and `crewai_tracing_enabled` logs, keeping all docs consistent.

## Core Workflows
1. **Campaign Creation:** JD intake, validation, and seeding of the crew pipeline.
2. **Candidate Ranking:** Evaluation outputs aggregated, bias/data-deficient flags computed, metrics stored, selection rationale surfaced.
3. **Outreach Drafting:** Three personalized drafts per candidate generated, editable within the UI, with send actions logged.
4. **Audit & Purge:** Every status change, ranking, and outreach action is audited and can be purged for compliance.

## Data & Integrations
- **Local store:** `CampaignStore` holds campaigns, candidate records, outreach drafts, metrics, and audit logs.
- **CrewAI tools:** Serper.dev (search), Browserless.io (scraping), and OpenAI/Claude LLMs via environment-configured keys.
- **Report export:** Streamlit assembles data into PDF downloads using `ui/report_utils.py`.

## Privacy, Security, & Compliance
- Data remains in-memory for the MVP, with placeholders for encryption-at-rest when a database is introduced.
- Secrets (LLM keys, feature flags) are stored via `.env` and loaded with `python-dotenv`.
- `/health` exposes runtime metadata (`APP_ENV`, `OPENAI_MODEL`) for auditor visibility.
- Audit logs, bias flags, and the right-to-erasure purge endpoint keep the project aligned with GDPR/AI Act expectations.

## Fairness & Bias Mitigation
- Structured rubrics in the evaluator agent ensure each candidate is scored against the JD.
- Bias flags and "Data Deficient" markers surface risky content; the UI highlights them before ranking/outreach.
- Redaction logic in outreach drafts removes detected PII and sensitive keywords before presenting drafts.
- Human-in-the-loop approvals gate any outreach send; UI warnings remind reviewers to inspect rationale and bias indicators.
- Calibration occurs via `CampaignStore` metrics (bias checks, selection rationale, audit timestamps) and report downloads that document decision paths.
- Explanations accompany every candidate ranking to help explain why a candidate was advanced, encouraging manual recalibration when unstable.

## Getting Started
### Prerequisites
- Python 3.10+ (the `uv` tool will provision the correct interpreter via `uv venv`).
- Optional API keys: `OPENAI_API_KEY` (or Claude), `SERPER_API_KEY`, `SENDGRID_API_KEY` (if outgoing email simulated).
- Docker is not required for the MVP but can be introduced later for deployment.

The compact [operational runbook](recruitment_assistant/runbook.md) at the project root (C:/Program Files/myRepos/recruitment-assistant/recruitment_assistant/runbook.md) captures the detailed Quick Start, logging/tracing overrides, crew credentials, and follow-up checks—refer to it before you provision or run the stack.

### Quickstart Steps
1. `uv venv` from the repository root.
2. `uv run pip install -r recruitment_assistant/requirements.txt`.
3. `uv run uvicorn recruitment_assistant.api.main:app --host 0.0.0.0 --port 8000 --reload`.
4. `uv run python -m streamlit run recruitment_assistant/ui/app.py` and open `http://localhost:8501`.

## Configuration
Store runtime secrets and flags in a `.env` file at the project root:

```.env.example
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
SERPER_API_KEY=serper-...
APP_ENV=development
APP_NAME=recruitment-assistant
FEATURE_FLAG_BIAS_ALERTS=true
DATABASE_URL=sqlite:///./data/dev.db
```

Load with `dotenv.load_dotenv()` before the FastAPI app initializes. Expose `APP_ENV`, `OPENAI_MODEL`, and `APP_NAME` via `/health` so the UI can warn when deployed to staging/production.

## Installation & Running Locally
1. `uv venv && uv run pip install -r recruitment_assistant/requirements.txt`.
2. Optionally set up a database and run migrations when moving beyond the in-memory store (script placeholder).
3. Seed the store automatically via `CampaignStore._populate_seed_campaign` when the API launches.
4. `uv run uvicorn recruitment_assistant.api.main:app --host 0.0.0.0 --port 8000 --reload`.
5. In a second terminal, `uv run python -m streamlit run recruitment_assistant/ui/app.py`.
6. Run `uv run pytest` from `recruitment_assistant/` to validate agents, API routes, and helpers.

## Usage
- Use the Streamlit UI to paste a JD or upload a file, click "Start Campaign", and monitor status tiles for the crew stages.
- Once candidates appear, view scorecards, rationale, and bias tags. Edit and approve outreach drafts before clicking "Send".
- Download PDF reports from the "Export" section to capture audit-friendly rationales.
- Use `/health`, `/campaigns`, `/audit-logs`, `/campaigns/{id}/report`, and `/campaigns/{id}` DELETE endpoints via API client for automation.
- Manage the local stack through the argparse CLI: `python scripts/cli.py api --reload`, `python scripts/cli.py ui`, or `python scripts/cli.py test`. The CLI autodetects the repo root (via `.git`) so it works when invoked from the root or nested workspace directories.
- Stop uvicorn/Streamlit via `Ctrl+C` in the terminals or the stop scripts once you finish.
- The Streamlit sidebar now exposes an `Exit App` button that halts rendering, displays a reminder to stop Streamlit/uvicorn with `Ctrl+C`, and lets you restart the UI by refreshing the page after closing the tab.

## Project Structure
- `recruitment_assistant/`: Python application root with `pyproject.toml`, FastAPI API, CrewAI agents, Streamlit UI, and shared logging/config helpers.
- `.github/`: Hosts agent definitions, instructions, and prompts that drive the AAMAD multi-agent workflows plus any GitHub-native automation tied to the recruitment assistant deliveries.
- `project-context/`: AAMAD documentation (MRD/PRD in `1.define`, architecture/backend/frontend/integration/QA plans plus SAD in `2.build`, and deployment/operational plans in `3.deliver`).
- `scripts/`: CLI helpers (`scripts/cli.py`, start scripts) that launch the backend, UI, and tests inside the `uv`-managed virtual environment.
- `tests/`: Pytest suites covering agents, API routes, systems, and UI components.
- `.venv/`: Local Python environment provisioned by `uv venv` and kept out of source control.
- Root docs and helper configs (AGENTS.md, CHECKLIST.md, context-summary.md, runbook, Dockerfile, docker-compose.yml) provide the narrative and operational context for the repo.

## Key Artifacts
- [AGENTS.md](AGENTS.md): AAMAD agent catalog and persona definitions that orchestrate the recruitment assistant conversations.
- [CHECKLIST.md](CHECKLIST.md): Go/no-go checklist for deployments and key validation checkpoints.
- [context-summary.md](context-summary.md): Condensed history of the workspace decisions and progress markers.
- [project-context/1.define/mrd.md](project-context/1.define/mrd.md) and [project-context/1.define/prd.md](project-context/1.define/prd.md): Phase 1 research and requirements artifacts.
- [project-context/2.build/architecture-plan.md](project-context/2.build/architecture-plan.md), [project-context/2.build/backend-plan.md](project-context/2.build/backend-plan.md), [project-context/2.build/frontend-plan.md](project-context/2.build/frontend-plan.md), [project-context/2.build/integration-plan.md](project-context/2.build/integration-plan.md), [project-context/2.build/qa-plan.md](project-context/2.build/qa-plan.md), and [project-context/2.build/sad.md](project-context/2.build/sad.md): Phase 2 design and implementation plans.
- [project-context/3.deliver/deployment-plan.md](project-context/3.deliver/deployment-plan.md): Completed Phase 3 delivery plan, including runtime checks and rollout/rollback guidance.
- [recruitment_assistant/runbook.md](recruitment_assistant/runbook.md): Operational runbook for day-to-day commands, logging/tracing verification, and response actions.
- [handoff-checklist.md](handoff-checklist.md): Handoff-ready validation cues for releases transitioning to operations or QA.

## Testing
- `uv run pytest` runs unit and integration tests for crew agents, `CampaignStore`, and FastAPI routes.
- Streamlit UI tests are manual (follow QA plan to verify workflows and report exports).
- Evaluation tests are simulated via crew outputs and `CampaignStore` metrics; run the entire suite before releases.

## Limitations
- The store is in-memory, so a restart loses campaigns/audit logs; migrating to a database is planned.
- LLM responses can still hallucinate; the UI relies on human review of rationales and bias flags before outreach.
- PDF exports assume the API returns metrics/rationale; any schema drift requires updating `ui/report_utils.py`.
- Non-English languages are not fully supported yet.

## Roadmap
- Persist campaigns in PostgreSQL or SQLite with migrations, adding audited storage tables, indexes, and retention policies for candidate metadata and audit trails.
- Introduce a keyed content retrieval layer (vector search + normalized candidate cache) so downstream reports and PDFs can query rationale/history without replaying CrewAI prompts.
- Add real integrations for Serper, Browserless, and SendGrid with authenticated credentials.
- Harden JWT-based auth for the API + rate limiting.
- Expand automated UI tests (e.g., Playwright) for Streamlit flows.
- Introduce real-time WebSocket status streaming and CrewAI metric dashboards.

## DevOps & Deployment
- Deployment artifacts live under `project-context/3.deliver`. The [deployment plan](project-context/3.deliver/deployment-plan.md) captures local, Docker, and cloud options plus rollout/rollback procedures.
- Operational runbook: [recruitment_assistant/runbook.md](recruitment_assistant/runbook.md) provides day-to-day commands, logging/tracing checks, and troubleshooting steps.
- Local starts use `recruitment_assistant/scripts/start-local-api.ps1` and `recruitment_assistant/scripts/start-local-ui.ps1`; both call `uv venv` and `uv run` so the `recruitment_assistant/` `.venv` stays authoritative.
- Docker runs build the root image via `Dockerfile` and `docker-compose.yml`; adapt the Compose commands when promoting to AWS, Render, or Modal (each platform can override the service command and expose ports 8000/8501).
- Cloud deployments must inject secrets (OPENAI_API_KEY, SERPER_API_KEY, SENDGRID_API_KEY, FEATURE_FLAG_BIAS_ALERTS) through the provider’s secret manager and verify `/health` before traffic shifts.
- Automate `uv run pytest` + `/health` polling in every pipeline and rerun manual UI smoke tests when CrewAI prompts or env vars change.

Common Deployment Options for this Project:
1. Local Python Script (Simplest) 
Create a `main.py` entry point 
Add `requirements.txt` with all dependencies 
Document how to run: python main.py 
2. Docker Container
Create `Dockerfile` 
Create `docker-compose.yml` (if needed) 
Document: `docker build -t recruitment-assistant . && docker run recruitment-assistant`
3. CLI Entry Point (Good for testing) 
Create a command-line interface 
Use `click` or `argparse` for CLI

## License
Apache License 2.0. See [LICENSE](LICENSE) for full terms.

## Acknowledgements
Thanks to open-source community for patterns that shaped the fair, auditable workflows in this repository.

Special thanks to <i>Carmelo Iaria</i> offering his [AAMAD](https://github.com/synaptic-ai-consulting/AAMAD/tree/main) framework to implement multi-agent systems.
