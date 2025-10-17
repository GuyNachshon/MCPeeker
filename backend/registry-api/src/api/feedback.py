"""Feedback API endpoints for analyst investigation.

Reference: FR-023 (Analyst feedback), US2
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.rbac import Role, get_current_user, require_role
from ..audit.logger import AuditAction, AuditLogger, audit_detection_access
from ..database import get_db
from ..models import User
from ..models.feedback import Feedback, FeedbackSeverity, FeedbackType, InvestigationNote

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


# Pydantic schemas
class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    detection_id: str = Field(..., description="Detection ID from ClickHouse")
    composite_id: Optional[str] = Field(None, description="Composite identifier")
    feedback_type: FeedbackType = Field(..., description="Feedback classification")
    severity: Optional[FeedbackSeverity] = Field(None, description="Severity assessment")
    notes: str = Field(..., min_length=10, description="Feedback notes")
    recommended_action: Optional[str] = Field(None, description="Recommended action")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    additional_context: Optional[dict] = Field(None, description="Additional context")


class FeedbackUpdate(BaseModel):
    """Schema for updating feedback."""
    feedback_type: Optional[FeedbackType] = None
    severity: Optional[FeedbackSeverity] = None
    notes: Optional[str] = Field(None, min_length=10)
    recommended_action: Optional[str] = None
    investigation_status: Optional[str] = None
    tags: Optional[List[str]] = None
    additional_context: Optional[dict] = None


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""
    id: str
    detection_id: str
    composite_id: Optional[str]
    analyst_id: Optional[str]
    analyst_email: str
    feedback_type: str
    severity: Optional[str]
    notes: str
    recommended_action: Optional[str]
    investigation_status: str
    resolution_notes: Optional[str]
    resolved_at: Optional[str]
    tags: Optional[List[str]]
    additional_context: Optional[dict]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ResolutionRequest(BaseModel):
    """Schema for resolving feedback."""
    resolution_notes: str = Field(..., min_length=10, description="Resolution notes")


class InvestigationNoteCreate(BaseModel):
    """Schema for creating investigation note."""
    note_text: str = Field(..., min_length=10, description="Note content")
    note_type: str = Field("observation", description="Note type: observation, action_taken, question")
    is_internal: bool = Field(False, description="Internal note visibility")


class InvestigationNoteResponse(BaseModel):
    """Schema for investigation note response."""
    id: str
    feedback_id: str
    detection_id: str
    author_id: Optional[str]
    author_email: str
    note_text: str
    note_type: str
    is_internal: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# API endpoints

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
@require_role([Role.ANALYST, Role.ADMIN])
async def submit_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback on a detection (Analyst, Admin only).

    Allows analysts to provide feedback on detection accuracy and
    track investigation progress.
    """
    # Create feedback record
    db_feedback = Feedback(
        detection_id=feedback.detection_id,
        composite_id=feedback.composite_id,
        analyst_id=current_user.id,
        analyst_email=current_user.email,
        feedback_type=feedback.feedback_type.value,
        severity=feedback.severity.value if feedback.severity else None,
        notes=feedback.notes,
        recommended_action=feedback.recommended_action,
        tags=feedback.tags,
        additional_context=feedback.additional_context,
    )

    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)

    # TODO: Audit log the feedback submission
    # audit_logger.log(...)

    return db_feedback.to_dict()


