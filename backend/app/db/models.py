import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Resume(Base):
    __tablename__ = "resume"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="uploaded")
    structured_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    interviews: Mapped[list["Interview"]] = relationship(back_populates="resume")


class Interview(Base):
    __tablename__ = "interview"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    resume_id: Mapped[str] = mapped_column(ForeignKey("resume.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="created")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    resume: Mapped["Resume"] = relationship(back_populates="interviews")
    turns: Mapped[list["TranscriptTurn"]] = relationship(back_populates="interview", order_by="TranscriptTurn.turn_index")
    feedback: Mapped["Feedback | None"] = relationship(back_populates="interview", uselist=False)


class TranscriptTurn(Base):
    __tablename__ = "transcript_turn"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    interview_id: Mapped[str] = mapped_column(ForeignKey("interview.id"), nullable=False)
    speaker: Mapped[str] = mapped_column(String, nullable=False)  # ai | candidate
    text: Mapped[str] = mapped_column(Text, nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    interview: Mapped["Interview"] = relationship(back_populates="turns")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    interview_id: Mapped[str] = mapped_column(ForeignKey("interview.id"), nullable=False, unique=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    communication: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    technical: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    resume_knowledge: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    weaknesses: Mapped[list | None] = mapped_column(JSON, nullable=True)
    improvements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    interview: Mapped["Interview"] = relationship(back_populates="feedback")
