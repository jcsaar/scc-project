from app.domain.disclosures import DisclosureCandidate, PrecisionLevel
from app.domain.providers import CloudRecommendation
from app.domain.workflow import VerificationResult, VerificationStatus


def test_candidate_preserves_the_fact_keys_it_abstracts() -> None:
    candidate = DisclosureCandidate(
        text="A high-throughput environment",
        category="operations.throughput",
        precision=PrecisionLevel.BROAD_CATEGORY,
        fact_keys=("peak_tps",),
    )

    assert candidate.fact_keys == ("peak_tps",)


def test_verification_can_request_a_safe_cloud_revision() -> None:
    recommendation = CloudRecommendation(
        text="Adopt eventual consistency.",
        context_requests=(),
    )
    result = VerificationResult(
        status=VerificationStatus.REVISION_REQUIRED,
        safe_feedback="Preserve the mandatory consistency model.",
    )

    assert "eventual consistency" in recommendation.text
    assert result.status is VerificationStatus.REVISION_REQUIRED
