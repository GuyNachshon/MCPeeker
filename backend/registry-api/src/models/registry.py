"""Registry entry model for MCP registrations.

Reference: FR-004 (Registry requirements), FR-005 (Registry matching), US1, US3
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, String, Text, Integer
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import Base


class RegistryStatus(str, Enum):
    """Registry entry status."""
    PENDING = "pending"       # Awaiting admin approval
    APPROVED = "approved"     # Approved and active
    REJECTED = "rejected"     # Rejected by admin
    REVOKED = "revoked"       # Previously approved, now revoked


class RegistryEntry(Base):
    """Registry entry for known/authorized MCP servers.

    Represents a registered MCP server that has been approved by platform engineers.
    Used for registry matching (FR-005) to reduce false positives.
    """
    __tablename__ = "registry_entries"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # MCP identification
    composite_id = Column(String(64), nullable=True, index=True)  # SHA256 composite ID
    host_id_hash = Column(String(64), nullable=True, index=True)  # SHA256(host_id)
    port = Column(Integer, nullable=True)
    manifest_hash = Column(String(64), nullable=True)  # SHA256 of manifest file
    process_signature = Column(String(255), nullable=True)

    # Metadata
    name = Column(String(255), nullable=False)  # Friendly name (e.g., "Production API MCP")
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=True)
    owner_email = Column(String(255), nullable=False, index=True)  # Who registered it
    business_justification = Column(Text, nullable=False)  # Why it's needed

    # Tags for categorization
    tags = Column(ARRAY(String), nullable=True)  # e.g., ["production", "api", "customer-facing"]

    # Approval workflow
    status = Column(String(20), nullable=False, default=RegistryStatus.PENDING.value, index=True)
    approved_by = Column(PGUUID(as_uuid=True), nullable=True)  # Admin user ID who approved
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Auto-approval (FR-005a)
    auto_approve = Column(Boolean, nullable=False, default=False)  # Auto-approve similar detections

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration date

    # Relationships
    # notifications = relationship("NotificationPreference", back_populates="registry_entry")

    def __repr__(self) -> str:
        return f"<RegistryEntry {self.name} ({self.status})>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "composite_id": self.composite_id,
            "host_id_hash": self.host_id_hash,
            "port": self.port,
            "manifest_hash": self.manifest_hash,
            "process_signature": self.process_signature,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "owner_email": self.owner_email,
            "business_justification": self.business_justification,
            "tags": self.tags,
            "status": self.status,
            "approved_by": str(self.approved_by) if self.approved_by else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "auto_approve": self.auto_approve,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def is_approved(self) -> bool:
        """Check if entry is approved."""
        return self.status == RegistryStatus.APPROVED.value

    def is_pending(self) -> bool:
        """Check if entry is pending approval."""
        return self.status == RegistryStatus.PENDING.value

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def approve(self, admin_user_id: UUID) -> None:
        """Approve the registry entry."""
        self.status = RegistryStatus.APPROVED.value
        self.approved_by = admin_user_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = None

    def reject(self, admin_user_id: UUID, reason: str) -> None:
        """Reject the registry entry."""
        self.status = RegistryStatus.REJECTED.value
        self.approved_by = admin_user_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason

    def revoke(self, admin_user_id: UUID, reason: str) -> None:
        """Revoke a previously approved entry."""
        self.status = RegistryStatus.REVOKED.value
        self.approved_by = admin_user_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason

    def matches_detection(
        self,
        composite_id: Optional[str] = None,
        host_id_hash: Optional[str] = None,
        port: Optional[int] = None,
        manifest_hash: Optional[str] = None,
    ) -> bool:
        """Check if this registry entry matches a detection.

        Implements FR-005 registry matching logic.
        Priority: composite_id > (host_id + port + manifest) > manifest only

        Args:
            composite_id: Composite identifier from detection
            host_id_hash: Hashed host ID from detection
            port: Port from detection
            manifest_hash: Manifest hash from detection

        Returns:
            bool: True if detection matches this registry entry
        """
        # Must be approved to match
        if not self.is_approved():
            return False

        # Check if expired
        if self.is_expired():
            return False

        # Highest priority: composite_id exact match
        if composite_id and self.composite_id:
            return composite_id == self.composite_id

        # Medium priority: host + port + manifest match
        if host_id_hash and self.host_id_hash and port and self.port and manifest_hash and self.manifest_hash:
            return (
                host_id_hash == self.host_id_hash
                and port == self.port
                and manifest_hash == self.manifest_hash
            )

        # Low priority: manifest hash only (less specific)
        if manifest_hash and self.manifest_hash:
            return manifest_hash == self.manifest_hash

        return False
