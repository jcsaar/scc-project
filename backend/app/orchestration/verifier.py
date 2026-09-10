from app.domain.disclosures import DisclosureProposal, PrecisionLevel


class LocalVerifier:
    def revision_proposal(self, safe_feedback: str, project_id: str) -> DisclosureProposal:
        return DisclosureProposal(
            text=safe_feedback,
            purpose="Revise a recommendation that violates a mandatory local constraint",
            category="architecture.consistency",
            requested_precision=PrecisionLevel.BOOLEAN,
            protected_entity_ids=(project_id,),
            fact_keys=("consistency_requirement",),
        )

    def local_fallback(self) -> str:
        return (
            "Local-only fallback: partition write ownership around a stable business key, "
            "shorten transaction scope, and preserve strong consistency."
        )
