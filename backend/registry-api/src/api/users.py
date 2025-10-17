"""
User profile and settings API endpoints

Reference: US3 (User settings), T100, T101
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..auth.rbac import get_current_user
from ..database import get_db
from ..models import NotificationPreference, User

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# Pydantic schemas
class UserProfileResponse(BaseModel):
    """User profile response schema"""
    id: str
    email: EmailStr
    role: str
    associated_endpoints: Optional[List[str]]
    created_at: datetime
    last_login_at: Optional[datetime]
    is_active: bool
    notification_preferences: Optional[List[dict]] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User profile update schema"""
    associated_endpoints: Optional[List[str]] = Field(None, description="Associated endpoint IDs")


class NotificationPreferenceCreate(BaseModel):
    """Notification preference creation schema"""
    registry_entry_id: Optional[str] = None
    enabled: bool = True
    channel: str = Field(..., description="email, slack, webhook, pagerduty")
    email_address: Optional[EmailStr] = None
    min_severity: str = Field("medium", description="low, medium, high, critical")
    notify_on_authorized: bool = False
    notify_on_suspect: bool = True
    notify_on_unauthorized: bool = True
    max_notifications_per_hour: int = Field(10, ge=1, le=100)
    digest_enabled: bool = False
    digest_frequency_minutes: Optional[int] = Field(None, ge=15, le=1440)
    quiet_hours_start: Optional[str] = Field(None, description="HH:MM format, e.g., '22:00'")
    quiet_hours_end: Optional[str] = Field(None, description="HH:MM format, e.g., '08:00'")
    quiet_hours_timezone: Optional[str] = Field(None, description="IANA timezone, e.g., 'America/New_York'")


class NotificationPreferenceUpdate(BaseModel):
    """Notification preference update schema"""
    enabled: Optional[bool] = None
    channel: Optional[str] = None
    email_address: Optional[EmailStr] = None
    min_severity: Optional[str] = None
    notify_on_authorized: Optional[bool] = None
    notify_on_suspect: Optional[bool] = None
    notify_on_unauthorized: Optional[bool] = None
    max_notifications_per_hour: Optional[int] = Field(None, ge=1, le=100)
    digest_enabled: Optional[bool] = None
    digest_frequency_minutes: Optional[int] = Field(None, ge=15, le=1440)
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    quiet_hours_timezone: Optional[str] = None


class NotificationPreferenceResponse(BaseModel):
    """Notification preference response schema"""
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
    created_at: datetime
    updated_at: datetime
    last_notification_sent_at: Optional[datetime]

    class Config:
        from_attributes = True


# API Endpoints

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user profile with notification preferences.

    Reference: US3, T100
    """
    # Get user's notification preferences
    preferences = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == current_user.id)
        .all()
    )

    # Convert preferences to dict
    preferences_data = [
        {
            "id": str(p.id),
            "channel": p.channel,
            "enabled": p.enabled,
            "min_severity": p.min_severity,
        }
        for p in preferences
    ]

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "associated_endpoints": current_user.associated_endpoints,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at,
        "is_active": current_user.is_active,
        "notification_preferences": preferences_data,
    }


@router.patch("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    update: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user profile.

    Reference: US3, T101
    """
    # Update allowed fields
    if update.associated_endpoints is not None:
        current_user.associated_endpoints = update.associated_endpoints

    db.commit()
    db.refresh(current_user)

    # Get preferences for response
    preferences = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == current_user.id)
        .all()
    )

    preferences_data = [
        {
            "id": str(p.id),
            "channel": p.channel,
            "enabled": p.enabled,
            "min_severity": p.min_severity,
        }
        for p in preferences
    ]

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "associated_endpoints": current_user.associated_endpoints,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at,
        "is_active": current_user.is_active,
        "notification_preferences": preferences_data,
    }


@router.get("/me/notifications", response_model=List[NotificationPreferenceResponse])
async def list_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all notification preferences for current user."""
    preferences = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == current_user.id)
        .all()
    )

    return preferences


@router.post("/me/notifications", response_model=NotificationPreferenceResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_preference(
    preference: NotificationPreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new notification preference for current user."""
    # Validate channel
    valid_channels = ["email", "slack", "webhook", "pagerduty"]
    if preference.channel not in valid_channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel. Must be one of: {', '.join(valid_channels)}"
        )

    # Validate severity
    valid_severities = ["low", "medium", "high", "critical"]
    if preference.min_severity not in valid_severities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity. Must be one of: {', '.join(valid_severities)}"
        )

    # Create preference
    db_preference = NotificationPreference(
        user_id=current_user.id,
        registry_entry_id=preference.registry_entry_id,
        enabled=preference.enabled,
        channel=preference.channel,
        email_address=preference.email_address or current_user.email,
        min_severity=preference.min_severity,
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

    return db_preference


@router.patch("/me/notifications/{preference_id}", response_model=NotificationPreferenceResponse)
async def update_notification_preference(
    preference_id: str,
    update: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a notification preference."""
    # Get preference
    preference = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.id == preference_id,
            NotificationPreference.user_id == current_user.id
        )
        .first()
    )

    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification preference not found"
        )

    # Update fields
    for field, value in update.dict(exclude_unset=True).items():
        setattr(preference, field, value)

    db.commit()
    db.refresh(preference)

    return preference


@router.delete("/me/notifications/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_preference(
    preference_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification preference."""
    # Get preference
    preference = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.id == preference_id,
            NotificationPreference.user_id == current_user.id
        )
        .first()
    )

    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification preference not found"
        )

    db.delete(preference)
    db.commit()
