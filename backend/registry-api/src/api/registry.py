"""Registry API endpoints.

Reference: FR-004 (Registry requirements), FR-005 (Registry matching), US1, US3
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..auth.rbac import Role, get_current_user, require_role
from ..database import get_db
from ..models import RegistryEntry, RegistryStatus, User

router = APIRouter(prefix="/api/v1/registry", tags=["registry"])


# Pydantic schemas
class RegistryEntryCreate(BaseModel):
    """Schema for creating a registry entry."""
    composite_id: Optional[str] = Field(None, max_length=64, description="SHA256 composite ID")
    host_id_hash: Optional[str] = Field(None, max_length=64, description="SHA256 hashed host ID")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Port number")
    manifest_hash: Optional[str] = Field(None, max_length=64, description="SHA256 manifest hash")
    process_signature: Optional[str] = Field(None, max_length=255, description="Process signature")
    name: str = Field(..., max_length=255, description="Friendly name")
    description: Optional[str] = Field(None, description="Description")
    version: Optional[str] = Field(None, max_length=50, description="MCP version")
    business_justification: str = Field(..., description="Business justification for registration")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    auto_approve: bool = Field(False, description="Auto-approve similar detections")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")


class RegistryEntryUpdate(BaseModel):
    """Schema for updating a registry entry."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = Field(None, max_length=50)
    business_justification: Optional[str] = None
    tags: Optional[List[str]] = None
    auto_approve: Optional[bool] = None
    expires_at: Optional[datetime] = None


class RegistryEntryResponse(BaseModel):
    """Schema for registry entry response."""
    id: str
    composite_id: Optional[str]
    host_id_hash: Optional[str]
    port: Optional[int]
    manifest_hash: Optional[str]
    process_signature: Optional[str]
    name: str
    description: Optional[str]
    version: Optional[str]
    owner_email: str
    business_justification: str
    tags: Optional[List[str]]
    status: str
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    auto_approve: bool
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    """Schema for approval/rejection request."""
    reason: Optional[str] = Field(None, description="Reason for rejection or revocation")


# API endpoints

@router.post("/entries", response_model=RegistryEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_registry_entry(
    entry: RegistryEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new registry entry (Developer, Analyst, Admin).

    Developers can register their own MCPs.
    Analysts and Admins can register on behalf of others.
    """
    # Create entry
    db_entry = RegistryEntry(
        composite_id=entry.composite_id,
        host_id_hash=entry.host_id_hash,
        port=entry.port,
        manifest_hash=entry.manifest_hash,
        process_signature=entry.process_signature,
        name=entry.name,
        description=entry.description,
        version=entry.version,
        owner_email=current_user.email,
        business_justification=entry.business_justification,
        tags=entry.tags,
        auto_approve=entry.auto_approve,
        expires_at=entry.expires_at,
        status=RegistryStatus.PENDING.value,
    )

    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    return db_entry


@router.get("/entries", response_model=List[RegistryEntryResponse])
async def list_registry_entries(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    owner_email: Optional[str] = Query(None, description="Filter by owner email"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List registry entries.

    - Developers see only their own entries
    - Analysts and Admins see all entries
    """
    query = db.query(RegistryEntry)

    # Apply RBAC filtering
    if current_user.is_developer:
        query = query.filter(RegistryEntry.owner_email == current_user.email)

    # Apply filters
    if status_filter:
        query = query.filter(RegistryEntry.status == status_filter)

    if owner_email:
        # Only Analysts/Admins can filter by other users' emails
        if current_user.is_developer and owner_email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Developers can only view their own entries"
            )
        query = query.filter(RegistryEntry.owner_email == owner_email)

    if tag:
        query = query.filter(RegistryEntry.tags.contains([tag]))

    # Pagination
    entries = query.offset(skip).limit(limit).all()

    return entries


@router.get("/entries/{entry_id}", response_model=RegistryEntryResponse)
async def get_registry_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific registry entry."""
    entry = db.query(RegistryEntry).filter(RegistryEntry.id == entry_id).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registry entry not found"
        )

    # RBAC check
    if current_user.is_developer and entry.owner_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developers can only view their own entries"
        )

    return entry


@router.patch("/entries/{entry_id}", response_model=RegistryEntryResponse)
async def update_registry_entry(
    entry_id: UUID,
    update: RegistryEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a registry entry.

    Owners can update their pending entries.
    Admins can update any entry.
    """
    entry = db.query(RegistryEntry).filter(RegistryEntry.id == entry_id).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registry entry not found"
        )

    # RBAC check
    if not current_user.is_admin and entry.owner_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own entries"
        )

    # Developers can only update pending entries
    if current_user.is_developer and entry.status != RegistryStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update pending entries"
        )

    # Apply updates
    for field, value in update.dict(exclude_unset=True).items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)

    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_registry_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a registry entry.

    Owners can delete their pending entries.
    Admins can delete any entry.
    """
    entry = db.query(RegistryEntry).filter(RegistryEntry.id == entry_id).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registry entry not found"
        )

    # RBAC check
    if not current_user.is_admin and entry.owner_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own entries"
        )

    # Developers can only delete pending entries
    if current_user.is_developer and entry.status != RegistryStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete pending entries"
        )

    db.delete(entry)
    db.commit()


@router.post("/entries/{entry_id}/approve", response_model=RegistryEntryResponse)
@require_role([Role.ADMIN])
async def approve_registry_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a registry entry (Admin only).

    Reference: US3 - Admin approval workflow
    """
    entry = db.query(RegistryEntry).filter(RegistryEntry.id == entry_id).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registry entry not found"
        )

    if entry.status != RegistryStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve entry with status: {entry.status}"
        )

    entry.approve(current_user.id)
    db.commit()
    db.refresh(entry)

    return entry


