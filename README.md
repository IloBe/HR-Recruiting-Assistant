# Recruitment Assistant AI

A production-ready Multi-Agent Recruitment System powered by the **CrewAI** framework. This assistant automates the end-to-end recruitment funnel: from parsing job descriptions to sourcing, screening, ranking, and drafting personalized outreach for top-tier talent.

> [!CAUTION]
> **Educational & Prototyping Use Only**: This project is not intended for commercial or business products. Automated searching and scraping of platforms like LinkedIn may violate their Terms of Service and API user agreements. Users are responsible for ensuring compliance with all platform policies and local regulations.

## 🚀 Project Overview
The Recruitment Assistant AI is designed to augment human recruiters by handling the high-volume, repetitive tasks of the early-stage hiring process. By leveraging specialized AI agents with distinct roles and backstories, the system provides nuanced candidate evaluation that goes beyond simple keyword matching.

## ⚖️ Problem Statement & Value Proposition
**The Problem**: Recruiters spend nearly 60% of their time on manual sourcing and screening, leading to burnout and missed talent in fast-moving markets. Traditional ATS systems are reactive and often filter out qualified candidates who don't match exact keywords.

**The Value**:
- **80% Time Savings**: Automating the manual toil of sourcing and initial screening.
- **40-60% Faster Hiring**: Accelerates the pipeline by identifying and engaging top talent 24/7.
- **Defensible ROI**: Projecting significant net savings per recruiter per month through labor cost reduction and displaced agency fees.

## ✨ Key Features
- **Semantic JD Parsing**: Extract key requirements and cultural context from raw Job Descriptions (PDF/TXT).
- **Multi-Source Sourcing**: Proactive search across LinkedIn, GitHub, and public portfolios using Serper.dev.
- **Candidate Scorecards**: Detailed markdown reports for every candidate with AI-generated selection rationale.
- **Ranked Recommendations**: A "Top 5" list with comparative analysis to help recruiters focus on the best fits.
- **Personalized Outreach**: Context-aware email drafts that reference a candidate's specific projects and achievements.

## 🏗️ Application Architecture (Multi-Agent Crew)
The system uses a sequential flow of four specialized agents:

1.  **Talent Sourcer (`researcher`)**: Finds candidates on the web using niche search strings and boolean logic.
2.  **Candidate Analyst (`evaluator`)**: Performs deep screening of profiles against the job requirements and logs all assumptions.
3.  **Recruitment Advisor (`recommender`)**: Acts as the final quality gate, ranking screened candidates by overall fit and growth potential.
4.  **Outreach Specialist (`writer`)**: Synthesizes backgrounds into highly compelling, personalized outreach messages.

## 🛠️ Getting Started

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended for dependency management)

### Installation
1.  Navigate to the application directory:
    ```bash
    cd recruitment-assistant
    ```
2.  Install dependencies:
    ```bash
    uv sync
    ```
3.  Set up environment variables (`.env`):
    ```env
    OPENAI_API_KEY=your_key_here
    SERPER_API_KEY=your_key_here
    ```

### Running the Assistant

#### 1. Start the Backend API
```bash
uv run uvicorn api.main:app --reload
```

#### 2. Start the Frontend UI
```bash
uv run streamlit run ui/app.py
```

## 📂 Project Structure
- `api/main.py`: FastAPI backend and orchestration entry point.
- `ui/app.py`: Streamlit recruiter dashboard.
- `agents/crew.py`: Core CrewAI agent and task definitions.
- `pyproject.toml`: Dependency and project metadata.
- `README.md`: This file.

## 🛡️ Regulatory & Ethics
This system is built with compliance in mind:
- **GDPR Ready**: Includes features for data erasure and PII redaction.
- **Explainable AI**: Every automated decision includes a human-readable "Selection Rationale."
- **Bias Mitigation**: Prototyped with a secondary "Bias-Check" layer to flag discriminatory language.

## ⏭️ Next Steps
The project is currently in the **Define** phase. The next step is for the **System Architect** to create the **SAD (System Architecture Document)** in `project-context/1.define/sad.md` to map out exact tool schemas and Pydantic models.

---
*Maintained by the Recruitment Assistant Development Crew.*
