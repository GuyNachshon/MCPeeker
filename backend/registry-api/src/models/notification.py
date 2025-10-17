"""Notification preference model.

Reference: FR-012 (Email alerts), US1
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Integer
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import Base


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"


class NotificationSeverity(str, Enum):
    """Notification severity levels."""
    LOW = "low"           # Authorized detections
    MEDIUM = "medium"     # Suspect detections
    HIGH = "high"         # Unauthorized detections
    CRITICAL = "critical" # Security incidents


class NotificationPreference(Base):
    """User notification preferences for MCP detections.

    Allows users to configure how and when they receive alerts about
    MCP detections related to their registered servers.
    """
    __tablename__ = "notification_preferences"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Owner
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scope (optional: specific registry entry or all)
    registry_entry_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("registry_entries.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Notification settings
    enabled = Column(Boolean, nullable=False, default=True)
    channel = Column(String(20), nullable=False, default=NotificationChannel.EMAIL.value)

    # Channel-specific configuration
    email_address = Column(String(255), nullable=True)  # For email channel
    slack_webhook_url = Column(String(500), nullable=True)  # For Slack channel
    webhook_url = Column(String(500), nullable=True)  # For generic webhook
    pagerduty_integration_key = Column(String(255), nullable=True)  # For PagerDuty

    # Severity filters (which levels to notify on)
    min_severity = Column(String(20), nullable=False, default=NotificationSeverity.MEDIUM.value)

    # Classification filters
    notify_on_authorized = Column(Boolean, nullable=False, default=False)
    notify_on_suspect = Column(Boolean, nullable=False, default=True)
    notify_on_unauthorized = Column(Boolean, nullable=False, default=True)

    # Rate limiting
    max_notifications_per_hour = Column(Integer, nullable=False, default=10)
    digest_enabled = Column(Boolean, nullable=False, default=False)  # Send digest instead of individual alerts
    digest_frequency_minutes = Column(Integer, nullable=True, default=60)  # How often to send digest

    # Quiet hours (optional)
    quiet_hours_start = Column(String(5), nullable=True)  # HH:MM format, e.g., "22:00"
    quiet_hours_end = Column(String(5), nullable=True)    # HH:MM format, e.g., "08:00"
    quiet_hours_timezone = Column(String(50), nullable=True, default="UTC")

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_notification_sent_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="notification_preferences")
    # registry_entry = relationship("RegistryEntry", back_populates="notifications")

    def __repr__(self) -> str:
        scope = f"registry={self.registry_entry_id}" if self.registry_entry_id else "global"
        return f"<NotificationPreference user={self.user_id} channel={self.channel} {scope}>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "registry_entry_id": str(self.registry_entry_id) if self.registry_entry_id else None,
            "enabled": self.enabled,
            "channel": self.channel,
            "email_address": self.email_address,
            "min_severity": self.min_severity,
            "notify_on_authorized": self.notify_on_authorized,
            "notify_on_suspect": self.notify_on_suspect,
            "notify_on_unauthorized": self.notify_on_unauthorized,
            "max_notifications_per_hour": self.max_notifications_per_hour,
            "digest_enabled": self.digest_enabled,
            "digest_frequency_minutes": self.digest_frequency_minutes,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "quiet_hours_timezone": self.quiet_hours_timezone,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_notification_sent_at": self.last_notification_sent_at.isoformat() if self.last_notification_sent_at else None,
        }

    def should_notify(self, classification: str, severity: str) -> bool:
        """Check if notification should be sent based on preferences.

        Args:
            classification: Detection classification (authorized, suspect, unauthorized)
            severity: Notification severity level

        Returns:
            bool: True if notification should be sent
        """
        if not self.enabled:
            return False

        # Check severity filter
        severity_levels = {
            NotificationSeverity.LOW.value: 1,
            NotificationSeverity.MEDIUM.value: 2,
            NotificationSeverity.HIGH.value: 3,
            NotificationSeverity.CRITICAL.value: 4,
        }

        if severity_levels.get(severity, 0) < severity_levels.get(self.min_severity, 0):
            return False

        # Check classification filter
        if classification == "authorized" and not self.notify_on_authorized:
            return False
        if classification == "suspect" and not self.notify_on_suspect:
            return False
        if classification == "unauthorized" and not self.notify_on_unauthorized:
            return False

        return True

    def is_in_quiet_hours(self, current_time: Optional[datetime] = None) -> bool:
        """Check if current time is within quiet hours.

        Args:
            current_time: Current time (defaults to now)

        Returns:
            bool: True if in quiet hours
        """
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False

        if current_time is None:
            current_time = datetime.utcnow()

        # TODO: Implement timezone-aware quiet hours check
        # For now, just return False
        return False

    def can_send_notification(self, current_time: Optional[datetime] = None) -> bool:
        """Check if notification can be sent (rate limit + quiet hours).

        Args:
            current_time: Current time (defaults to now)

        Returns:
            bool: True if notification can be sent
        """
        if not self.enabled:
            return False

        # Check quiet hours
        if self.is_in_quiet_hours(current_time):
            return False

        # Check rate limit
        if self.last_notification_sent_at:
            if current_time is None:
                current_time = datetime.utcnow()

            hours_since_last = (current_time - self.last_notification_sent_at).total_seconds() / 3600
            if hours_since_last < 1:
                # TODO: Track notification count in last hour
                # For now, allow notification
                pass

        return True

    def mark_notification_sent(self) -> None:
        """Mark that a notification was sent."""
        self.last_notification_sent_at = datetime.utcnow()
