from datetime import UTC, datetime

from pydantic import Field
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.domain.disclosures import StrictFrozenModel
from app.ledger.models import Base, ExposureClaimRow, ExposureEventRow, SessionRow


class LedgerIntegrityError(RuntimeError):
    pass


class ExposureCommit(StrictFrozenModel):
    session_id: str
    protected_entity_id: str
    dimension: str
    semantic_key: str
    category: str
    safe_representation: str
    representation_hash: str
    precision: str
    base_weight: int = Field(default=20, ge=0, le=100)
    risk_before: int = Field(ge=0, le=100)
    risk_after: int = Field(ge=0, le=100)
    disclosure_delta: int = Field(ge=0, le=100)
    budget_cost: int = Field(ge=0)
    decision: str
    reason_code: str


class ExposureClaim(StrictFrozenModel):
    trust_zone_id: str
    protected_entity_id: str
    dimension: str
    semantic_key: str
    category: str
    safe_representation: str
    representation_hash: str
    precision: str
    base_weight: int


class ExposureRepository:
    _precision_rank = {
        "boolean": 0,
        "broad_category": 1,
        "coarse_range": 2,
        "bounded_range": 3,
        "approximate": 4,
        "exact": 5,
    }

    def __init__(self, database_url: str) -> None:
        options = (
            {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
            if database_url == "sqlite://"
            else {}
        )
        self._engine = create_engine(database_url, **options)
        if database_url.startswith("sqlite"):
            event.listen(self._engine, "connect", self._configure_sqlite)

    @staticmethod
    def _configure_sqlite(dbapi_connection: object, connection_record: object) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    def initialize(self) -> None:
        Base.metadata.create_all(self._engine)

    def register_session(
        self, session_id: str, employee_id: str, trust_zone_id: str, budget: int
    ) -> None:
        with Session(self._engine) as session, session.begin():
            session.add(
                SessionRow(
                    id=session_id,
                    employee_id=employee_id,
                    trust_zone_id=trust_zone_id,
                    initial_budget=budget,
                    remaining_budget=budget,
                )
            )

    def commit_disclosure(self, disclosure: ExposureCommit) -> None:
        with Session(self._engine) as database, database.begin():
            session = database.get(SessionRow, disclosure.session_id)
            if session is None or session.remaining_budget < disclosure.budget_cost:
                raise LedgerIntegrityError("Session or disclosure budget is invalid")
            claim_statement = select(ExposureClaimRow).where(
                ExposureClaimRow.trust_zone_id == session.trust_zone_id,
                ExposureClaimRow.protected_entity_id == disclosure.protected_entity_id,
                ExposureClaimRow.semantic_key == disclosure.semantic_key,
            )
            claim = database.scalar(claim_statement)
            if claim is None:
                database.add(
                    ExposureClaimRow(
                        trust_zone_id=session.trust_zone_id,
                        protected_entity_id=disclosure.protected_entity_id,
                        dimension=disclosure.dimension,
                        semantic_key=disclosure.semantic_key,
                        category=disclosure.category,
                        safe_representation=disclosure.safe_representation,
                        representation_hash=disclosure.representation_hash,
                        precision=disclosure.precision,
                        base_weight=disclosure.base_weight,
                    )
                )
            else:
                claim.last_exposed_at = datetime.now(UTC)
                if (
                    self._precision_rank[disclosure.precision]
                    > self._precision_rank[claim.precision]
                ):
                    claim.safe_representation = disclosure.safe_representation
                    claim.representation_hash = disclosure.representation_hash
                    claim.precision = disclosure.precision
                    claim.base_weight = disclosure.base_weight
            database.add(
                ExposureEventRow(
                    session_id=session.id,
                    protected_entity_id=disclosure.protected_entity_id,
                    semantic_key=disclosure.semantic_key,
                    decision=disclosure.decision,
                    reason_code=disclosure.reason_code,
                    risk_before=disclosure.risk_before,
                    risk_after=disclosure.risk_after,
                    disclosure_delta=disclosure.disclosure_delta,
                    budget_cost=disclosure.budget_cost,
                )
            )
            session.remaining_budget -= disclosure.budget_cost

    def current_claims(
        self, trust_zone_id: str, protected_entity_id: str
    ) -> tuple[ExposureClaim, ...]:
        statement = select(ExposureClaimRow).where(
            ExposureClaimRow.trust_zone_id == trust_zone_id,
            ExposureClaimRow.protected_entity_id == protected_entity_id,
        )
        with Session(self._engine) as session:
            rows = session.scalars(statement).all()
            return tuple(
                ExposureClaim(
                    trust_zone_id=row.trust_zone_id,
                    protected_entity_id=row.protected_entity_id,
                    dimension=row.dimension,
                    semantic_key=row.semantic_key,
                    category=row.category,
                    safe_representation=row.safe_representation,
                    representation_hash=row.representation_hash,
                    precision=row.precision,
                    base_weight=row.base_weight,
                )
                for row in rows
            )

    def remaining_budget(self, session_id: str) -> int:
        with Session(self._engine) as session:
            row = session.get(SessionRow, session_id)
            if row is None:
                raise LedgerIntegrityError("Session not found")
            return row.remaining_budget
