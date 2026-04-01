from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProfilingResult(Base):
    __tablename__ = "profiling_results"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    numeric_stats: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    categorical_stats: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    date_stats: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    correlation_stats: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    pps_stats: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
