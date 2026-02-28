"""FastAPI scaffolding for recruitment campaigns, ranking, and outreach."""

from __future__ import annotations

from datetime import datetime, timezone
from os import getenv
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4
import time

import crewai
import structlog
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Body, FastAPI, HTTPException
from fastapi import Request
from pydantic import BaseModel, Field

from recruitment_assistant.agents.crew import (
    JobDescriptionModel,
    OutreachDraft,
    OutreachTemplate,
    RankedCandidate,
    RecruitmentCrew,
    RankingPolicy,
)
from recruitment_assistant.api.store import CampaignStore
from recruitment_assistant.logging_config import get_app_logger

logger = structlog.get_logger(__name__)
CREWAI_VERSION = crewai.__version__
load_dotenv()

APP_NAME = getenv("APP_NAME", "Recruitment Assistant AI Backend")
APP_ENV = getenv("APP_ENV", "development")
OPENAI_MODEL = getenv("OPENAI_MODEL", "gpt-4o")
app = FastAPI(title=f"{APP_NAME} ({APP_ENV})")
log = get_app_logger()
log.info("application_startup", app_env=APP_ENV, openai_model=OPENAI_MODEL, crewai_version=CREWAI_VERSION)

crew = RecruitmentCrew()
store = CampaignStore()


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable[[Request], Any]):
	request_id = str(uuid4())
	trace_id = request.headers.get("x-trace-id", request_id)
	user_id = request.headers.get("x-user-id")
	start = time.monotonic()
	response: Optional[Any] = None
	with log.contextualize(request_id=request_id, trace_id=trace_id, user_id=user_id):
		log.info(
			"http_request_start",
			method=request.method,
			path=request.url.path,
		)
		try:
			response = await call_next(request)
		except Exception as exc:  # pragma: no cover - log and re-raise
			log.exception(
				"http_request_failed",
				method=request.method,
				path=request.url.path,
				error=str(exc),
			)
			raise
		finally:
			duration = (time.monotonic() - start) * 1000
			status_code = response.status_code if response else 500
			log.info(
				"http_request_complete",
				method=request.method,
				path=request.url.path,
				status=status_code,
				duration_ms=round(duration, 1),
			)
			if response is not None:
				response.headers["x-request-id"] = request_id
	return response


class CampaignCreateRequest(BaseModel):
	"""Payload used to initialize a new campaign."""
	title: str = Field(..., min_length=1)
	description: str = Field("Recruitment campaign", min_length=1)
	content: str = Field(...)


class JobDescription(BaseModel):
	"""Job description representation posted to the crew."""
	title: str
	content: str


class RankRequest(BaseModel):
	"""Ranking request controlling the policy strategy and result limit."""
	strategy: Optional[str] = "balanced"
	limit: Optional[int] = None


class OutreachRequest(BaseModel):
	"""Optional controls for outreach template overrides."""
	campaign_id: Optional[str] = None
	template_tone: Optional[str] = None
	cta: Optional[str] = None
	compliance_notes: Optional[str] = None


class OutreachSendRequest(BaseModel):
	"""Message used when sending outreach drafts."""
	campaign_id: str
	candidate_id: str
	message: str = Field(..., min_length=1)


class SerperRequest(BaseModel):
	"""Minimal search payload for the Serper integration."""
	query: str = Field(..., min_length=3)


class CampaignStatusResponse(BaseModel):
	"""Response shape used by the status endpoint."""
	campaign_id: str
	status: str
	last_updated: str
	total_candidates: int
	bias_flags: int
	phase: str
	metrics: Dict[str, Any]


def _validate_jd(title: str, content: str) -> None:
	"""Raise HTTP errors when the JD payload is malformed."""
	if len(title.strip()) < 5:
		raise HTTPException(status_code=400, detail="Invalid JD Title")
	if len(content.strip()) < 20:
		raise HTTPException(status_code=400, detail="Invalid JD content")


def safe_crew_call(operation: Callable[[], Any], detail: str) -> Any:
	"""Safely invoke crew operations and wrap errors in HTTP responses."""
	try:
		return operation()
	except Exception as exc:  # pragma: no cover - keep request from crashing
		logger.exception("crew-operation-failed", detail=detail, error=str(exc))
		raise HTTPException(status_code=500, detail=f"Crew operation '{detail}' failed: {exc}")


