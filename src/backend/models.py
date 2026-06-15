from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base


class User(Base):
    """Registered user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    runs: Mapped[list["ResearchRun"]] = relationship("ResearchRun", back_populates="user")


class ResearchRun(Base):
    """Saved result of a research pipeline execution."""

    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topics: Mapped[str] = mapped_column(Text, nullable=False)        # JSON array string
    competitors: Mapped[str] = mapped_column(Text, nullable=False)   # JSON array string
    urls: Mapped[str] = mapped_column(Text, nullable=False)          # JSON array string
    result_json: Mapped[str] = mapped_column(Text, nullable=False)   # Full PipelineResult JSON
    hallucination_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    run_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="runs")