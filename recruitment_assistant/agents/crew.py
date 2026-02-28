"""Agents orchestrating candidate research, evaluation, ranking, and outreach."""

from __future__ import annotations

import hashlib
import html
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple
from uuid import uuid4

import structlog
from recruitment_assistant.logging_config import get_app_logger

logger = structlog.get_logger(__name__)
log = get_app_logger()


def _current_time() -> datetime:
    """Return the current UTC timestamp for traceability."""
    return datetime.now(timezone.utc)


def _stable_candidate_id(name: str, job_title: str) -> str:
    """Generate a deterministic candidate identifier based on the JD context."""
    key = f"{name}|{job_title}"
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:8]
    return f"CAN-{digest.upper()}"


class CrewError(Exception):
    """Domain errors surfaced by the RecruitmentCrew stack."""


@dataclass(frozen=True)
class JobDescriptionModel:
    """Represents the recruitment brief used to guide the agents."""
    title: str
    content: str
    created_at: datetime = field(default_factory=_current_time)
    classification: str = "Tier-2"


@dataclass(frozen=True)
class CandidateSeed:
    """Candidate attributes discovered during the research phase."""
    candidate_id: str
    name: str
    role: str
    score: float
    rationale: str
    tags: List[str]
    data_sources: List[str]
    sourced_at: datetime = field(default_factory=_current_time)


@dataclass(frozen=True)
class EvaluationResult:
    """Structured output from the evaluator agent per candidate."""
    candidate_id: str
    candidate_name: str
    role: str
    score: float
    rationale: str
    bias_flags: List[str]
    comments: str
    tags: List[str]
    profile_url: str
    evaluated_at: datetime = field(default_factory=_current_time)


@dataclass(frozen=True)
class RankedCandidate:
    """Final ranking details shared with the outreach workflow."""
    candidate_id: str
    name: str
    role: str
    final_score: float
    rationale: str
    tags: List[str]
    bias_flags: List[str]
    rank_label: str
    recommendation: str
    profile_url: str
    ranked_at: datetime = field(default_factory=_current_time)
    notes: Optional[str] = None


@dataclass(frozen=True)
class OutreachTemplate:
    """Reusable outreach script metadata and compliance hints."""
    tone: str = "professional"
    cta: str = "Let's schedule a time to chat"
    compliance_notes: str = "GDPR-compliant; transparent opt-out included."
    eu_ai_statement: str = (
        "High-risk HR workflow per EU AI Act; human oversight and record keeping enforced."
    )


@dataclass(frozen=True)
class OutreachDraft:
    """Candidate-specific outreach message generated from a template."""
    campaign_id: str
    candidate_id: str
    message: str
    template: OutreachTemplate
    draft_id: str = field(default_factory=lambda: f"DRAFT-{uuid4().hex[:6].upper()}")
    created_at: datetime = field(default_factory=_current_time)


@dataclass(frozen=True)
class RankingPolicy:
    """Configurable ranking knobs used by the recommender."""
    name: str = "balanced"
    diversity_bonus: float = 0.05
    bias_tolerance: float = 0.7
    respect_bias_flags: bool = True


@dataclass(frozen=True)
class CompliancePolicy:
    """Static compliance metadata for GDPR and EU AI Act claims."""
    gdpr_note: str = "Personal data processed only for recruitment; subject rights respected."
    eu_ai_act_category: str = "High-Risk HR"
    retention_days: int = 30
    logging_level: str = "INFO"


@dataclass(frozen=True)
class RiskAssessment:
    """Quantified risk artifacts emitted by the crew."""
    score: float
    bias_flags: int
    level: str
    evaluated_at: datetime = field(default_factory=_current_time)


BASE_PROFILES: List[Dict[str, Any]] = [
    {
        "name": "Alex Dev",
        "role": "Backend Engineer",
        "score": 0.60,
        "tags": ["Data Deficient", "Manual Review Required"],
        "data_sources": ["Serper.dev", "GitHub"],
        "profile_url": "https://talent.example.com/alex-dev",
    },
    {
        "name": "Marina Byte",
        "role": "Full Stack Engineer",
        "score": 0.72,
        "tags": ["High Confidence"],
        "data_sources": ["Serper.dev", "Portfolio"],
        "profile_url": "https://talent.example.com/marina-byte",
    },
    {
        "name": "Kai Ops",
        "role": "DevOps Engineer",
        "score": 0.68,
        "tags": ["Manual Review Required"],
        "data_sources": ["GitHub", "Browserless.io"],
        "profile_url": "https://talent.example.com/kai-ops",
    },
    {
        "name": "Nia Vector",
        "role": "Platform Architect",
        "score": 0.64,
        "tags": ["Leadership Potential"],
        "data_sources": ["LinkedIn", "Public Portfolio"],
        "profile_url": "https://talent.example.com/nia-vector",
    },
]


