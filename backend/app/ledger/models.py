from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String, nullable=False)
    trust_zone_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    initial_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_budget: Mapped[int] = mapped_column(Integer, nullable=False)


class ExposureClaimRow(Base):
    __tablename__ = "exposure_claims"
    __table_args__ = (UniqueConstraint("trust_zone_id", "protected_entity_id", "semantic_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trust_zone_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    protected_entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String, nullable=False)
    semantic_key: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    safe_representation: Mapped[str] = mapped_column(String, nullable=False)
    representation_hash: Mapped[str] = mapped_column(String, nullable=False)
    precision: Mapped[str] = mapped_column(String, nullable=False)
    first_exposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_exposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ExposureEventRow(Base):
    __tablename__ = "exposure_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    protected_entity_id: Mapped[str] = mapped_column(String, nullable=False)
    semantic_key: Mapped[str] = mapped_column(String, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    reason_code: Mapped[str] = mapped_column(String, nullable=False)
    risk_before: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_after: Mapped[int] = mapped_column(Integer, nullable=False)
    disclosure_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
