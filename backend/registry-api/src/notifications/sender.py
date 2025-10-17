"""
Notification sender service - supports multiple channels

Reference: FR-025 (Notifications), US3 (Admin management), T099
"""

import logging
import os
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Optional
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Supported notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"
    IN_APP = "in_app"


@dataclass
class NotificationRequest:
    """Notification request data"""
    recipient_email: str
    recipient_user_id: Optional[UUID]
    subject: str
    message: str
    priority: str = "normal"  # low, normal, high, critical
    category: str = "general"  # expiration_warning, detection_alert, etc.
    metadata: Optional[dict] = None


class NotificationSender:
    """Sends notifications via multiple channels"""

    def __init__(self):
        # Email configuration
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("SMTP_FROM", "noreply@mcpeeker.local")

        # Slack configuration
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")

        # Webhook configuration
        self.webhook_url = os.getenv("NOTIFICATION_WEBHOOK_URL", "")
        self.webhook_secret = os.getenv("NOTIFICATION_WEBHOOK_SECRET", "")

        # PagerDuty configuration
        self.pagerduty_api_key = os.getenv("PAGERDUTY_API_KEY", "")
        self.pagerduty_routing_key = os.getenv("PAGERDUTY_ROUTING_KEY", "")

    def send_email(self, notification: NotificationRequest) -> None:
        """Send email notification"""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.subject
            msg["From"] = self.smtp_from
            msg["To"] = notification.recipient_email

            # Plain text version
            text_part = MIMEText(notification.message, "plain")
            msg.attach(text_part)

            # HTML version (optional, convert markdown to HTML)
            html_content = self._markdown_to_html(notification.message)
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)

                server.sendmail(
                    self.smtp_from,
                    notification.recipient_email,
                    msg.as_string()
                )

            logger.info(f"Email sent to {notification.recipient_email}: {notification.subject}")

        except Exception as e:
            logger.error(f"Failed to send email to {notification.recipient_email}: {e}")
            raise

    def send_slack(self, notification: NotificationRequest) -> None:
        """Send Slack notification"""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL not configured, skipping")
            return

        try:
            # Build Slack message
            slack_message = {
                "text": notification.subject,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": notification.subject
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": notification.message
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Priority: *{notification.priority}* | Category: {notification.category}"
                            }
                        ]
                    }
                ]
            }

            # Send to Slack
            response = httpx.post(self.slack_webhook_url, json=slack_message, timeout=10.0)
            response.raise_for_status()

            logger.info(f"Slack notification sent: {notification.subject}")

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            raise

    def send_webhook(self, notification: NotificationRequest) -> None:
        """Send webhook notification (generic HTTP POST)"""
        if not self.webhook_url:
            logger.warning("Webhook URL not configured, skipping")
            return

        try:
            # Build webhook payload
            payload = {
                "recipient_email": notification.recipient_email,
                "recipient_user_id": str(notification.recipient_user_id) if notification.recipient_user_id else None,
                "subject": notification.subject,
                "message": notification.message,
                "priority": notification.priority,
                "category": notification.category,
                "metadata": notification.metadata or {},
            }

            # Add HMAC signature if secret is configured
            headers = {"Content-Type": "application/json"}
            if self.webhook_secret:
                import hmac
                import hashlib
                import json

                payload_json = json.dumps(payload, sort_keys=True)
                signature = hmac.new(
                    self.webhook_secret.encode(),
                    payload_json.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Webhook-Signature"] = signature

            # Send webhook
            response = httpx.post(self.webhook_url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()

            logger.info(f"Webhook notification sent: {notification.subject}")

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            raise

    def send_pagerduty(self, notification: NotificationRequest) -> None:
        """Send PagerDuty alert (for critical notifications only)"""
        if not self.pagerduty_routing_key:
            logger.warning("PagerDuty routing key not configured, skipping")
            return

        # Only send to PagerDuty for high/critical priority
        if notification.priority not in ["high", "critical"]:
            logger.info(f"Skipping PagerDuty for {notification.priority} priority notification")
            return

        try:
            # Build PagerDuty event
            event = {
                "routing_key": self.pagerduty_routing_key,
                "event_action": "trigger",
                "payload": {
                    "summary": notification.subject,
                    "severity": self._map_priority_to_severity(notification.priority),
                    "source": "mcpeeker",
                    "component": "registry-api",
                    "group": notification.category,
                    "custom_details": {
                        "message": notification.message,
                        "recipient_email": notification.recipient_email,
                        "metadata": notification.metadata or {},
                    }
                }
            }

            # Send to PagerDuty Events API v2
            response = httpx.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=event,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()

            logger.info(f"PagerDuty alert sent: {notification.subject}")

        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
            raise

    def send_multi_channel(
        self,
        notification: NotificationRequest,
        channels: list[NotificationChannel]
    ) -> dict:
        """Send notification to multiple channels"""
        results = {}

        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    self.send_email(notification)
                    results[channel] = "success"
                elif channel == NotificationChannel.SLACK:
                    self.send_slack(notification)
                    results[channel] = "success"
                elif channel == NotificationChannel.WEBHOOK:
                    self.send_webhook(notification)
                    results[channel] = "success"
                elif channel == NotificationChannel.PAGERDUTY:
                    self.send_pagerduty(notification)
                    results[channel] = "success"
                elif channel == NotificationChannel.IN_APP:
                    # TODO: Implement in-app notifications (store in DB, WebSocket push)
                    logger.info("In-app notifications not yet implemented")
                    results[channel] = "not_implemented"
                else:
                    results[channel] = "unknown_channel"
            except Exception as e:
                logger.error(f"Failed to send via {channel}: {e}")
                results[channel] = f"error: {str(e)}"

        return results

    def _markdown_to_html(self, markdown_text: str) -> str:
        """Convert simple markdown to HTML"""
        html = markdown_text
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        html = html.replace("\n\n", "</p><p>")
        html = f"<html><body><p>{html}</p></body></html>"
        return html

    def _map_priority_to_severity(self, priority: str) -> str:
        """Map notification priority to PagerDuty severity"""
        mapping = {
            "low": "info",
            "normal": "info",
            "high": "warning",
            "critical": "critical"
        }
        return mapping.get(priority, "info")