class AgentTracer:
    """Context manager that logs agent work boundaries."""

    def __init__(self, logger: structlog.BoundLogger, agent_name: str) -> None:
        self.logger = logger
        self.agent_name = agent_name

    @contextmanager
    def trace(self, operation: str, **context: Any) -> Iterator[None]:
        """Context manager that logs the start, error, and end of an agent operation."""
        start = datetime.now(timezone.utc)
        self.logger.info(
            "agent_operation_start",
            agent=self.agent_name,
            operation=operation,
            timestamp=start.isoformat(),
            **context,
        )
        try:
            yield
        except Exception as exc:
            self.logger.exception(
                "agent_operation_failed",
                agent=self.agent_name,
                operation=operation,
                error=str(exc),
                **context,
            )
            raise CrewError(f"{self.agent_name} failed during {operation}") from exc
        finally:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            self.logger.info(
                "agent_operation_end",
                agent=self.agent_name,
                operation=operation,
                duration_seconds=duration,
                **context,
            )


class BaseAgent:
    """Base class that injects tracing for every agent."""

    def __init__(self, name: str) -> None:
        self.tracer = AgentTracer(logger.bind(agent=name), name)


class ResearcherAgent(BaseAgent):
    """Searches candidate profiles to seed the evaluation pipeline."""
    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        candidate_pool: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> None:
        super().__init__("researcher")
        self.role = "Technical Talent Sourcer"
        self.goal = "Find a diverse slate that fits the JD"
        self.llm_model = llm_model
        self._candidate_pool = list(candidate_pool or BASE_PROFILES)

    def research(self, job_description: JobDescriptionModel, limit: int = 4) -> List[CandidateSeed]:
        """Discover candidate seeds that match the job description."""
        with self.tracer.trace(
            "research", job_title=job_description.title, limit=limit, model=self.llm_model
        ):
            seeds: List[CandidateSeed] = []
            content_bonus = len(job_description.content) / 400
            for profile in self._candidate_pool[:limit]:
                candidate_id = _stable_candidate_id(profile["name"], job_description.title)
                score = min(0.95, profile["score"] + content_bonus)
                rationale = (
                    f"{profile['name']} shows a {profile['role']} signal that aligns with {job_description.title}."
                )
                seeds.append(
                    CandidateSeed(
                        candidate_id=candidate_id,
                        name=profile["name"],
                        role=profile["role"],
                        score=score,
                        rationale=rationale,
                        tags=list(profile["tags"]),
                        data_sources=list(profile["data_sources"]),
                    )
                )
            return seeds


class EvaluatorAgent(BaseAgent):
    """Scores candidate seeds with bias-aware heuristics."""
    def __init__(
        self,
        llm_model: str = "gpt-4o",
        bias_thresholds: Optional[Mapping[str, float]] = None,
    ) -> None:
        super().__init__("evaluator")
        self.role = "Senior Technical Interviewer"
        self.goal = "Screen candidates objectively for bias"
        self.llm_model = llm_model
        self._bias_thresholds = dict(bias_thresholds or {"default": 0.65})

    def _derive_bias_flags(self, seed: CandidateSeed) -> List[str]:
        """Create bias flags based on the candidate seed metadata."""
        flags: List[str] = []
        if "Data Deficient" in seed.tags:
            flags.append("Data Deficient")
        if "Manual Review Required" in seed.tags:
            flags.append("Manual Review Required")
        threshold = self._bias_thresholds.get(seed.role, self._bias_thresholds["default"])
        if seed.score < threshold:
            flags.append("Bias Warning")
        return flags

    def evaluate(self, seeds: Sequence[CandidateSeed]) -> List[EvaluationResult]:
        """Score the provided candidate seeds and emit evaluation artifacts."""
        with self.tracer.trace(
            "evaluate", candidate_count=len(seeds), model=self.llm_model
        ):
            results: List[EvaluationResult] = []
            for seed in seeds:
                bias_flags = self._derive_bias_flags(seed)
                score = min(1.0, seed.score + 0.1)
                comments = (
                    f"Evaluated {seed.name}; {len(seed.tags)} tag(s) observed."
                )
                results.append(
                    EvaluationResult(
                        candidate_id=seed.candidate_id,
                        candidate_name=seed.name,
                        role=seed.role,
                        score=score,
                        rationale=seed.rationale,
                        bias_flags=bias_flags,
                        comments=comments,
                        tags=list(seed.tags),
                        profile_url=f"https://talent.example.com/{seed.name.lower().replace(' ', '-')}",
                    )
                )
            return results


