from app.domain.disclosures import DisclosureCandidate, DisclosureProposal, PrecisionLevel
from app.domain.private import PrivateContext
from app.domain.providers import CloudRecommendation
from app.domain.workflow import VerificationResult, VerificationStatus
from app.providers.local.base import LocalModelProvider


class MockLocalModelProvider(LocalModelProvider):
    def analyse(self, prompt: str, context: PrivateContext) -> DisclosureProposal:
        lower_prompt = prompt.lower()
        if any(
            marker in lower_prompt
            for marker in (
                "blocked",
                "secret",
                "password",
                "api key",
                "access token",
                "private key",
            )
        ):
            return DisclosureProposal(
                text="password=synthetic-demo-secret",
                purpose="Attempt a protected disclosure for the denial demonstration",
                category="credential",
                requested_precision=PrecisionLevel.EXACT,
                protected_entity_ids=(context.project_id,),
                fact_keys=("credential",),
            )
        if any(
            marker in lower_prompt
            for marker in (
                "exact customer",
                "customer identity",
                "nric",
                "national id",
                "account number",
            )
        ):
            return DisclosureProposal(
                text="Aisha Rahman · NRIC S1234567A · account 004281",
                purpose="Attempt to identify a protected customer for the denial demonstration",
                category="identity.customer",
                requested_precision=PrecisionLevel.EXACT,
                protected_entity_ids=(context.project_id,),
                fact_keys=("customer_identity",),
            )
        return DisclosureProposal(
            text=(
                "A large regulated financial organisation operates a clustered relational "
                "database at 15k-20k transactions per second. Recommend approaches for reducing "
                "write contention while identifying any constraints that must be checked locally."
            ),
            purpose="Recommend database contention controls",
            category="architecture.contention",
            requested_precision=PrecisionLevel.BOUNDED_RANGE,
            protected_entity_ids=(context.project_id,),
            fact_keys=(
                "customer_identity",
                "database_platform",
                "peak_tps",
            ),
            alternatives=(
                DisclosureCandidate(
                    text=(
                        "A large regulated organisation uses a clustered relational database "
                        "at high transaction volume. Recommend safe contention controls."
                    ),
                    category="architecture.contention",
                    precision=PrecisionLevel.BROAD_CATEGORY,
                    fact_keys=("customer_identity", "database_platform", "peak_tps"),
                ),
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
