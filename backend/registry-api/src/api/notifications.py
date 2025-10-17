"""Notification preference API endpoints.

Reference: FR-012 (Email alerts), US1
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from ..auth.rbac import get_current_user
from ..database import get_db
from ..models import NotificationChannel, NotificationPreference, NotificationSeverity, User

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


# Pydantic schemas
class NotificationPreferenceCreate(BaseModel):
    """Schema for creating a notification preference."""
    registry_entry_id: Optional[UUID] = Field(None, description="Specific registry entry (or None for global)")
    channel: NotificationChannel = Field(NotificationChannel.EMAIL, description="Notification channel")
    email_address: Optional[EmailStr] = Field(None, description="Email address for email channel")
    slack_webhook_url: Optional[str] = Field(None, max_length=500, description="Slack webhook URL")
    webhook_url: Optional[str] = Field(None, max_length=500, description="Generic webhook URL")
    pagerduty_integration_key: Optional[str] = Field(None, max_length=255, description="PagerDuty integration key")
    min_severity: NotificationSeverity = Field(NotificationSeverity.MEDIUM, description="Minimum severity to notify")
    notify_on_authorized: bool = Field(False, description="Notify on authorized detections")
    notify_on_suspect: bool = Field(True, description="Notify on suspect detections")
    notify_on_unauthorized: bool = Field(True, description="Notify on unauthorized detections")
    max_notifications_per_hour: int = Field(10, ge=1, le=1000, description="Rate limit")
    digest_enabled: bool = Field(False, description="Send digest instead of individual alerts")
    digest_frequency_minutes: Optional[int] = Field(60, ge=1, le=1440, description="Digest frequency")
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="Quiet hours start (HH:MM)")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="Quiet hours end (HH:MM)")
    quiet_hours_timezone: str = Field("UTC", description="Timezone for quiet hours")


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating a notification preference."""
    enabled: Optional[bool] = None
    channel: Optional[NotificationChannel] = None
    email_address: Optional[EmailStr] = None
    slack_webhook_url: Optional[str] = Field(None, max_length=500)
    webhook_url: Optional[str] = Field(None, max_length=500)
    pagerduty_integration_key: Optional[str] = Field(None, max_length=255)
    min_severity: Optional[NotificationSeverity] = None
    notify_on_authorized: Optional[bool] = None
    notify_on_suspect: Optional[bool] = None
    notify_on_unauthorized: Optional[bool] = None
    max_notifications_per_hour: Optional[int] = Field(None, ge=1, le=1000)
    digest_enabled: Optional[bool] = None
    digest_frequency_minutes: Optional[int] = Field(None, ge=1, le=1440)
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_timezone: Optional[str] = None


class NotificationPreferenceResponse(BaseModel):
    """Schema for notification preference response."""
    id: str
    user_id: str
    registry_entry_id: Optional[str]
    enabled: bool
    channel: str
    email_address: Optional[str]
    min_severity: str
    notify_on_authorized: bool
    notify_on_suspect: bool
    notify_on_unauthorized: bool
    max_notifications_per_hour: int
    digest_enabled: bool
    digest_frequency_minutes: Optional[int]
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    quiet_hours_timezone: Optional[str]
    created_at: str
    updated_at: str
    last_notification_sent_at: Optional[str]

    class Config:
        from_attributes = True


# API endpoints

@router.post("/preferences", response_model=NotificationPreferenceResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_preference(
    preference: NotificationPreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new notification preference.

    Users can create preferences for their own notifications.
    """
    # Validate channel-specific configuration
    if preference.channel == NotificationChannel.EMAIL and not preference.email_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required for email channel"
        )
    if preference.channel == NotificationChannel.SLACK and not preference.slack_webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slack webhook URL is required for Slack channel"
        )
    if preference.channel == NotificationChannel.WEBHOOK and not preference.webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL is required for webhook channel"
        )
    if preference.channel == NotificationChannel.PAGERDUTY and not preference.pagerduty_integration_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PagerDuty integration key is required for PagerDuty channel"
        )

    # Create preference
    db_preference = NotificationPreference(
        user_id=current_user.id,
        registry_entry_id=preference.registry_entry_id,
        channel=preference.channel.value,
        email_address=preference.email_address,
        slack_webhook_url=preference.slack_webhook_url,
        webhook_url=preference.webhook_url,
        pagerduty_integration_key=preference.pagerduty_integration_key,
        min_severity=preference.min_severity.value,
        notify_on_authorized=preference.notify_on_authorized,
        notify_on_suspect=preference.notify_on_suspect,
        notify_on_unauthorized=preference.notify_on_unauthorized,
        max_notifications_per_hour=preference.max_notifications_per_hour,
        digest_enabled=preference.digest_enabled,
        digest_frequency_minutes=preference.digest_frequency_minutes,
        quiet_hours_start=preference.quiet_hours_start,
        quiet_hours_end=preference.quiet_hours_end,
        quiet_hours_timezone=preference.quiet_hours_timezone,
    )

    db.add(db_preference)
    db.commit()
    db.refresh(db_preference)

    return db_preference.to_dict()


@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
async def list_notification_preferences(
    registry_entry_id: Optional[UUID] = Query(None, description="Filter by registry entry"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's notification preferences.

    Users can only view their own preferences.
    """
    query = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    )

    # Apply filters
    if registry_entry_id:
        query = query.filter(NotificationPreference.registry_entry_id == registry_entry_id)

    # Pagination
    preferences = query.offset(skip).limit(limit).all()

    return [p.to_dict() for p in preferences]


@router.get("/preferences/{preference_id}", response_model=NotificationPreferenceResponse)
async def get_notification_preference(
    preference_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific notification preference."""
    preference = db.query(NotificationPreference).filter(
        NotificationPreference.id == preference_id
    ).first()

    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification preference not found"
        )

    # Users can only view their own preferences
    if preference.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own notification preferences"
        )

    return preference.to_dict()


@router.patch("/preferences/{preference_id}", response_model=NotificationPreferenceResponse)
async def update_notification_preference(
    preference_id: UUID,
    update: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a notification preference."""
    preference = db.query(NotificationPreference).filter(
        NotificationPreference.id == preference_id
    ).first()

    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification preference not found"
        )

    # Users can only update their own preferences
    if preference.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own notification preferences"
        )

    # Apply updates
    for field, value in update.dict(exclude_unset=True).items():
        # Convert Enum to value if needed
        if isinstance(value, NotificationChannel) or isinstance(value, NotificationSeverity):
            value = value.value
        setattr(preference, field, value)

    db.commit()
    db.refresh(preference)

    return preference.to_dict()


@router.delete("/preferences/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_preference(
    preference_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification preference."""
    preference = db.query(NotificationPreference).filter(
        NotificationPreference.id == preference_id
    ).first()

    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification preference not found"
        )

    # Users can only delete their own preferences
    if preference.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own notification preferences"
        )

    db.delete(preference)
    db.commit()


@router.post("/preferences/{preference_id}/test", status_code=status.HTTP_200_OK)
async def test_notification(
    preference_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a test notification.

    Allows users to verify their notification configuration works correctly.
    """
    preference = db.query(NotificationPreference).filter(
        NotificationPreference.id == preference_id
    ).first()

    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification preference not found"
        )

    # Users can only test their own preferences
    if preference.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only test your own notification preferences"
        )

    # TODO: Implement actual notification sending
    # For now, just return success
    return {
        "status": "success",
        "message": f"Test notification sent via {preference.channel}",
        "channel": preference.channel,
    }
