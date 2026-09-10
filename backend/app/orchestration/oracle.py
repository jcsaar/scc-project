from app.domain.disclosures import DisclosureProposal
from app.domain.private import PrivateContext
from app.domain.providers import CloudContextRequest


class LocalOracle:
    _fact_by_category = {
        "architecture.partitioning": "natural_partition_key",
        "architecture.consistency": "consistency_requirement",
        "operations.latency": "maximum_queue_delay_ms",
        "operations.throughput": "peak_tps",
    }

    def answer(self, request: CloudContextRequest, context: PrivateContext) -> DisclosureProposal:
        semantic_key = self._fact_by_category[request.category]
        fact = next(item for item in context.facts if item.semantic_key == semantic_key)
        released = fact.generalizations.get(request.requested_precision.value)
        if released is None:
            released = next(iter(fact.generalizations.values()))
        text = str(released)
        if request.requested_precision.value == "boolean" and not text.lower().startswith("yes"):
            text = f"Yes, {text[0].lower()}{text[1:]}."
        return DisclosureProposal(
            text=text,
            purpose=request.purpose,
            category=request.category,
            requested_precision=request.requested_precision,
            protected_entity_ids=(context.project_id,),
            fact_keys=(semantic_key,),
        )
