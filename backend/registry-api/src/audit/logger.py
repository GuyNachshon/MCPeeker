"""Audit logging for registry operations.

Reference: FR-021 (Signed audit logs), FR-029 (Immutable audit log)
"""
import hashlib
import hmac
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Session

from ..models.base import Base


class AuditAction(str, Enum):
    """Audit log action types."""
    # Registry operations
    REGISTRY_CREATE = "registry.create"
    REGISTRY_UPDATE = "registry.update"
    REGISTRY_DELETE = "registry.delete"
    REGISTRY_APPROVE = "registry.approve"
    REGISTRY_REJECT = "registry.reject"
    REGISTRY_REVOKE = "registry.revoke"

    # User operations
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

    # Detection operations
    DETECTION_VIEW = "detection.view"
    DETECTION_FEEDBACK = "detection.feedback"

    # Notification operations
    NOTIFICATION_CREATE = "notification.create"
    NOTIFICATION_UPDATE = "notification.update"
    NOTIFICATION_DELETE = "notification.delete"


class AuditLog(Base):
    """Audit log entry.

    Immutable audit trail of all actions in the system.
    Each entry is signed with HMAC to ensure integrity.
    """
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sequence_number = Column(Integer, nullable=False, unique=True, index=True)

    # Who, what, when
    user_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)  # None for system actions
    user_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)  # registry_entry, user, detection, etc.
    resource_id = Column(String(255), nullable=True, index=True)

    # Details
    details = Column(JSONB, nullable=True)  # Action-specific metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)

    # Immutability
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    previous_log_id = Column(PGUUID(as_uuid=True), nullable=True)  # Chain to previous log
    signature = Column(String(64), nullable=False)  # HMAC-SHA256 signature

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.user_email} at {self.timestamp}>"


class AuditLogger:
    """Audit logger for signed, immutable audit logs."""

    def __init__(self, secret_key: str):
        """Initialize audit logger.

        Args:
            secret_key: Secret key for HMAC signing
        """
        self.secret_key = secret_key.encode('utf-8')

    def log(
        self,
        db: Session,
        action: AuditAction,
        resource_type: str,
        user_id: Optional[UUID] = None,
        user_email: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            db: Database session
            action: Action being logged
            resource_type: Type of resource (registry_entry, user, etc.)
            user_id: User performing the action
            user_email: User's email
            resource_id: ID of the affected resource
            details: Additional action metadata
            ip_address: User's IP address
            user_agent: User's user agent

        Returns:
            AuditLog: Created audit log entry
        """
        # Get previous log for chaining
        previous_log = db.query(AuditLog).order_by(AuditLog.sequence_number.desc()).first()
        previous_log_id = previous_log.id if previous_log else None
        sequence_number = (previous_log.sequence_number + 1) if previous_log else 1

        # Create log entry (without signature first)
        log_entry = AuditLog(
            sequence_number=sequence_number,
            user_id=user_id,
            user_email=user_email,
            action=action.value,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            previous_log_id=previous_log_id,
        )

        # Generate signature
        log_entry.signature = self._generate_signature(log_entry)

        # Save to database
        db.add(log_entry)
        db.flush()  # Get the ID without committing

        return log_entry

    def _generate_signature(self, log_entry: AuditLog) -> str:
        """Generate HMAC-SHA256 signature for a log entry.

        Args:
            log_entry: Audit log entry to sign

        Returns:
            str: Hex-encoded HMAC signature
        """
        # Canonical representation for signing
        canonical = {
            'sequence_number': log_entry.sequence_number,
            'user_id': str(log_entry.user_id) if log_entry.user_id else None,
            'action': log_entry.action,
            'resource_type': log_entry.resource_type,
            'resource_id': log_entry.resource_id,
            'timestamp': log_entry.timestamp.isoformat(),
            'previous_log_id': str(log_entry.previous_log_id) if log_entry.previous_log_id else None,
        }

        # Sort keys for consistent hashing
        canonical_json = json.dumps(canonical, sort_keys=True)

        # Generate HMAC
        signature = hmac.new(
            self.secret_key,
            canonical_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def verify_signature(self, log_entry: AuditLog) -> bool:
        """Verify the signature of an audit log entry.

        Args:
            log_entry: Audit log entry to verify

        Returns:
            bool: True if signature is valid
        """
        expected_signature = self._generate_signature(log_entry)
        return hmac.compare_digest(expected_signature, log_entry.signature)

    def verify_chain(self, db: Session, start_sequence: int = 1, end_sequence: Optional[int] = None) -> bool:
        """Verify the integrity of the audit log chain.

        Args:
            db: Database session
            start_sequence: Starting sequence number
            end_sequence: Ending sequence number (None = latest)

        Returns:
            bool: True if chain is valid
        """
        query = db.query(AuditLog).filter(AuditLog.sequence_number >= start_sequence)

        if end_sequence:
            query = query.filter(AuditLog.sequence_number <= end_sequence)

        logs = query.order_by(AuditLog.sequence_number).all()

        previous_id = None
        for log in logs:
            # Verify signature
            if not self.verify_signature(log):
                return False

            # Verify chain
            if log.previous_log_id != previous_id:
                return False

            previous_id = log.id

        return True


# Helper functions for common audit operations

def audit_registry_operation(
    db: Session,
    logger: AuditLogger,
    action: AuditAction,
    user_id: UUID,
    user_email: str,
    registry_entry_id: UUID,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Audit a registry operation.

    Args:
        db: Database session
        logger: Audit logger instance
        action: Action being performed
        user_id: User performing the action
        user_email: User's email
        registry_entry_id: Registry entry ID
        details: Additional action details
        ip_address: User's IP address
        user_agent: User's user agent
    """
    logger.log(
        db=db,
        action=action,
        resource_type="registry_entry",
        user_id=user_id,
        user_email=user_email,
        resource_id=str(registry_entry_id),
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def audit_detection_access(
    db: Session,
    logger: AuditLogger,
    user_id: UUID,
    user_email: str,
    detection_id: str,
    details: Optional[Dict[str, Any]] = None,
):
    """Audit detection viewing.

    Args:
        db: Database session
        logger: Audit logger instance
        user_id: User viewing the detection
        user_email: User's email
        detection_id: Detection ID
        details: Additional details
    """
    logger.log(
        db=db,
        action=AuditAction.DETECTION_VIEW,
        resource_type="detection",
        user_id=user_id,
        user_email=user_email,
        resource_id=detection_id,
        details=details,
    )
