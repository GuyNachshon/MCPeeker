"""
Expiration checker cron job - sends notifications for expiring registry entries

Reference: FR-025 (Expiration notifications), US3 (Admin management), T098
"""

import logging
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RegistryEntry, RegistryStatus, User
from ..notifications.sender import NotificationSender, NotificationChannel, NotificationRequest

logger = logging.getLogger(__name__)


class ExpirationChecker:
    """Checks for expiring registry entries and sends notifications"""

    def __init__(self, db: Session, notification_sender: NotificationSender):
        self.db = db
        self.notification_sender = notification_sender
        self.warning_days = [14, 7, 3, 1]  # Days before expiration to send warnings

    def check_expirations(self) -> dict:
        """
        Check for entries expiring soon and send notifications.

        Returns a summary of notifications sent.
        """
        now = datetime.utcnow()
        summary = {
            "total_checked": 0,
            "expiring_soon": 0,
            "notifications_sent": 0,
            "errors": 0,
        }

        try:
            # Query approved entries with expiration dates
            entries = (
                self.db.query(RegistryEntry)
                .filter(
                    RegistryEntry.status == RegistryStatus.APPROVED.value,
                    RegistryEntry.expires_at.isnot(None),
                    RegistryEntry.expires_at > now,  # Not yet expired
                )
                .all()
            )

            summary["total_checked"] = len(entries)

            for entry in entries:
                days_until_expiration = (entry.expires_at - now).days

                # Check if we should send a notification for this entry
                if days_until_expiration in self.warning_days:
                    summary["expiring_soon"] += 1

                    try:
                        self._send_expiration_warning(entry, days_until_expiration)
                        summary["notifications_sent"] += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to send expiration notification for entry {entry.id}: {e}"
                        )
                        summary["errors"] += 1

            # Also check for expired entries and auto-revoke them
            expired_entries = (
                self.db.query(RegistryEntry)
                .filter(
                    RegistryEntry.status == RegistryStatus.APPROVED.value,
                    RegistryEntry.expires_at.isnot(None),
                    RegistryEntry.expires_at <= now,  # Already expired
                )
                .all()
            )

            for entry in expired_entries:
                try:
                    self._handle_expired_entry(entry)
                except Exception as e:
                    logger.error(f"Failed to handle expired entry {entry.id}: {e}")
                    summary["errors"] += 1

            logger.info(
                f"Expiration check complete: {summary['total_checked']} checked, "
                f"{summary['expiring_soon']} expiring soon, "
                f"{summary['notifications_sent']} notifications sent, "
                f"{summary['errors']} errors"
            )

        except Exception as e:
            logger.error(f"Expiration checker failed: {e}")
            summary["errors"] += 1

        return summary

    def _send_expiration_warning(self, entry: RegistryEntry, days_remaining: int) -> None:
        """Send expiration warning notification to entry owner"""

        # Get owner user to check notification preferences
        owner = self.db.query(User).filter(User.email == entry.owner_email).first()

        if not owner:
            logger.warning(f"Owner {entry.owner_email} not found for entry {entry.id}")
            return

        # Prepare notification message
        subject = f"MCP Registry Entry Expiring in {days_remaining} day(s)"
        message = f"""
Your MCP registry entry is expiring soon:

**MCP Name:** {entry.name}
**Description:** {entry.description or 'N/A'}
**Expires:** {entry.expires_at.strftime('%Y-%m-%d %H:%M UTC')}
**Days Remaining:** {days_remaining}

**Action Required:**
Please renew your MCP registration to avoid service disruption.

1. Log in to the MCPeeker dashboard
2. Navigate to My Registrations
3. Click "Renew" on the expiring entry

If you no longer need this MCP, you can let it expire or delete it manually.

**Entry Details:**
- Entry ID: {entry.id}
- Status: {entry.status}
- Created: {entry.created_at.strftime('%Y-%m-%d')}

---
This is an automated notification from MCPeeker.
        """.strip()

        # Send notification via configured channels
        notification = NotificationRequest(
            recipient_email=entry.owner_email,
            recipient_user_id=owner.id if owner else None,
            subject=subject,
            message=message,
            priority="high" if days_remaining <= 3 else "normal",
            category="expiration_warning",
            metadata={
                "entry_id": str(entry.id),
                "entry_name": entry.name,
                "days_remaining": days_remaining,
                "expires_at": entry.expires_at.isoformat(),
            },
        )

        # Send via email (primary channel)
        try:
            self.notification_sender.send_email(notification)
            logger.info(f"Sent expiration warning to {entry.owner_email} for entry {entry.id}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            raise

        # TODO: Send via other channels (Slack, webhook) based on user preferences

    def _handle_expired_entry(self, entry: RegistryEntry) -> None:
        """Handle an expired registry entry by auto-revoking it"""

        logger.info(f"Auto-revoking expired entry {entry.id} (expired: {entry.expires_at})")

        # Revoke the entry
        entry.revoke(
            revoked_by=None,  # System-initiated revocation
            revocation_reason=f"Automatically revoked: expired on {entry.expires_at.strftime('%Y-%m-%d')}"
        )

        self.db.commit()

        # Send notification about expiration
        owner = self.db.query(User).filter(User.email == entry.owner_email).first()

        subject = f"MCP Registry Entry Expired and Revoked"
        message = f"""
Your MCP registry entry has expired and been automatically revoked:

**MCP Name:** {entry.name}
**Expired On:** {entry.expires_at.strftime('%Y-%m-%d %H:%M UTC')}

This MCP will now trigger detections as "unauthorized". If you still need this MCP, please:

1. Log in to the MCPeeker dashboard
2. Create a new registration request
3. Wait for admin approval

**Entry Details:**
- Entry ID: {entry.id}
- Original Status: Approved
- New Status: Revoked
- Created: {entry.created_at.strftime('%Y-%m-%d')}

---
This is an automated notification from MCPeeker.
        """.strip()

        notification = NotificationRequest(
            recipient_email=entry.owner_email,
            recipient_user_id=owner.id if owner else None,
            subject=subject,
            message=message,
            priority="high",
            category="expiration_revoked",
            metadata={
                "entry_id": str(entry.id),
                "entry_name": entry.name,
                "expired_at": entry.expires_at.isoformat(),
            },
        )

        try:
            self.notification_sender.send_email(notification)
            logger.info(f"Sent expiration notification to {entry.owner_email} for revoked entry {entry.id}")
        except Exception as e:
            logger.error(f"Failed to send expiration notification: {e}")


def run_expiration_check():
    """Entry point for running the expiration checker as a cron job"""
    from ..database import SessionLocal
    from ..notifications.sender import NotificationSender

    db = SessionLocal()
    try:
        notification_sender = NotificationSender()
        checker = ExpirationChecker(db, notification_sender)
        summary = checker.check_expirations()

        logger.info(f"Expiration check summary: {summary}")
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    # Can be run directly: python -m src.cron.expiration_checker
    logging.basicConfig(level=logging.INFO)
    run_expiration_check()
