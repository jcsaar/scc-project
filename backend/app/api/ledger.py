from fastapi import APIRouter, Query

from app.ledger.repository import ExposureClaim, ExposureRepository


def create_ledger_router(repository: ExposureRepository) -> APIRouter:
    router = APIRouter(prefix="/api/ledger", tags=["ledger"])

    @router.get("", response_model=list[ExposureClaim])
    def ledger(
        trust_zone_id: str = Query(min_length=1),
        protected_entity_id: str = Query(min_length=1),
    ) -> tuple[ExposureClaim, ...]:
        return repository.current_claims(trust_zone_id, protected_entity_id)

    return router
