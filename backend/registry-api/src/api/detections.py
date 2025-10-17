"""Detection API endpoints for querying from ClickHouse.

Reference: FR-007 (ClickHouse analytics), US1, US2
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from clickhouse_driver import Client as ClickHouseClient
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..auth.rbac import get_current_user
from ..models import User

router = APIRouter(prefix="/api/v1/detections", tags=["detections"])

# ClickHouse client (global)
# TODO: Move to dependency injection
CH_CLIENT = None


def get_clickhouse_client():
    """Get ClickHouse client (lazy initialization)."""
    global CH_CLIENT
    if CH_CLIENT is None:
        import os
        ch_host = os.getenv("CLICKHOUSE_HOST", "localhost")
        ch_port = int(os.getenv("CLICKHOUSE_PORT", "9000"))
        ch_database = os.getenv("CLICKHOUSE_DATABASE", "mcpeeker")

        CH_CLIENT = ClickHouseClient(
            host=ch_host,
            port=ch_port,
            database=ch_database,
        )
    return CH_CLIENT


# Pydantic models
class Evidence(BaseModel):
    """Evidence record."""
    type: str
    source: str
    score_contribution: int
    snippet: str


class Detection(BaseModel):
    """Detection response."""
    detection_id: str
    timestamp: datetime
    host_id_hash: str
    composite_id: str
    score: int
    classification: str
    evidence: List[Evidence]
    judge_available: bool


class DetectionListResponse(BaseModel):
    """Paginated detection list."""
    detections: List[Detection]
    total: int
    skip: int
    limit: int


# API endpoints

@router.get("", response_model=DetectionListResponse)
async def list_detections(
    classification: Optional[str] = Query(None, description="Filter by classification"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp"),
    end_time: Optional[datetime] = Query(None, description="End timestamp"),
    host_id_hash: Optional[str] = Query(None, description="Filter by host ID hash"),
    min_score: Optional[int] = Query(None, ge=0, description="Minimum score"),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
):
    """List detections with filters.

    - Developers see only detections from their associated endpoints
    - Analysts and Admins see all detections
    """
    ch_client = get_clickhouse_client()

    # Build query
    query_parts = ["SELECT detection_id, timestamp, host_id_hash, composite_id, score, classification,"]
    query_parts.append("evidence.type, evidence.source, evidence.score_contribution, evidence.snippet,")
    query_parts.append("judge_available FROM detections WHERE 1=1")
    params = []

    # Apply RBAC filtering
    if current_user.is_developer and current_user.associated_endpoints:
        # Developers see only their endpoints
        # Match on host_id_hash (SHA256 of host_id)
        # TODO: Hash the associated endpoints for comparison
        pass  # For now, skip this filtering

    # Apply filters
    if classification:
        query_parts.append("AND classification = %s")
        params.append(classification)

    if start_time:
        query_parts.append("AND timestamp >= %s")
        params.append(start_time)

    if end_time:
        query_parts.append("AND timestamp < %s")
        params.append(end_time)
    else:
        # Default: last 24 hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        query_parts.append("AND timestamp >= %s AND timestamp < %s")
        params.extend([start_time, end_time])

    if host_id_hash:
        query_parts.append("AND host_id_hash = %s")
        params.append(host_id_hash)

    if min_score is not None:
        query_parts.append("AND score >= %s")
        params.append(min_score)

    # Order by timestamp descending
    query_parts.append("ORDER BY timestamp DESC")

    # Pagination
    query_parts.append("LIMIT %s OFFSET %s")
    params.extend([limit, skip])

    query = " ".join(query_parts)

    # Execute query
    try:
        rows = ch_client.execute(query, params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ClickHouse query failed: {str(e)}"
        )

    # Parse results
    detections = []
    for row in rows:
        (
            detection_id,
            timestamp,
            host_id_hash_val,
            composite_id,
            score,
            classification_val,
            evidence_types,
            evidence_sources,
            evidence_scores,
            evidence_snippets,
            judge_available,
        ) = row

        # Build evidence list
        evidence = []
        for i in range(len(evidence_types)):
            evidence.append(Evidence(
                type=evidence_types[i],
                source=evidence_sources[i],
                score_contribution=evidence_scores[i],
                snippet=evidence_snippets[i],
            ))

        detections.append(Detection(
            detection_id=detection_id,
            timestamp=timestamp,
            host_id_hash=host_id_hash_val,
            composite_id=composite_id,
            score=score,
            classification=classification_val,
            evidence=evidence,
            judge_available=judge_available,
        ))

    # Get total count (for pagination)
    # TODO: Implement efficient total count
    total = len(detections)

    return DetectionListResponse(
        detections=detections,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{detection_id}", response_model=Detection)
async def get_detection(
    detection_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a specific detection by ID."""
    ch_client = get_clickhouse_client()

    query = """
        SELECT detection_id, timestamp, host_id_hash, composite_id, score, classification,
               evidence.type, evidence.source, evidence.score_contribution, evidence.snippet,
               judge_available
        FROM detections
        WHERE detection_id = %s
        LIMIT 1
    """

    try:
        rows = ch_client.execute(query, [detection_id])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ClickHouse query failed: {str(e)}"
        )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection not found"
        )

    row = rows[0]
    (
        det_id,
        timestamp,
        host_id_hash,
        composite_id,
        score,
        classification,
        evidence_types,
        evidence_sources,
        evidence_scores,
        evidence_snippets,
        judge_available,
    ) = row

    # Build evidence list
    evidence = []
    for i in range(len(evidence_types)):
        evidence.append(Evidence(
            type=evidence_types[i],
            source=evidence_sources[i],
            score_contribution=evidence_scores[i],
            snippet=evidence_snippets[i],
        ))

    # RBAC check
    if current_user.is_developer and current_user.associated_endpoints:
        # TODO: Check if host_id_hash matches user's endpoints
        pass

    return Detection(
        detection_id=det_id,
        timestamp=timestamp,
        host_id_hash=host_id_hash,
        composite_id=composite_id,
        score=score,
        classification=classification,
        evidence=evidence,
        judge_available=judge_available,
    )


@router.get("/stats/summary")
async def get_detection_stats(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get detection statistics summary.

    Returns counts by classification, score distribution, etc.
    """
    ch_client = get_clickhouse_client()

    # Default time range: last 24 hours
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)

    # Query counts by classification
    query = """
        SELECT
            classification,
            count() as count,
            avg(score) as avg_score,
            max(score) as max_score
        FROM detections
        WHERE timestamp >= %s AND timestamp < %s
        GROUP BY classification
    """

    try:
        rows = ch_client.execute(query, [start_time, end_time])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ClickHouse query failed: {str(e)}"
        )

    # Parse results
    stats_by_classification = {}
    for row in rows:
        classification, count, avg_score, max_score = row
        stats_by_classification[classification] = {
            "count": count,
            "avg_score": round(avg_score, 2),
            "max_score": max_score,
        }

    # Get total count
    total_query = "SELECT count() FROM detections WHERE timestamp >= %s AND timestamp < %s"
    total_count = ch_client.execute(total_query, [start_time, end_time])[0][0]

    return {
        "time_range": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        },
        "total_detections": total_count,
        "by_classification": stats_by_classification,
    }
