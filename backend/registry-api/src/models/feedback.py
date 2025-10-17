"""Feedback model for analyst investigation.

Reference: FR-023 (Analyst feedback), US2
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base


class FeedbackType(str, Enum):
    """Feedback type classification."""
    FALSE_POSITIVE = "false_positive"
    TRUE_POSITIVE = "true_positive"
    INVESTIGATION_NEEDED = "investigation_needed"
    ESCALATION_REQUIRED = "escalation_required"
    RESOLVED = "resolved"


class FeedbackSeverity(str, Enum):
    """Feedback severity assessment."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Feedback(Base):
    """Analyst feedback on detections.

    Allows analysts to provide feedback on detection accuracy,
    track investigation progress, and improve the system.
    """
    __tablename__ = "feedback_records"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Detection reference
    detection_id = Column(String(255), nullable=False, index=True)  # From ClickHouse
    composite_id = Column(String(64), nullable=True, index=True)

    # Analyst who provided feedback
    analyst_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    analyst_email = Column(String(255), nullable=False)

    # Feedback classification
    feedback_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=True)

    # Feedback content
    notes = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)

    # Investigation status
    investigation_status = Column(String(50), nullable=False, default="open", index=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Tags for categorization
    tags = Column(JSONB, nullable=True)

    # Metadata
    additional_context = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    analyst = relationship("User", foreign_keys=[analyst_id])

    def __repr__(self) -> str:
        return f"<Feedback {self.feedback_type} by {self.analyst_email} on {self.detection_id}>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "detection_id": self.detection_id,
            "composite_id": self.composite_id,
            "analyst_id": str(self.analyst_id) if self.analyst_id else None,
            "analyst_email": self.analyst_email,
            "feedback_type": self.feedback_type,
            "severity": self.severity,
            "notes": self.notes,
            "recommended_action": self.recommended_action,
            "investigation_status": self.investigation_status,
            "resolution_notes": self.resolution_notes,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "tags": self.tags,
            "additional_context": self.additional_context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def is_open(self) -> bool:
        """Check if investigation is still open."""
        return self.investigation_status == "open"

    def is_resolved(self) -> bool:
        """Check if investigation is resolved."""
        return self.investigation_status == "resolved"

    def resolve(self, resolution_notes: str) -> None:
        """Mark feedback as resolved."""
        self.investigation_status = "resolved"
        self.resolution_notes = resolution_notes
        self.resolved_at = datetime.utcnow()

    def reopen(self) -> None:
        """Reopen a resolved investigation."""
        self.investigation_status = "open"
        self.resolved_at = None


class InvestigationNote(Base):
    """Investigation notes for collaborative analysis.

    Allows multiple analysts to add notes to an ongoing investigation.
    """
    __tablename__ = "investigation_notes"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Reference to feedback/detection
    feedback_id = Column(PGUUID(as_uuid=True), ForeignKey("feedback_records.id", ondelete="CASCADE"), nullable=False, index=True)
    detection_id = Column(String(255), nullable=False, index=True)

    # Author
    author_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_email = Column(String(255), nullable=False)

    # Note content
    note_text = Column(Text, nullable=False)

    # Note type
    note_type = Column(String(50), nullable=False, default="observation")  # observation, action_taken, question

    # Visibility
    is_internal = Column(Boolean, nullable=False, default=False)  # Internal notes vs shared with stakeholders

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    feedback = relationship("Feedback", backref="notes")
    author = relationship("User", foreign_keys=[author_id])

    def __repr__(self) -> str:
        return f"<InvestigationNote by {self.author_email} on {self.detection_id}>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "feedback_id": str(self.feedback_id),
            "detection_id": self.detection_id,
            "author_id": str(self.author_id) if self.author_id else None,
            "author_email": self.author_email,
            "note_text": self.note_text,
            "note_type": self.note_type,
            "is_internal": self.is_internal,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
