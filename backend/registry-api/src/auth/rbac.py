"""RBAC middleware for Registry API.

Reference: FR-031-035 (Role-Based Access Control)
- Developer: View own detections + register MCPs
- Analyst: View all detections + investigate + provide feedback
- Admin: Full access including registry approval and user management
"""
from enum import Enum
from functools import wraps
from typing import Callable, List
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session


class Role(str, Enum):
    """User roles with hierarchical permissions."""
    DEVELOPER = "developer"
    ANALYST = "analyst"
    ADMIN = "admin"


# Role hierarchy: Admin > Analyst > Developer
ROLE_HIERARCHY = {
    Role.ADMIN: 3,
    Role.ANALYST: 2,
    Role.DEVELOPER: 1,
}


def require_role(allowed_roles: List[Role]) -> Callable:
    """Decorator to enforce role-based access control on endpoints.

    Args:
        allowed_roles: List of roles allowed to access the endpoint

    Returns:
        Decorator function

    Example:
        @require_role([Role.ANALYST, Role.ADMIN])
        async def get_all_detections():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            # Extract user from request state (set by JWT middleware)
            if not request or not hasattr(request.state, "user"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user = request.state.user
            user_role = Role(user.get("role"))

            # Check if user's role is in allowed roles
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {[r.value for r in allowed_roles]}"
                )

            return await func(*args, request=request, **kwargs)

        return wrapper
    return decorator


def require_min_role(min_role: Role) -> Callable:
    """Decorator to enforce minimum role requirement.

    Uses role hierarchy: Admin > Analyst > Developer

    Args:
        min_role: Minimum role required

    Example:
        @require_min_role(Role.ANALYST)  # Allows Analyst and Admin
        async def view_all_detections():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            if not request or not hasattr(request.state, "user"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user = request.state.user
            user_role = Role(user.get("role"))

            # Check role hierarchy
            if ROLE_HIERARCHY[user_role] < ROLE_HIERARCHY[min_role]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Minimum role: {min_role.value}"
                )

            return await func(*args, request=request, **kwargs)

        return wrapper
    return decorator


def check_ownership(user_id: str, resource_owner_id: str) -> bool:
    """Check if user owns a resource.

    Used for Developers to access their own detections/registry entries.

    Args:
        user_id: Current user's ID
        resource_owner_id: Owner ID of the resource

    Returns:
        bool: True if user owns the resource
    """
    return user_id == resource_owner_id


def get_user_role(request: Request) -> Role:
    """Extract user role from request.

    Args:
        request: FastAPI request object

    Returns:
        Role: User's role

    Raises:
        HTTPException: If user not authenticated
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return Role(request.state.user.get("role"))


def get_user_id(request: Request) -> str:
    """Extract user ID from request.

    Args:
        request: FastAPI request object

    Returns:
        str: User's ID (UUID)

    Raises:
        HTTPException: If user not authenticated
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return request.state.user.get("id")


# Permission checks for specific operations

def can_view_detection(user_role: Role, detection_owner_id: str, user_id: str) -> bool:
    """Check if user can view a detection.

    - Developers: Only their own detections
    - Analysts/Admins: All detections

    Args:
        user_role: User's role
        detection_owner_id: Owner of the detection
        user_id: Current user's ID

    Returns:
        bool: True if user can view detection
    """
    if user_role in [Role.ANALYST, Role.ADMIN]:
        return True
    return check_ownership(user_id, detection_owner_id)


def can_register_mcp(user_role: Role) -> bool:
    """Check if user can register an MCP.

    All roles can register MCPs (FR-032, FR-006).

    Args:
        user_role: User's role

    Returns:
        bool: True if user can register MCP
    """
    return user_role in [Role.DEVELOPER, Role.ANALYST, Role.ADMIN]


def can_approve_registry(user_role: Role) -> bool:
    """Check if user can approve/deny registry entries.

    Only Admins can approve (FR-034, US3).

    Args:
        user_role: User's role

    Returns:
        bool: True if user can approve registry entries
    """
    return user_role == Role.ADMIN


def can_submit_feedback(user_role: Role) -> bool:
    """Check if user can submit detection feedback.

    Analysts and Admins can provide feedback (FR-023, US2).

    Args:
        user_role: User's role

    Returns:
        bool: True if user can submit feedback
    """
    return user_role in [Role.ANALYST, Role.ADMIN]


# FastAPI dependencies

async def get_current_user(request: Request, db: Session = Depends(None)):
    """FastAPI dependency to get the current authenticated user.

    Extracts user from request state (set by JWT middleware) and
    loads full User object from database.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User: Current user object

    Raises:
        HTTPException: If user not authenticated or not found
    """
    # Import here to avoid circular dependency
    from ..database import get_db
    from ..models import User

    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = request.state.user
    user_id = UUID(user_data.get("id"))

    # Get database session if not provided
    if db is None:
        db_gen = get_db()
        db = next(db_gen)
        try:
            user = db.query(User).filter(User.id == user_id).first()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    else:
        user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user
