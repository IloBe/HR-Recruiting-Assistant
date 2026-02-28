import pytest

from recruitment_assistant.agents.crew import (
    CandidateSeed,
    EvaluationResult,
    JobDescriptionModel,
    OutreachDraft,
    RankedCandidate,
    RecruitmentCrew,
    ResearcherAgent,
    RecommenderAgent,
    WriterAgent,
    EvaluatorAgent,
    RankingPolicy,
    OutreachTemplate,
)


@pytest.fixture
def job_description() -> JobDescriptionModel:
    return JobDescriptionModel(title="Senior Python Engineer", content="Build scalable APIs")


def test_researcher_agent_returns_candidate_seeds(job_description: JobDescriptionModel) -> None:
    researcher = ResearcherAgent()
    seeds = researcher.research(job_description)
    assert seeds and all(isinstance(seed, CandidateSeed) for seed in seeds)
    assert any("Data Deficient" in seed.tags for seed in seeds)


def test_evaluator_agent_scores_candidates(job_description: JobDescriptionModel) -> None:
    researcher = ResearcherAgent()
    evaluator = EvaluatorAgent()
    seeds = researcher.research(job_description)
    evaluations = evaluator.evaluate(seeds)
    assert evaluations and all(isinstance(result, EvaluationResult) for result in evaluations)
    assert all(0.0 <= result.score <= 1.0 for result in evaluations)


def test_recommender_agent_rankings_respect_policy(job_description: JobDescriptionModel) -> None:
    researcher = ResearcherAgent()
    evaluator = EvaluatorAgent()
    recommender = RecommenderAgent()
    seeds = researcher.research(job_description)
    evaluations = evaluator.evaluate(seeds)
    ranked = recommender.recommend(evaluations, RankingPolicy(name="balanced"))
    assert ranked and all(isinstance(candidate, RankedCandidate) for candidate in ranked)
    assert ranked[0].final_score >= ranked[-1].final_score


def test_writer_agent_creates_outreach(job_description: JobDescriptionModel) -> None:
    researcher = ResearcherAgent()
    recommender = RecommenderAgent()
    evaluator = EvaluatorAgent()
    writer = WriterAgent()
    seeds = researcher.research(job_description)
    evaluations = evaluator.evaluate(seeds)
    ranked = recommender.recommend(evaluations, RankingPolicy())
    draft = writer.draft("CAMP_001", ranked[0], OutreachTemplate())
    assert isinstance(draft, OutreachDraft)
    assert "Hi" in draft.message


def test_recruitment_crew_run_campaign_and_risk(job_description: JobDescriptionModel) -> None:
    crew = RecruitmentCrew(jd_data=job_description)
    ranked, evaluations = crew.run_campaign(job_description)
    assert ranked and evaluations
    assert isinstance(ranked[0], RankedCandidate)
    risk_assessment = crew.assess_risk(evaluations)
    assert risk_assessment.level in {"standard", "elevated"}


def test_recruitment_crew_outreach_and_compliance(job_description: JobDescriptionModel) -> None:
    crew = RecruitmentCrew(jd_data=job_description)
    ranked, _ = crew.run_campaign(job_description)
    drafts = crew.generate_outreach("CAMP_COMPLIANCE", ranked[:1])
    summary = crew.compliance_summary()
    assert drafts and "GDPR" in drafts[0].message
    assert summary["eu_ai_act"] == "High-Risk HR"