class RecommenderAgent(BaseAgent):
    """Ranks evaluated candidates according to the current policy."""
    def __init__(self) -> None:
        super().__init__("recommender")
        self.role = "Recruitment Advisor"
        self.goal = "Rank candidates while flagging risks"
        self.active_policy = RankingPolicy()

    def recommend(
        self, evaluations: Sequence[EvaluationResult], policy: RankingPolicy
    ) -> List[RankedCandidate]:
        """Produce ranked candidates using the supplied policy."""
        self._apply_policy(policy)
        with self.tracer.trace("recommend", policy=policy.name):
            sorted_evaluations = sorted(evaluations, key=lambda entry: entry.score, reverse=True)
            ranked_candidates: List[RankedCandidate] = []
            for position, evaluation in enumerate(sorted_evaluations, start=1):
                diversity_boost = (
                    policy.diversity_bonus
                    if any(tag in ["Manual Review Required", "Data Deficient"] for tag in evaluation.tags)
                    else 0.0
                )
                final_score = min(1.0, evaluation.score + diversity_boost)
                rank_label = f"Tier {1 + (position - 1) // 2}"
                recommendation = (
                    f"Rank {position}: {evaluation.candidate_name} ({final_score:.2f})"
                )
                notes = "Manual review advised." if evaluation.bias_flags else None
                ranked_candidates.append(
                    RankedCandidate(
                        candidate_id=evaluation.candidate_id,
                        name=evaluation.candidate_name,
                        role=evaluation.role,
                        final_score=final_score,
                        rationale=evaluation.rationale,
                        tags=list(evaluation.tags),
                        bias_flags=list(evaluation.bias_flags),
                        rank_label=rank_label,
                        recommendation=recommendation,
                        profile_url=evaluation.profile_url,
                        notes=notes,
                    )
                )
            return ranked_candidates

    def _apply_policy(self, policy: RankingPolicy) -> None:
        """Apply a new ranking policy to the recommender."""
        self.active_policy = policy

    def set_policy(self, policy: RankingPolicy) -> None:
        """Expose policy switching to external callers."""
        self._apply_policy(policy)

class WriterAgent(BaseAgent):
    """Drafts compliant outreach touchpoints for ranked candidates."""
    def __init__(self) -> None:
        super().__init__("writer")
        self.role = "Personalized Outreach Specialist"
        self.goal = "Draft human-first, compliant outreach"

    def _sanitize(self, value: str) -> str:
        """Escape HTML-sensitive characters before using in outreach copy."""
        return html.escape(value)

    def draft(
        self, campaign_id: str, candidate: RankedCandidate, template: OutreachTemplate
    ) -> OutreachDraft:
        """Generate an outreach draft for a single ranked candidate."""
        with self.tracer.trace(
            "draft", campaign_id=campaign_id, candidate_id=candidate.candidate_id
        ):
            safe_name = self._sanitize(candidate.name)
            safe_role = self._sanitize(candidate.role)
            safe_rationale = self._sanitize(candidate.rationale.lower())
            safe_cta = self._sanitize(template.cta)
            safe_compliance = self._sanitize(template.compliance_notes)
            safe_eu_statement = self._sanitize(template.eu_ai_statement)
            message = (
                f"Hi {safe_name},\n\n"
                f"I saw your work as a {safe_role} and the way you {safe_rationale}\n"
                f"{safe_compliance} {safe_eu_statement}\n"
                f"{safe_cta}.\n\n"
                "Best,\nRecruitment Assistant Crew"
            )
            return OutreachDraft(
                campaign_id=campaign_id,
                candidate_id=candidate.candidate_id,
                message=message,
                template=template,
            )