@router.post("/entries/{entry_id}/reject", response_model=RegistryEntryResponse)
@require_role([Role.ADMIN])
async def reject_registry_entry(
    entry_id: UUID,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a registry entry (Admin only).

    Reference: US3 - Admin approval workflow
    """
    entry = db.query(RegistryEntry).filter(RegistryEntry.id == entry_id).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registry entry not found"
        )

    if entry.status != RegistryStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject entry with status: {entry.status}"
        )

    if not request.reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required"
        )

    entry.reject(current_user.id, request.reason)
    db.commit()
    db.refresh(entry)

    return entry


@router.post("/entries/{entry_id}/revoke", response_model=RegistryEntryResponse)
@require_role([Role.ADMIN])
async def revoke_registry_entry(
    entry_id: UUID,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke an approved registry entry (Admin only).

    Reference: US3 - Admin revocation
    """
    entry = db.query(RegistryEntry).filter(RegistryEntry.id == entry_id).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registry entry not found"
        )

    if entry.status != RegistryStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only revoke approved entries"
        )

    if not request.reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Revocation reason is required"
        )

    entry.revoke(current_user.id, request.reason)
    db.commit()
    db.refresh(entry)

    return entry


@router.get("/match")
async def match_detection(
    composite_id: Optional[str] = Query(None),
    host_id_hash: Optional[str] = Query(None),
    port: Optional[int] = Query(None),
    manifest_hash: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if a detection matches any approved registry entry.

    Reference: FR-005 (Registry matching logic)
    Used by correlator service for registry lookups.
    """
    if not any([composite_id, host_id_hash, port, manifest_hash]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one identifier must be provided"
        )

    # Query approved, non-expired entries
    query = db.query(RegistryEntry).filter(
        RegistryEntry.status == RegistryStatus.APPROVED.value
    )

    # Filter out expired entries
    query = query.filter(
        or_(
            RegistryEntry.expires_at.is_(None),
            RegistryEntry.expires_at > datetime.utcnow()
        )
    )

    # Match logic (priority: composite_id > host+port+manifest > manifest only)
    if composite_id:
        query = query.filter(RegistryEntry.composite_id == composite_id)
    elif host_id_hash and port and manifest_hash:
        query = query.filter(
            and_(
                RegistryEntry.host_id_hash == host_id_hash,
                RegistryEntry.port == port,
                RegistryEntry.manifest_hash == manifest_hash
            )
        )
    elif manifest_hash:
        query = query.filter(RegistryEntry.manifest_hash == manifest_hash)

    entry = query.first()

    if entry:
        return {
            "matched": True,
            "entry": entry.to_dict(),
            "penalty": -6,  # FR-005 registry penalty
        }

    return {
        "matched": False,
        "entry": None,
        "penalty": 0,
    }
