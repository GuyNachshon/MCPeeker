"""
Analytics API endpoints for dashboard metrics and visualizations

Reference: FR-012 (Dashboard), Phase 8 Polish, T107-T109
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.rbac import get_current_user
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# Pydantic schemas
class ScoreBucket(BaseModel):
    """Score distribution bucket"""
    score_min: int
    score_max: int
    count: int
    percentage: float


class ScoreDistributionResponse(BaseModel):
    """Score distribution histogram response"""
    buckets: List[ScoreBucket]
    total_detections: int
    time_range: str


class TrendlineDataPoint(BaseModel):
    """Single data point in trendline"""
    timestamp: str
    total_count: int
    authorized_count: int
    suspect_count: int
    unauthorized_count: int


class TrendlineResponse(BaseModel):
    """Trendline data response"""
    data_points: List[TrendlineDataPoint]
    granularity: str  # hour, day, week
    time_range: str


class DashboardSummary(BaseModel):
    """Dashboard summary statistics"""
    total_detections: int
    total_detections_24h: int
    active_hosts: int
    classification_breakdown: dict
    average_score: float
    high_risk_detections: int  # Score >= 9
    registry_match_rate: float  # Percentage of detections matched to registry


# API Endpoints

@router.get("/score-distribution", response_model=ScoreDistributionResponse)
async def get_score_distribution(
    start_time: Optional[str] = Query(None, description="Start time (ISO 8601)"),
    end_time: Optional[str] = Query(None, description="End time (ISO 8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get score distribution histogram for dashboard visualization.

    Returns detection counts grouped by score ranges (buckets).
    Reference: T107, FR-012
    """
    # TODO: Implement ClickHouse query for score distribution
    # For now, return mock data structure

    # Parse time range
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    else:
        start_dt = datetime.utcnow() - timedelta(days=7)

    if end_time:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    else:
        end_dt = datetime.utcnow()

    # Define score buckets (aligned with classification thresholds)
    # 0-4: Authorized
    # 5-8: Suspect
    # 9-15: Unauthorized
    buckets = [
        ScoreBucket(score_min=0, score_max=4, count=0, percentage=0.0),
        ScoreBucket(score_min=5, score_max=8, count=0, percentage=0.0),
        ScoreBucket(score_min=9, score_max=15, count=0, percentage=0.0),
        ScoreBucket(score_min=16, score_max=100, count=0, percentage=0.0),
    ]

    # Query ClickHouse for score distribution
    from ..services.clickhouse_client import ClickHouseClient

    try:
        ch_client = ClickHouseClient()
        ch_client.connect()

        buckets_data = ch_client.get_score_distribution(start_dt, end_dt)

        ch_client.disconnect()

        # Convert to response format
        buckets = [
            ScoreBucket(**bucket) for bucket in buckets_data
        ]

        total_detections = sum(b.count for b in buckets)

        return ScoreDistributionResponse(
            buckets=buckets,
            total_detections=total_detections,
            time_range=f"{start_dt.isoformat()} to {end_dt.isoformat()}"
        )

    except Exception as e:
        logger.error(f"Failed to get score distribution: {e}")
        # Return empty buckets on error
        buckets = [
            ScoreBucket(score_min=0, score_max=4, count=0, percentage=0.0),
            ScoreBucket(score_min=5, score_max=8, count=0, percentage=0.0),
            ScoreBucket(score_min=9, score_max=15, count=0, percentage=0.0),
            ScoreBucket(score_min=16, score_max=100, count=0, percentage=0.0),
        ]
        return ScoreDistributionResponse(
            buckets=buckets,
            total_detections=0,
            time_range=f"{start_dt.isoformat()} to {end_dt.isoformat()}"
        )


@router.get("/trendlines", response_model=TrendlineResponse)
async def get_trendlines(
    granularity: str = Query("hour", description="Granularity: hour, day, week"),
    start_time: Optional[str] = Query(None, description="Start time (ISO 8601)"),
    end_time: Optional[str] = Query(None, description="End time (ISO 8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detection trendlines over time with classification breakdown.

    Returns time-series data for line chart visualization.
    Reference: T108, FR-012
    """
    # Validate granularity
    if granularity not in ["hour", "day", "week"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Granularity must be 'hour', 'day', or 'week'"
        )

    # Parse time range
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    else:
        # Default time ranges based on granularity
        if granularity == "hour":
            start_dt = datetime.utcnow() - timedelta(days=1)
        elif granularity == "day":
            start_dt = datetime.utcnow() - timedelta(days=30)
        else:  # week
            start_dt = datetime.utcnow() - timedelta(days=90)

    if end_time:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    else:
        end_dt = datetime.utcnow()

    # Query ClickHouse for trendline data
    from ..services.clickhouse_client import ClickHouseClient

    try:
        ch_client = ClickHouseClient()
        ch_client.connect()

        data_points_raw = ch_client.get_trendline_data(granularity, start_dt, end_dt)

        ch_client.disconnect()

        # Convert to response format
        data_points = [
            TrendlineDataPoint(**point) for point in data_points_raw
        ]

        return TrendlineResponse(
            data_points=data_points,
            granularity=granularity,
            time_range=f"{start_dt.isoformat()} to {end_dt.isoformat()}"
        )

    except Exception as e:
        logger.error(f"Failed to get trendline data: {e}")
        # Return empty data on error
        return TrendlineResponse(
            data_points=[],
            granularity=granularity,
            time_range=f"{start_dt.isoformat()} to {end_dt.isoformat()}"
        )


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get dashboard summary statistics.

    Provides high-level metrics for the main dashboard view.
    Reference: T109, FR-012
    """
    # Query ClickHouse for real metrics (≤2s per SC-007)
    from ..services.clickhouse_client import ClickHouseClient

    try:
        ch_client = ClickHouseClient()
        ch_client.connect()

        summary_data = ch_client.get_dashboard_summary()

        ch_client.disconnect()

        return DashboardSummary(**summary_data)

    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        # Return empty summary on error
        return DashboardSummary(
            total_detections=0,
            total_detections_24h=0,
            active_hosts=0,
            classification_breakdown={"authorized": 0, "suspect": 0, "unauthorized": 0},
            average_score=0.0,
            high_risk_detections=0,
            registry_match_rate=0.0,
        )


@router.get("/health")
async def analytics_health():
    """Health check endpoint for analytics service"""
    return {
        "status": "healthy",
        "service": "analytics",
        "timestamp": datetime.utcnow().isoformat(),
    }
