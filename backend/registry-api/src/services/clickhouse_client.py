"""
ClickHouse client for querying detections and analytics

Reference: US2 (Investigation), Phase 8 (Analytics), T072
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from clickhouse_driver import Client

logger = logging.getLogger(__name__)


class ClickHouseClient:
    """Client for querying ClickHouse detections database"""

    def __init__(self, host: str = "localhost", port: int = 9000, database: str = "mcpeeker"):
        self.host = host
        self.port = port
        self.database = database
        self.client: Optional[Client] = None

    def connect(self) -> None:
        """Connect to ClickHouse"""
        try:
            self.client = Client(
                host=self.host,
                port=self.port,
                database=self.database,
            )
            # Test connection
            self.client.execute("SELECT 1")
            logger.info(f"Connected to ClickHouse at {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from ClickHouse"""
        if self.client:
            self.client.disconnect()
            logger.info("Disconnected from ClickHouse")

    def query_detections(
        self,
        score_min: Optional[int] = None,
        classification: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        host_id_hash: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query detections with filters.

        Reference: US2, FR-013 (RBAC filtering)
        """
        if not self.client:
            raise RuntimeError("Not connected to ClickHouse")

        # Build WHERE clauses
        where_clauses = []
        params = {}

        if score_min is not None:
            where_clauses.append("score >= %(score_min)s")
            params["score_min"] = score_min

        if classification:
            where_clauses.append("classification = %(classification)s")
            params["classification"] = classification

        if start_time:
            where_clauses.append("timestamp >= %(start_time)s")
            params["start_time"] = start_time

        if end_time:
            where_clauses.append("timestamp <= %(end_time)s")
            params["end_time"] = end_time

        if host_id_hash:
            where_clauses.append("host_id_hash = %(host_id_hash)s")
            params["host_id_hash"] = host_id_hash

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Query
        query = f"""
        SELECT
            event_id,
            timestamp,
            host_id_hash,
            composite_id,
            score,
            classification,
            evidence,
            registry_matched,
            judge_available,
            created_at
        FROM detections
        WHERE {where_sql}
        ORDER BY timestamp DESC
        LIMIT %(limit)s
        OFFSET %(offset)s
        """

        params["limit"] = limit
        params["offset"] = offset

        try:
            rows = self.client.execute(query, params)

            detections = []
            for row in rows:
                detections.append({
                    "event_id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "host_id_hash": row[2],
                    "composite_id": row[3],
                    "score": row[4],
                    "classification": row[5],
                    "evidence": row[6],
                    "registry_matched": row[7],
                    "judge_available": row[8],
                    "created_at": row[9].isoformat() if row[9] else None,
                })

            return detections

        except Exception as e:
            logger.error(f"Failed to query detections: {e}")
            raise

    def get_detection_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get single detection by event ID"""
        if not self.client:
            raise RuntimeError("Not connected to ClickHouse")

        query = """
        SELECT
            event_id,
            timestamp,
            host_id_hash,
            composite_id,
            score,
            classification,
            evidence,
            registry_matched,
            judge_available,
            created_at
        FROM detections
        WHERE event_id = %(event_id)s
        LIMIT 1
        """

        try:
            rows = self.client.execute(query, {"event_id": event_id})

            if not rows:
                return None

            row = rows[0]
            return {
                "event_id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "host_id_hash": row[2],
                "composite_id": row[3],
                "score": row[4],
                "classification": row[5],
                "evidence": row[6],
                "registry_matched": row[7],
                "judge_available": row[8],
                "created_at": row[9].isoformat() if row[9] else None,
            }

        except Exception as e:
            logger.error(f"Failed to get detection: {e}")
            raise

    def get_score_distribution(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get score distribution for histogram.

        Reference: T107, FR-012
        """
        if not self.client:
            raise RuntimeError("Not connected to ClickHouse")

        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        if not end_time:
            end_time = datetime.utcnow()

        query = """
        SELECT
            CASE
                WHEN score <= 4 THEN 0
                WHEN score <= 8 THEN 1
                WHEN score <= 15 THEN 2
                ELSE 3
            END as bucket_idx,
            COUNT(*) as count
        FROM detections
        WHERE timestamp >= %(start_time)s AND timestamp <= %(end_time)s
        GROUP BY bucket_idx
        ORDER BY bucket_idx
        """

        try:
            rows = self.client.execute(query, {
                "start_time": start_time,
                "end_time": end_time,
            })

            # Define bucket ranges
            buckets = [
                {"score_min": 0, "score_max": 4, "count": 0},
                {"score_min": 5, "score_max": 8, "count": 0},
                {"score_min": 9, "score_max": 15, "count": 0},
                {"score_min": 16, "score_max": 100, "count": 0},
            ]

            # Fill in counts from query results
            for row in rows:
                bucket_idx, count = row
                if 0 <= bucket_idx < len(buckets):
                    buckets[bucket_idx]["count"] = count

            # Calculate percentages
            total = sum(b["count"] for b in buckets)
            for bucket in buckets:
                bucket["percentage"] = (bucket["count"] / total * 100) if total > 0 else 0.0

            return buckets

        except Exception as e:
            logger.error(f"Failed to get score distribution: {e}")
            raise

    def get_trendline_data(
        self,
        granularity: str = "hour",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get detection trendlines with classification breakdown.

        Reference: T108, FR-012
        """
        if not self.client:
            raise RuntimeError("Not connected to ClickHouse")

        # Default time ranges
        if not start_time:
            if granularity == "hour":
                start_time = datetime.utcnow() - timedelta(days=1)
            elif granularity == "day":
                start_time = datetime.utcnow() - timedelta(days=30)
            else:  # week
                start_time = datetime.utcnow() - timedelta(days=90)

        if not end_time:
            end_time = datetime.utcnow()

        # Choose time bucket function
        if granularity == "hour":
            time_bucket = "toStartOfHour(timestamp)"
        elif granularity == "day":
            time_bucket = "toStartOfDay(timestamp)"
        else:  # week
            time_bucket = "toStartOfWeek(timestamp)"

        query = f"""
        SELECT
            {time_bucket} as time_bucket,
            COUNT(*) as total_count,
            countIf(classification = 'authorized') as authorized_count,
            countIf(classification = 'suspect') as suspect_count,
            countIf(classification = 'unauthorized') as unauthorized_count
        FROM detections
        WHERE timestamp >= %(start_time)s AND timestamp <= %(end_time)s
        GROUP BY time_bucket
        ORDER BY time_bucket
        """

        try:
            rows = self.client.execute(query, {
                "start_time": start_time,
                "end_time": end_time,
            })

            data_points = []
            for row in rows:
                data_points.append({
                    "timestamp": row[0].isoformat(),
                    "total_count": row[1],
                    "authorized_count": row[2],
                    "suspect_count": row[3],
                    "unauthorized_count": row[4],
                })

            return data_points

        except Exception as e:
            logger.error(f"Failed to get trendline data: {e}")
            raise

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get dashboard summary statistics.

        Reference: T109, FR-012
        """
        if not self.client:
            raise RuntimeError("Not connected to ClickHouse")

        # Total detections
        total_query = "SELECT COUNT(*) FROM detections"
        total_detections = self.client.execute(total_query)[0][0]

        # Detections in last 24 hours
        day_ago = datetime.utcnow() - timedelta(days=1)
        day_query = "SELECT COUNT(*) FROM detections WHERE timestamp >= %(ts)s"
        total_detections_24h = self.client.execute(day_query, {"ts": day_ago})[0][0]

        # Active hosts (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        hosts_query = "SELECT COUNT(DISTINCT host_id_hash) FROM detections WHERE timestamp >= %(ts)s"
        active_hosts = self.client.execute(hosts_query, {"ts": week_ago})[0][0]

        # Classification breakdown
        class_query = """
        SELECT
            classification,
            COUNT(*) as count
        FROM detections
        GROUP BY classification
        """
        class_rows = self.client.execute(class_query)
        classification_breakdown = {
            "authorized": 0,
            "suspect": 0,
            "unauthorized": 0,
        }
        for row in class_rows:
            classification, count = row
            if classification in classification_breakdown:
                classification_breakdown[classification] = count

        # Average score (last 7 days)
        avg_query = "SELECT AVG(score) FROM detections WHERE timestamp >= %(ts)s"
        avg_result = self.client.execute(avg_query, {"ts": week_ago})[0][0]
        average_score = float(avg_result) if avg_result else 0.0

        # High risk detections (score >= 9, last 7 days)
        high_risk_query = "SELECT COUNT(*) FROM detections WHERE score >= 9 AND timestamp >= %(ts)s"
        high_risk_detections = self.client.execute(high_risk_query, {"ts": week_ago})[0][0]

        # Registry match rate (last 7 days)
        match_query = """
        SELECT
            COUNT(*) as total,
            countIf(registry_matched = true) as matched
        FROM detections
        WHERE timestamp >= %(ts)s
        """
        match_row = self.client.execute(match_query, {"ts": week_ago})[0]
        total, matched = match_row
        registry_match_rate = (matched / total * 100) if total > 0 else 0.0

        return {
            "total_detections": total_detections,
            "total_detections_24h": total_detections_24h,
            "active_hosts": active_hosts,
            "classification_breakdown": classification_breakdown,
            "average_score": round(average_score, 1),
            "high_risk_detections": high_risk_detections,
            "registry_match_rate": round(registry_match_rate, 1),
        }

    def query_detections_without_judge(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query detections that don't have Judge evidence (for retrospective scoring).

        Reference: FR-020c, retrospective scoring
        """
        if not self.client:
            raise RuntimeError("Not connected to ClickHouse")

        query = """
        SELECT
            event_id,
            timestamp,
            host_id_hash,
            composite_id,
            score,
            classification,
            evidence,
            registry_matched
        FROM detections
        WHERE judge_available = false
        ORDER BY timestamp DESC
        LIMIT %(limit)s
        """

        try:
            rows = self.client.execute(query, {"limit": limit})

            detections = []
            for row in rows:
                detections.append({
                    "event_id": row[0],
                    "timestamp": row[1],
                    "host_id_hash": row[2],
                    "composite_id": row[3],
                    "score": row[4],
                    "classification": row[5],
                    "evidence": row[6],
                    "registry_matched": row[7],
                })

            return detections

        except Exception as e:
            logger.error(f"Failed to query detections without judge: {e}")
            raise

    def update_detection(self, detection: Dict[str, Any]) -> None:
        """
        Update detection with new evidence/score.

        Note: ClickHouse doesn't support UPDATE natively, so we use ALTER TABLE UPDATE.
        """
        if not self.client:
            raise RuntimeError("Not connected to ClickHouse")

        # In production, consider using mutations or re-inserting with ReplacingMergeTree
        query = """
        ALTER TABLE detections
        UPDATE
            score = %(score)s,
            classification = %(classification)s,
            evidence = %(evidence)s,
            judge_available = %(judge_available)s
        WHERE event_id = %(event_id)s
        """

        try:
            self.client.execute(query, {
                "event_id": detection["event_id"],
                "score": detection["score"],
                "classification": detection["classification"],
                "evidence": detection["evidence"],
                "judge_available": detection.get("judge_available", False),
            })
            logger.info(f"Updated detection: {detection['event_id']}")

        except Exception as e:
            logger.error(f"Failed to update detection: {e}")
            raise
