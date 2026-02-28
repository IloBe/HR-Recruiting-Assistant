import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from typing import Dict, Any

# @qa.eng: Aligning with pathlib standard and absolute import resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from recruitment_assistant.api.main import app, JobDescription
from recruitment_assistant.agents.crew import RecruitmentCrew


client = TestClient(app)

# Mock JD Data
mock_jd: Dict[str, Any] = {
    "title": "Senior Data Engineer",
    "content": "Expert in PySpark, Kubernetes and Azure Data Factory."
}

def test_campaign_creation_standard() -> None:
    """Tests standard campaign creation."""
    response = client.post("/campaign/create", json=mock_jd)
    assert response.status_code == 200
    assert response.json()["status"] == "initialized"    

def test_campaign_creation_invalid_title() -> None:
    """Tests edge case: Input Sanitization (SAD Section 6)."""
    invalid_jd = {"title": "SE", "content": "Too short"}
    response = client.post("/campaign/create", json=invalid_jd)
    assert response.status_code == 400
    assert "Invalid JD Title" in response.json()["detail"]

def test_agent_initialization_typing() -> None:
    """Tests if RecruitmentCrew initializes with correct typing."""
    crew = RecruitmentCrew(mock_jd)
    assert isinstance(crew.jd_data, dict)
    assert crew.eval_model == "gpt-4o"
    assert crew.sourcer_model == "gpt-4o-mini"

def test_campaign_status_polling() -> None:
    """SAD requires async status polling."""
    response = client.get("/campaigns/CAMP_001/status")
    assert response.status_code == 200
    assert response.json()["campaign_id"] == "CAMP_001"
    assert response.json()["status"] in {"created", "running", "completed"}

def test_health_check_payload() -> None:
    """Tests the production-grade health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "version" in response.json()

def test_campaign_report_structure() -> None:
    """Tests the reporting endpoint structure (SAD Section 8/9)."""
    response = client.get("/campaign/CAMP_001/report")
    assert response.status_code == 200
    # @qa.eng: Ensure metrics key is present in response
    metrics = response.json()["metrics"]
    assert "bias_checks_passed" in metrics
    assert metrics["bias_checks_passed"] is True
    assert "data_deficient_count" in metrics
    assert metrics["total_candidates"] >= 0
    assert "selection_rationale" in metrics

def test_recruitment_advisor_integration() -> None:
    """Tests if the Recruitment Advisor agent is present in the Crew."""
    crew = RecruitmentCrew(mock_jd)
    advisor = crew.recruitment_advisor()
    assert advisor.role == 'Recruitment Advisor'
    assert "Ranking" in advisor.goal or "Rank" in advisor.goal

def test_candidate_ranking_payload() -> None:
    """Tests ranking endpoint returns rationales and scores."""
    rank_payload = {"filters": ["diversity"], "limit": 3}
    response = client.post("/campaigns/CAMP_001/rank", json=rank_payload)
    assert response.status_code == 200
    ranked = response.json()["ranked_candidates"]
    assert isinstance(ranked, list)
    assert ranked[0]["score"] >= 0 and ranked[0]["score"] <= 1
    assert "rationale" in ranked[0]

def test_outreach_drafts_and_send() -> None:
    """Tests outreach draft creation and send queue."""
    response = client.post("/campaigns/CAMP_001/outreach")
    assert response.status_code == 200
    drafts = response.json()["drafts"]
    assert drafts and "candidate_id" in drafts[0]
    send_resp = client.post(
        "/outreach/send",
        json={"campaign_id": "CAMP_001", "candidate_id": drafts[0]["candidate_id"], "message": "Hi there"}
    )
    assert send_resp.status_code == 200
    assert send_resp.json()["status"] in {"queued", "sent"}

def test_candidate_ranking_and_human_flagging_logic() -> None:
    """
    Tests for HITL (Human-in-the-Loop) Transparency (SAD Section 3/4).
    Verifies that candidates include ranking rationale and specific metrics 
    that trigger manual human analysis.
    """
    response = client.get("/campaign/CAMP_001/candidates")
    assert response.status_code == 200
    candidates = response.json()
    
    for cand in candidates:
        # 1. Rationale Verification (HITL Transparency requirement)
        assert "rationale" in cand
        assert len(cand["rationale"]) > 10, "Rationale should be descriptive"
        
        # 2. Ranking/Tiering verification
        assert "score" in cand
        assert 0 <= cand["score"] <= 1.0
        
        # 3. Human Intervention Metrics (Manual Review triggers)
        # We check if candidates are appropriately tagged for human analysis
        expected_manual_review_tags = ["Data Deficient", "Manual Review Required", "Bias Warning"]
        has_human_review_flag = any(
            any(flag in tag for flag in expected_manual_review_tags) 
            for tag in cand.get("tags", [])
        )
        
        # In our mock data/contract, Alex Dev should trigger this
        if cand["name"] == "Alex Dev":
            assert has_human_review_flag, "Candidates with sparse data must be flagged for human review"