class RecruitmentCrew:
    """Facade that orchestrates sourcing, evaluation, ranking, and outreach."""

    def __init__(
        self,
        jd_data: Optional[Dict[str, Any]] = None,
        policy: Optional[RankingPolicy] = None,
        compliance_policy: Optional[CompliancePolicy] = None,
        candidate_pool: Optional[Sequence[Dict[str, Any]]] = None,
        evaluator_bias_thresholds: Optional[Mapping[str, float]] = None,
    ) -> None:
        self.policy = policy or RankingPolicy()
        self.compliance = compliance_policy or CompliancePolicy()
        self.researcher = ResearcherAgent(candidate_pool=candidate_pool)
        self.evaluator = EvaluatorAgent(bias_thresholds=evaluator_bias_thresholds)
        self.recommender = RecommenderAgent()
        self.writer = WriterAgent()
        self.sourcer_model = self.researcher.llm_model
        self.eval_model = self.evaluator.llm_model
        self.tracer = AgentTracer(logger.bind(agent="crew"), "crew")
        self.latest_candidates: List[RankedCandidate] = []
        self.latest_evaluations: List[EvaluationResult] = []
        self.risk_history: List[RiskAssessment] = []
        self.job_description = self._normalize_job_description(jd_data)
        if isinstance(jd_data, dict):
            self.jd_data = jd_data
        else:
            self.jd_data = {
                "title": self.job_description.title,
                "content": self.job_description.content,
            }
        self.recommender.set_policy(self.policy)

    def _normalize_job_description(
        self, source: Optional[Dict[str, Any]]
    ) -> JobDescriptionModel:
        """Ensure the crew always has a job description model to work with."""
        if isinstance(source, JobDescriptionModel):
            return source
        if isinstance(source, dict):
            return JobDescriptionModel(
                title=source.get("title", "Talent Search"),
                content=source.get("content", "No JD provided."),
            )
        return JobDescriptionModel(title="Talent Search", content="No JD provided.")

    def _record_state(
        self,
        candidates: List[RankedCandidate],
        evaluations: List[EvaluationResult],
        risk: RiskAssessment,
    ) -> None:
        """Capture the latest state snapshots for future reruns."""
        self.latest_candidates = candidates
        self.latest_evaluations = evaluations
        self.risk_history.append(risk)

    def run_campaign(
        self, job_description: Optional[JobDescriptionModel] = None, limit: int = 4
    ) -> Tuple[List[RankedCandidate], List[EvaluationResult]]:
        """Execute a full campaign run from sourcing through ranking."""
        payload = job_description or self.job_description
        log.info("crew_run_campaign_start", job_title=payload.title, limit=limit)
        with self.tracer.trace("run_campaign", job_title=payload.title):
            seeds = self.researcher.research(payload, limit=limit)
            evaluations = self.evaluator.evaluate(seeds)
            ranked = self.recommender.recommend(evaluations, self.policy)
            risk = self.assess_risk(evaluations)
            self._record_state(ranked, evaluations, risk)
            log.info(
                "crew_run_campaign_complete",
                job_title=payload.title,
                candidates=len(ranked),
                bias_flags=sum(len(eval.bias_flags) for eval in evaluations),
            )
            return ranked, evaluations

    def rerank(
        self,
        evaluations: Optional[List[EvaluationResult]] = None,
        policy: Optional[RankingPolicy] = None,
    ) -> List[RankedCandidate]:
        """Re-rank candidates using a different policy or latest evaluations."""
        source = evaluations or self.latest_evaluations
        if not source:
            logger.warning("rerank_without_evaluations")
            return []
        active_policy = policy or self.policy
        self.policy = active_policy
        self.recommender.set_policy(active_policy)
        ranked = self.recommender.recommend(source, active_policy)
        risk = self.assess_risk(source)
        self._record_state(ranked, source, risk)
        return ranked

    def generate_outreach(
        self,
        campaign_id: str,
        candidates: Optional[List[RankedCandidate]] = None,
        template: Optional[OutreachTemplate] = None,
    ) -> List[OutreachDraft]:
        """Build outreach drafts for the current candidate roster."""
        roster = candidates or self.latest_candidates
        if not roster:
            logger.warning("generate_outreach_no_candidates", campaign_id=campaign_id)
            return []
        template = template or OutreachTemplate()
        return [self.writer.draft(
            campaign_id, candidate, template
        ) for candidate in roster]

    def assess_risk(self, evaluations: Sequence[EvaluationResult]) -> RiskAssessment:
        """Score the candidate slate for operational risk."""
        flag_count = sum(len(evaluation.bias_flags) for evaluation in evaluations)
        score = min(1.0, flag_count / max(1, len(evaluations)))
        level = "elevated" if score > 0.3 else "standard"
        return RiskAssessment(score=score, bias_flags=flag_count, level=level)

    def compliance_summary(self) -> Dict[str, Any]:
        """Return compliance metadata consumed by the UI."""
        return {
            "gdpr": self.compliance.gdpr_note,
            "eu_ai_act": self.compliance.eu_ai_act_category,
            "retention_days": self.compliance.retention_days,
            "logging_level": self.compliance.logging_level,
        }

    def recruitment_advisor(self) -> RecommenderAgent:
        """Expose the recommender for downstream inspection."""
        return self.recommender
