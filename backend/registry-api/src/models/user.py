"""User model for Registry API.

Reference: specs/001-mcp-detection-platform/data-model.md (PostgreSQL users table)
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    """User model with RBAC roles (FR-031).

    Attributes:
        id: User UUID (primary key)
        email: User email address (unique)
        hashed_password: Bcrypt hashed password
        role: User role (developer, analyst, admin)
        associated_endpoints: List of host identifiers for Developer role scoping
        created_at: Account creation timestamp
        last_login_at: Last login timestamp
        is_active: Account active status
    """

    __tablename__ = "users"

    # Primary key
    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Authentication
    email: str = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password: str = Column(String(255), nullable=False)

    # RBAC (FR-032, FR-033, FR-034)
    role: str = Column(String(50), nullable=False, index=True)

    # Developer role scoping (FR-032)
    # Developers see only detections from their associated endpoints
    associated_endpoints: Optional[List[str]] = Column(ARRAY(Text), nullable=True)

    # Metadata
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_login_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    is_active: bool = Column(Boolean, nullable=False, default=True)

    # Relationships
    notification_preferences = relationship("NotificationPreference", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation."""
        return f"<User {self.email} ({self.role})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            dict: User data (without hashed_password)
        """
        return {
            "id": str(self.id),
            "email": self.email,
            "role": self.role,
            "associated_endpoints": self.associated_endpoints,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "is_active": self.is_active,
        }

    @property
    def is_developer(self) -> bool:
        """Check if user has Developer role."""
        return self.role == "developer"

    @property
    def is_analyst(self) -> bool:
        """Check if user has Analyst role."""
        return self.role == "analyst"

    @property
    def is_admin(self) -> bool:
        """Check if user has Admin role."""
        return self.role == "admin"

    def can_view_endpoint(self, endpoint: str) -> bool:
        """Check if user can view detections from a specific endpoint.

        - Developers: Only endpoints in their associated_endpoints list
        - Analysts/Admins: All endpoints

        Args:
            endpoint: Host identifier

        Returns:
            bool: True if user can view endpoint detections
        """
        if self.is_analyst or self.is_admin:
            return True

        if self.is_developer and self.associated_endpoints:
            return endpoint in self.associated_endpoints

        return False
