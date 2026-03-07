# Recruitment Assistant AI

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CrewAI](https://img.shields.io/badge/Stack-CrewAI-purple.svg)](https://www.crewai.com/)
[![FastAPI](https://img.shields.io/badge/Stack-FastAPI-0995ec.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Stack-Streamlit-orange.svg)](https://streamlit.io/)
[![Testing](https://img.shields.io/badge/Tests-pytest-green.svg)](https://pytest.org/)

An HR‑focused multi‑agent platform that accelerates sourcing, vetting, and outreach for technical roles. Built for talent teams, agency recruiters, and hiring managers who need to surface deeply qualified leaders faster, while remaining compliant and auditable.

---
## Table of Contents
- [What It Does](#what-it-does)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Governance](#governance)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## What It Does
Recruitment Assistant AI is a multi‑agent recruitment platform that:

- **Automates research and shortlisting** of candidates from job descriptions.
- **Scores candidates against structured rubrics** based on the JD.
- **Generates personalized outreach drafts** for each candidate.
- **Surfaces transparent rationale** and bias flags for audit‑ready decision‑making.
- **Keeps humans in the loop** for governance, final approval, and compliance.

The core value proposition is delivering **curated “Top 3” shortlists**, **reasoned candidate rationales**, and **personalized outreach drafts** without drowning in spreadsheets or manual sourcing, so recruiters not losing time on repetitive tasks or failing to differentiate the employer brand.

---

## Key Features
- **Job‑description–driven pipeline**  
  Paste or upload a job description to start a campaign.

- **Sequential multi‑agent workflow**  
  A CrewAI pipeline (`researcher → evaluator → recommender → writer`) handles:
  - Researching candidates.
  - Evaluating against the JD.
  - Recommending shortlists.
  - Drafting personalized outreach.

- **Campaign‑centric storage**  
  All campaigns, candidates, metrics, and audit logs are stored in `CampaignStore` (in‑memory MVP).

- **Human‑in‑the‑loop review**  
  - UI shows scorecards, rationale, and bias flags.
  - Outbound outreach is gated behind explicit approval.

- **Audit & purge**  
  Every status change, ranking, and outreach action is logged; a purge endpoint supports GDPR‑style right‑to‑erasure.

- **Exportable reports**  
  Download PDF reports with audit‑friendly rationales and decision paths.

- **FastAPI API**
REST endpoints for:
  - Campaigns, rankings, and outreach
  - Reports and audit logs
  - Purge operations

---

## Tech Stack
- **Python 3.10+** managed via `uv`.
- **CrewAI** agents implemented in `recruitment_assistant/agents/crew.py`.
- **FastAPI** backend in `recruitment_assistant/api/main.py`, serving the `CampaignStore` (in‑memory).
- **Streamlit UI** under `recruitment_assistant/ui/` (components, API client, report utilities).
- **FPDF2** for PDF export.
- **structlog** and **Loguru** for structured logging.
- **pytest** for testing agents, API routes, and helpers.

---

## Prerequisites
- **Python 3.10+** (the `uv` tool will provision the correct interpreter).
- **Optional**: Docker (not required for MVP but can be used later for deployment).
- **Configuration**: For requested env keys have a look to **.env.example**; optional API keys are e.g. `SENDGRID_API_KEY` (for simulating outbound email). Set your **.env** file accordingly. Load the .env file with dotenv.load_dotenv() before FastAPI starts. The /health endpoint exposes APP_ENV, OPENAI_MODEL, and APP_NAME so the UI can warn when running in staging or production.
- **CrewAI tracing** requires `CREWAI_AOP_ACCOUNT` and `CREWAI_AOP_API_KEY` (plus optional `CREWAI_AOP_PROJECT`) to be configured; once provided, `logging_config.enable_crewai_tracing()` marks `CREWAI_TRACING_ENABLED` and logs `crewai_tracing_enabled` with the dashboard URL, proving the account is authenticated and linking you directly to the trace viewer.

---

## Governance
### Data & Integrations
- **Local store:** `CampaignStore` holds campaigns, candidate records, outreach drafts, metrics, and audit logs.
- **CrewAI tools:** Serper.dev (search), Browserless.io (scraping), and OpenAI/Claude LLMs via environment-configured keys.
- **Report export:** Streamlit assembles data into PDF downloads using `ui/report_utils.py`.

### Privacy, Security, & Compliance
- Data remains in-memory for the MVP, with placeholders for encryption-at-rest when a database is introduced.
- Secrets (LLM keys, feature flags) are stored via `.env` and loaded with `python-dotenv`.
- `/health` exposes runtime metadata (`APP_ENV`, `OPENAI_MODEL`) for auditor visibility.
- Audit logs, bias flags, and the right-to-erasure purge endpoint keep the project aligned with GDPR/AI Act expectations.

### Fairness & Bias Mitigation
- Structured rubrics in the evaluator agent ensure each candidate is scored against the JD, reducing ad-hoc comparisons.
- Bias flags and "Data Deficient" markers surface risky content; the UI highlights them before ranking/outreach.
- Redaction logic in outreach drafts removes detected PII and sensitive keywords before presenting drafts.
- Human-in-the-loop approvals gate any outreach send; UI warnings remind reviewers to inspect rationale and bias indicators.
- Calibration occurs via `CampaignStore` metrics (bias checks, selection rationale, audit timestamps) and report downloads that document decision paths.
- Each candidate ranking includes explicit explanations. PDF exports and audit logs help document why a candidate was advanced or filtered,  encouraging manual recalibration when unstable.

---

## Installation
1. Create a virtual environment from repository root:
   ```bash
   uv venv
2. Install dependencies
   ```bash
   uv run pip install -r recruitment_assistant/requirements.txt

---

## Running the Project
1. Start the FastAPI backend:
   ```bash
   uv run uvicorn recruitment_assistant.api.main:app --host 0.0.0.0 --port 8000 --reload

2. In a separate terminal, start the Streamlit UI:
   ```bash
   uv run python -m streamlit run recruitment_assistant/ui/app.py

3. Open the UI in your browser:
   ```bash
   http://localhost:8501

---

## Usage
1. Create a campaign
   - Paste a job description or upload a file.
   - Click “Start Campaign” and monitor the status tiles for each agent stage.
2. Review candidate shortlists
   - View scorecards, rationale, and bias flags.
   - Inspect “Data Deficient” markers and any redacted PII.
3. Edit and approve outreach
   - Three personalized drafts are generated per candidate.
   - Edit drafts in the UI and approve outreach before sending.
4. Download reports
   - Use the “Export” section to download PDF reports with audit‑friendly rationales.
5. Use the API directly
   Relevant endpoints:
   - /health – runtime metadata (APP_ENV, OPENAI_MODEL)
   - /campaigns – list and create campaigns
   - /campaigns/{id}/report – download campaign reports
   - /audit-logs – retrieve audit entries
   - DELETE /campaigns/{id} – purge a campaign for compliance
6. Local CLI
   Run tools from scripts/cli.py:
   ```bash
   python scripts/cli.py api --reload
   python scripts/cli.py ui
   python scripts/cli.py test
7. The Streamlit sidebar now exposes an `Exit App` button that halts rendering, displays a reminder to stop Streamlit/uvicorn with `Ctrl+C`, and lets you restart the UI by refreshing the page after closing the tab.

---

## Project Structure
1. `recruitment_assistant/`: 
   - Python application root
   - Contains `pyproject.toml`, FastAPI API, CrewAI agents, Streamlit UI,   and shared logging/config helpers
2. `scripts/`: 
   - CLI helpers (`scripts/cli.py`) and start scripts for API, UI and tests
3. `tests/`: 
   - Pytest suites covering agents, API routes, systems and UI components.
4. Root docs like `Dockerfile`, `docker-compose.yml` etc. provide the narrative and operational context for the repo.

---

## Testing
1. Run the test suite:
   ```bash
   uv run pytest

This covers:
- Crew agents.
- CampaignStore and core logic.
- FastAPI routes and helpers.

2. UI‑level tests are currently manual; follow the QA plan for workflow validation and report‑export checks. The full suite should pass before any release.

---

## Limitations
1. The store is in-memory, so a restart loses campaigns/audit logs; migrating to a database is planned.
2. LLM responses can still hallucinate; the UI relies on human review of rationales and bias flags before outreach.
3. PDF exports assume the API returns metrics/rationale; any schema drift requires updating `ui/report_utils.py`.
4. Non-English languages are not fully supported yet.

---

## Roadmap
1. Persist campaigns in PostgreSQL or SQLite with migrations, adding audited storage tables, indexes, and retention policies for candidate metadata and audit trails.
2. Introduce a keyed content retrieval layer (vector search + normalized candidate cache) so downstream reports and PDFs can query rationale/history without replaying CrewAI prompts.
3. Add real integrations for Serper, Browserless, and SendGrid with authenticated credentials.
4. Harden JWT-based auth for the API + rate limiting.
5. Expand automated UI tests (e.g., Playwright) for Streamlit flows.
6. Introduce real-time WebSocket status streaming and CrewAI metric dashboards.

---

## License
Apache License 2.0. See [LICENSE](https://www.apache.org/licenses/LICENSE-2.0) for full terms.

---

## Acknowledgements
Thanks to open-source community for patterns that shaped the fair, auditable workflows in this repository.

Special thanks to <i>Carmelo Iaria</i> offering his [AAMAD](https://github.com/synaptic-ai-consulting/AAMAD/tree/main) framework to implement multi-agent systems.
