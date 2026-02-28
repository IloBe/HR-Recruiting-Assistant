"""In-memory store that simulates campaign persistence and audit logs."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Optional, Sequence, Union

from recruitment_assistant.agents.crew import (
    EvaluationResult,
    OutreachDraft,
    RankedCandidate,
    RecruitmentCrew,
)

class CampaignStatus(str, Enum):
    """Finite status enums used by campaigns."""
    CREATED = "created"
    INITIALIZED = "initialized"
    RUNNING = "running"
    RANKED = "ranked"
    PURGED = "purged"


@dataclass
class CampaignRecord:
    """Aggregate telemetry for a stored campaign."""
    campaign_id: str
    title: str
    description: str
    job_description: str
    created_at: str
    status: CampaignStatus
    candidates: list[RankedCandidate] = field(default_factory=list)
    evaluations: list[EvaluationResult] = field(default_factory=list)
    outreach_drafts: list[OutreachDraft] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    serper_insights: dict[str, Any] = field(default_factory=dict)


class CampaignStore:
    """Thread-safe container for campaign records and audit events."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._campaigns: dict[str, CampaignRecord] = {}
        self._audit_logs: list[dict[str, Any]] = []
        self._populate_seed_campaign()

    def _next_id(self) -> str:
        """Produce a new campaign identifier."""
        return f"CAMP_{len(self._campaigns) + 1:03d}"

    def _timestamp(self) -> str:
        """Generate a UTC timestamp string for auditing."""
        return datetime.now(timezone.utc).replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")

    def _resolve_status(self, status: Union[str, CampaignStatus]) -> CampaignStatus:
        """Normalize status strings to CampaignStatus enums."""
        if isinstance(status, CampaignStatus):
            return status
        try:
            return CampaignStatus(status)
        except ValueError as exc:
            raise ValueError(f"Unknown campaign status: {status}") from exc

    def _build_metrics(self, candidates: Sequence[RankedCandidate]) -> dict[str, Any]:
        """Compute derived metrics from ranked candidates."""
        bias_checks = sum(len(candidate.bias_flags) for candidate in candidates)
        data_deficient = sum(
            1 for candidate in candidates if "Data Deficient" in candidate.tags
        )
        selection_rationale = (
            f"Top candidate: {candidates[0].name} ({candidates[0].role})"
            if candidates
            else "Pending"
        )
        return {
            "total_candidates": len(candidates),
            "bias_checks_passed": bias_checks == 0,
            "bias_checks": bias_checks,
            "data_deficient_count": data_deficient,
            "selection_rationale": selection_rationale,
            "generated_at": self._timestamp(),
        }

    def _populate_seed_campaign(self) -> None:
        """Create a seeded campaign for health checks."""
        crew = RecruitmentCrew(
            {
                "title": "AI Platform Engineer",
                "content": "Build resilient recruitment automation using CrewAI and FastAPI.",
            }
        )
        ranked, evaluations = crew.run_campaign()
        sanitized_ranked = [replace(candidate, bias_flags=[]) for candidate in ranked]
        metrics = self._build_metrics(sanitized_ranked)
        record = CampaignRecord(
            campaign_id="CAMP_001",
            title="Sample Campaign",
            description="Seed campaign for health/status checks",
            job_description="Auto-generated JD",
            created_at=self._timestamp(),
            status=CampaignStatus.CREATED,
            candidates=sanitized_ranked,
            evaluations=evaluations,
            metrics=metrics,
            serper_insights={"query": "seed campaign", "insights": []},
        )
        self._campaigns[record.campaign_id] = record
        self._audit_logs.append(
            {
                "timestamp": record.created_at,
                "campaign_id": record.campaign_id,
                "action": "campaign_seeded",
                "details": {"title": record.title},
            }
        )

    def create_campaign(
        self,
        title: str,
        description: str,
        job_description: str,
        candidates: Sequence[RankedCandidate],
        evaluations: Sequence[EvaluationResult],
        metrics: dict[str, Any],
        serper_insights: dict[str, Any],
    ) -> CampaignRecord:
        """Persist a newly created campaign and record the audit event."""
        with self._lock:
            campaign_id = self._next_id()
            record = CampaignRecord(
                campaign_id=campaign_id,
                title=title,
                description=description,
                job_description=job_description,
                created_at=self._timestamp(),
                status=CampaignStatus.INITIALIZED,
                candidates=list(candidates),
                evaluations=list(evaluations),
                metrics=dict(metrics),
                serper_insights=dict(serper_insights),
            )
            self._campaigns[campaign_id] = record
            self._audit_logs.append(
                {
                    "timestamp": record.created_at,
                    "campaign_id": campaign_id,
                    "action": "campaign_created",
                    "details": {"title": title, "status": record.status},
                }
            )
            return record

    def get_campaign(self, campaign_id: str) -> Optional[CampaignRecord]:
        """Return a campaign record by its identifier."""
        return self._campaigns.get(campaign_id)

    def update_status(self, campaign_id: str, status: Union[str, CampaignStatus]) -> None:
        """Update campaign status and log the change."""
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign:
                campaign.status = self._resolve_status(status)
                self._audit_logs.append(
                    {
                        "timestamp": self._timestamp(),
                        "campaign_id": campaign_id,
                        "action": "status_update",
                        "details": {"status": campaign.status},
                    }
                )

    def update_candidates(
        self,
        campaign_id: str,
        candidates: Sequence[RankedCandidate],
        evaluations: Sequence[EvaluationResult],
        metrics: dict[str, Any],
    ) -> Optional[CampaignRecord]:
        """Refresh stored candidate/evaluation data and metrics."""
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if not campaign:
                return None
            campaign.candidates = list(candidates)
            campaign.evaluations = list(evaluations)
            campaign.metrics = dict(metrics)
            campaign.status = CampaignStatus.RANKED
            return campaign

    def add_outreach_drafts(
        self, campaign_id: str, drafts: Sequence[OutreachDraft]
    ) -> Optional[list[OutreachDraft]]:
        """Attach outreach drafts to a campaign."""
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if not campaign:
                return None
            campaign.outreach_drafts = list(drafts)
            return campaign.outreach_drafts

    def record_audit(self, campaign_id: str, action: str, details: Optional[dict[str, Any]] = None) -> None:
        """Append an audit log entry."""
        self._audit_logs.append(
            {
                "timestamp": self._timestamp(),
                "campaign_id": campaign_id,
                "action": action,
                "details": details or {},
            }
        )

    def get_audit_logs(self) -> list[dict[str, Any]]:
        """Return a copy of the audit log list."""
        return list(self._audit_logs)

    def purge_campaign(self, campaign_id: str) -> bool:
        """Purge a campaign record and log the deletion."""
        with self._lock:
            if campaign_id in self._campaigns:
                del self._campaigns[campaign_id]
                self._audit_logs.append(
                    {
                        "timestamp": self._timestamp(),
                        "campaign_id": campaign_id,
                        "action": "campaign_purged",
                        "details": {"status": CampaignStatus.PURGED},
                    }
                )
                return True
        return False