def build_metrics(ranked: List[RankedCandidate], evaluations: List[Any]) -> Dict[str, Any]:
	"""Summarize ranking and bias data for a candidate slate."""
	bias_checks = sum(len(eval.bias_flags) for eval in evaluations)
	data_deficient = sum(1 for candidate in ranked if "Data Deficient" in candidate.tags)
	selection_rationale = (
		f"{ranked[0].name} ({ranked[0].role}) leads the pack"
		if ranked
		else "Campaign initializing"
	)
	return {
		"total_candidates": len(ranked),
		"bias_checks": bias_checks,
		"bias_checks_passed": bias_checks == 0,
		"data_deficient_count": data_deficient,
		"selection_rationale": selection_rationale,
		"generated_at": datetime.now(timezone.utc)
			.replace(second=0, microsecond=0)
			.strftime("%Y-%m-%d %H:%M"),
	}


def run_serper_search(query: str) -> Dict[str, Any]:
	"""Wrap the Serper integration for candidate research insights."""
	logger.info("serper-search", query=query)
	return {
		"query": query,
		"insights": [
			{"source": "SerperAI", "summary": f"Top skills matched for {query}"},
		],
	}



def _serialize_candidate(candidate: RankedCandidate) -> Dict[str, Any]:
	"""Convert a RankedCandidate to a minimal API payload."""
	return {
		"candidate_id": candidate.candidate_id,
		"name": candidate.name,
		"role": candidate.role,
		"score": candidate.final_score,
		"rationale": candidate.rationale,
		"rank_label": candidate.rank_label,
		"bias_flags": candidate.bias_flags,
		"tags": candidate.tags,
		"profile_url": candidate.profile_url,
	}


def _persist_campaign(
	payload: CampaignCreateRequest, job_description: JobDescriptionModel
) -> Dict[str, Any]:
	"""Run the crew and store the resulting campaign record."""
	ranked, evaluations = safe_crew_call(lambda: crew.run_campaign(job_description), "run_campaign")
	metrics = build_metrics(ranked, evaluations)
	serper_insights = run_serper_search(job_description.content or payload.title)
	record = store.create_campaign(
		title=payload.title,
		description=payload.description,
		job_description=job_description.content or "",
		candidates=ranked,
		evaluations=evaluations,
		metrics=metrics,
		serper_insights=serper_insights,
	)
	store.record_audit(record.campaign_id, "campaign_initialized", {"jd": payload.title})
	return {
		"campaign_id": record.campaign_id,
		"status": record.status,
		"metrics": metrics,
		"serper": serper_insights,
	}


@app.get("/")
def root() -> Dict[str, str]:
	"""Handle the root health check endpoint."""
	return {"message": "Recruitment Assistant AI API is live."}


@app.get("/health")
def health() -> Dict[str, str]:
	"""Return application and dependency metadata for uptime monitoring."""
	return {
		"status": "healthy",
		"version": CREWAI_VERSION,
		"app_env": APP_ENV,
		"openai_model": OPENAI_MODEL,
	}


@app.post("/campaigns")
def create_campaign(payload: CampaignCreateRequest) -> Dict[str, Any]:
	"""Validate and persist a new campaign run."""
	_validate_jd(payload.title, payload.content)
	job_description = JobDescriptionModel(title=payload.title, content=payload.content)
	return _persist_campaign(payload, job_description)


@app.post("/campaign/create")
def create_campaign_alias(payload: CampaignCreateRequest) -> Dict[str, Any]:
	"""Alias endpoint for campaign creation."""
	return create_campaign(payload)


@app.get("/campaigns/{campaign_id}/status", response_model=CampaignStatusResponse)
def campaign_status(campaign_id: str) -> CampaignStatusResponse:
	"""Fetch the current status of a campaign."""
	campaign = store.get_campaign(campaign_id)
	if not campaign:
		raise HTTPException(status_code=404, detail="Campaign not found")
	return CampaignStatusResponse(
		campaign_id=campaign.campaign_id,
		status=campaign.status,
		last_updated=campaign.created_at,
		total_candidates=len(campaign.candidates),
		bias_flags=sum(len(candidate.bias_flags) for candidate in campaign.candidates),
		phase="ranking" if campaign.candidates else "initializing",
		metrics=campaign.metrics,
	)


@app.get("/campaigns/{campaign_id}/candidates")
@app.get("/campaign/{campaign_id}/candidates")
def campaign_candidates(campaign_id: str) -> List[Dict[str, Any]]:
	"""List serialized candidate data for the requested campaign."""
	campaign = store.get_campaign(campaign_id)
	if not campaign:
		raise HTTPException(status_code=404, detail="Campaign not found")
	return [_serialize_candidate(candidate) for candidate in campaign.candidates]