@router.get("", response_model=List[FeedbackResponse])
async def list_feedback(
    detection_id: Optional[str] = Query(None, description="Filter by detection ID"),
    feedback_type: Optional[FeedbackType] = Query(None, description="Filter by feedback type"),
    investigation_status: Optional[str] = Query(None, description="Filter by investigation status"),
    analyst_email: Optional[str] = Query(None, description="Filter by analyst email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List feedback records.

    Analysts and Admins can view all feedback.
    """
    if not current_user.is_analyst and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only analysts and admins can view feedback"
        )

    query = db.query(Feedback)

    # Apply filters
    if detection_id:
        query = query.filter(Feedback.detection_id == detection_id)

    if feedback_type:
        query = query.filter(Feedback.feedback_type == feedback_type.value)

    if investigation_status:
        query = query.filter(Feedback.investigation_status == investigation_status)

    if analyst_email:
        query = query.filter(Feedback.analyst_email == analyst_email)

    # Order by most recent first
    query = query.order_by(Feedback.created_at.desc())

    # Pagination
    feedback_records = query.offset(skip).limit(limit).all()

    return [f.to_dict() for f in feedback_records]


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific feedback record."""
    if not current_user.is_analyst and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only analysts and admins can view feedback"
        )

    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    return feedback.to_dict()


@router.patch("/{feedback_id}", response_model=FeedbackResponse)
@require_role([Role.ANALYST, Role.ADMIN])
async def update_feedback(
    feedback_id: UUID,
    update: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update feedback record.

    Analysts can update their own feedback.
    Admins can update any feedback.
    """
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    # Check permissions
    if not current_user.is_admin and feedback.analyst_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own feedback"
        )

    # Apply updates
    for field, value in update.dict(exclude_unset=True).items():
        if isinstance(value, (FeedbackType, FeedbackSeverity)):
            value = value.value
        setattr(feedback, field, value)

    db.commit()
    db.refresh(feedback)

    return feedback.to_dict()


@router.post("/{feedback_id}/resolve", response_model=FeedbackResponse)
@require_role([Role.ANALYST, Role.ADMIN])
async def resolve_feedback(
    feedback_id: UUID,
    resolution: ResolutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve a feedback/investigation."""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    # Check permissions
    if not current_user.is_admin and feedback.analyst_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only resolve your own investigations"
        )

    feedback.resolve(resolution.resolution_notes)
    db.commit()
    db.refresh(feedback)

    return feedback.to_dict()


@router.post("/{feedback_id}/reopen", response_model=FeedbackResponse)
@require_role([Role.ANALYST, Role.ADMIN])
async def reopen_feedback(
    feedback_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reopen a resolved investigation."""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    if not feedback.is_resolved():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback is not resolved"
        )

    feedback.reopen()
    db.commit()
    db.refresh(feedback)

    return feedback.to_dict()


# Investigation notes endpoints

@router.post("/{feedback_id}/notes", response_model=InvestigationNoteResponse, status_code=status.HTTP_201_CREATED)
@require_role([Role.ANALYST, Role.ADMIN])
async def add_investigation_note(
    feedback_id: UUID,
    note: InvestigationNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a note to an investigation.

    Allows collaborative investigation with multiple analysts.
    """
    # Verify feedback exists
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    # Create note
    db_note = InvestigationNote(
        feedback_id=feedback_id,
        detection_id=feedback.detection_id,
        author_id=current_user.id,
        author_email=current_user.email,
        note_text=note.note_text,
        note_type=note.note_type,
        is_internal=note.is_internal,
    )

    db.add(db_note)
    db.commit()
    db.refresh(db_note)

    return db_note.to_dict()


@router.get("/{feedback_id}/notes", response_model=List[InvestigationNoteResponse])
async def list_investigation_notes(
    feedback_id: UUID,
    include_internal: bool = Query(False, description="Include internal notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List notes for an investigation."""
    if not current_user.is_analyst and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only analysts and admins can view investigation notes"
        )

    query = db.query(InvestigationNote).filter(InvestigationNote.feedback_id == feedback_id)

    # Filter internal notes unless requested
    if not include_internal:
        query = query.filter(InvestigationNote.is_internal == False)

    notes = query.order_by(InvestigationNote.created_at).all()

    return [n.to_dict() for n in notes]


@router.get("/detection/{detection_id}/timeline")
async def get_investigation_timeline(
    detection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full investigation timeline for a detection.

    Returns all feedback and notes in chronological order.
    """
    if not current_user.is_analyst and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only analysts and admins can view investigation timeline"
        )

    # Get all feedback for this detection
    feedback_records = db.query(Feedback).filter(
        Feedback.detection_id == detection_id
    ).all()

    if not feedback_records:
        return {
            "detection_id": detection_id,
            "timeline": [],
            "summary": {
                "total_feedback": 0,
                "open_investigations": 0,
                "resolved_investigations": 0,
            }
        }

    # Build timeline
    timeline = []
    open_count = 0
    resolved_count = 0

    for feedback in feedback_records:
        # Add feedback entry
        timeline.append({
            "type": "feedback",
            "timestamp": feedback.created_at.isoformat(),
            "data": feedback.to_dict(),
        })

        if feedback.is_open():
            open_count += 1
        elif feedback.is_resolved():
            resolved_count += 1

        # Add notes
        for note in feedback.notes:
            timeline.append({
                "type": "note",
                "timestamp": note.created_at.isoformat(),
                "data": note.to_dict(),
            })

    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])

    return {
        "detection_id": detection_id,
        "timeline": timeline,
        "summary": {
            "total_feedback": len(feedback_records),
            "open_investigations": open_count,
            "resolved_investigations": resolved_count,
        }
    }
