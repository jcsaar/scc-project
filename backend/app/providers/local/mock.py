from app.domain.disclosures import DisclosureProposal, PrecisionLevel
from app.domain.private import PrivateContext
from app.domain.providers import CloudRecommendation
from app.domain.workflow import VerificationResult, VerificationStatus
from app.providers.local.base import LocalModelProvider


class MockLocalModelProvider(LocalModelProvider):
    def analyse(self, prompt: str, context: PrivateContext) -> DisclosureProposal:
        del prompt
        return DisclosureProposal(
            text=(
                "A large regulated financial organisation operates a clustered relational "
                "database at 15k-20k transactions per second. Horizontal node expansion is "
                "contractually unavailable. Strong consistency must be preserved. Recommend "
                "approaches for reducing write contention."
            ),
            purpose="Recommend database contention controls",
            category="architecture.contention",
            requested_precision=PrecisionLevel.BOUNDED_RANGE,
            protected_entity_ids=(context.project_id,),
            fact_keys=(
                "customer_identity",
                "database_platform",
                "peak_tps",
                "node_expansion_allowed",
                "consistency_requirement",
            ),
        )

    def verify(
        self, recommendation: CloudRecommendation, context: PrivateContext
    ) -> VerificationResult:
        requires_strong_consistency = any(
            fact.semantic_key == "consistency_requirement" and fact.raw_value == "strong"
            for fact in context.facts
        )
        if requires_strong_consistency and "eventual consistency" in recommendation.text.lower():
            return VerificationResult(
                status=VerificationStatus.REVISION_REQUIRED,
                safe_feedback="Revise the proposal while preserving strong consistency.",
            )
        return VerificationResult(
            status=VerificationStatus.ACCEPTED,
            final_text=recommendation.text,
        )