@app.post("/campaigns/{campaign_id}/rank")
def rank_candidates(campaign_id: str, payload: RankRequest) -> Dict[str, Any]:
	"""Re-rank candidates using the requested strategy."""
	campaign = store.get_campaign(campaign_id)
	if not campaign:
		raise HTTPException(status_code=404, detail="Campaign not found")
	if not campaign.evaluations:
		raise HTTPException(status_code=400, detail="No evaluations available for ranking")
	policy = RankingPolicy(name=payload.strategy or "balanced")
	ranked = safe_crew_call(lambda: crew.rerank(campaign.evaluations, policy), "rerank")
	if payload.limit and payload.limit > 0:
		ranked = ranked[: payload.limit]
	metrics = build_metrics(ranked, campaign.evaluations)
	updated = store.update_candidates(campaign_id, ranked, campaign.evaluations, metrics)
	if not updated:
		raise HTTPException(status_code=500, detail="Failed to update ranking")
	store.record_audit(campaign_id, "ranking_updated", {"strategy": policy.name})
	return {
		"campaign_id": campaign_id,
		"ranked_candidates": [_serialize_candidate(candidate) for candidate in ranked],
		"metrics": metrics,
	}

@app.post("/campaigns/{campaign_id}/outreach")
def generate_outreach(
	campaign_id: str,
	payload: Optional[OutreachRequest] = Body(None),
) -> Dict[str, Any]:
	"""Generate outreach drafts for all ranked candidates."""
	campaign = store.get_campaign(campaign_id)
	if not campaign:
		raise HTTPException(status_code=404, detail="Campaign not found")
	payload = payload or OutreachRequest()
	template = OutreachTemplate(
		tone=payload.template_tone or "professional",
		cta=payload.cta or "Let's schedule time to chat",
		compliance_notes=payload.compliance_notes
		or "GDPR-compliant; transparent opt-out included",
	)
	drafts = safe_crew_call(
		lambda: crew.generate_outreach(campaign_id, campaign.candidates, template),
		"generate_outreach",
	)
	persisted = store.add_outreach_drafts(campaign_id, drafts)
	if persisted is None:
		raise HTTPException(status_code=500, detail="Failed to persist outreach drafts")
	store.record_audit(campaign_id, "outreach_generated", {"draft_count": len(persisted)})
	return {
		"campaign_id": campaign_id,
		"drafts": [
			{
				"draft_id": draft.draft_id,
				"candidate_id": draft.candidate_id,
				"message": draft.message,
			}
			for draft in persisted
		],
	}


@app.post("/outreach/send")
def send_outreach(payload: OutreachSendRequest, background_tasks: BackgroundTasks) -> Dict[str, str]:
	"""Queue a background task to record outreach dispatch."""
	campaign = store.get_campaign(payload.campaign_id)
	if not campaign:
		raise HTTPException(status_code=404, detail="Campaign not found")
	background_tasks.add_task(
		store.record_audit,
		payload.campaign_id,
		"outreach_sent",
		{"candidate_id": payload.candidate_id, "message": payload.message},
	)
	return {"status": "queued", "candidate_id": payload.candidate_id}


@app.get("/campaigns/{campaign_id}/report")
@app.get("/campaign/{campaign_id}/report")
def campaign_report(campaign_id: str) -> Dict[str, Any]:
	"""Return the stored campaign report payload."""
	campaign = store.get_campaign(campaign_id)
	if not campaign:
		raise HTTPException(status_code=404, detail="Campaign not found")
	return {
		"campaign_id": campaign.campaign_id,
		"status": campaign.status,
		"metrics": campaign.metrics,
		"bias_checks": [
			{"flag": flag, "candidate_id": candidate.candidate_id}
			for candidate in campaign.candidates
			for flag in candidate.bias_flags
		],
		"selection_rationale": campaign.metrics.get("selection_rationale", "Pending"),
		"serper_insights": campaign.serper_insights,
	}


@app.get("/audit-logs")
def audit_logs() -> List[Dict[str, Any]]:
	"""Expose stored audit log entries."""
	return store.get_audit_logs()


@app.delete("/campaigns/{campaign_id}")
def purge_campaign(campaign_id: str) -> Dict[str, str]:
	"""Remove a campaign from the in-memory store."""
	if store.purge_campaign(campaign_id):
		return {"campaign_id": campaign_id, "status": "purged"}
	raise HTTPException(status_code=404, detail="Campaign not found")


@app.post("/serper/search")
def serper_search(payload: SerperRequest) -> Dict[str, Any]:
	"""Proxy a Serper search for candidate insights."""
	return run_serper_search(payload.query)
