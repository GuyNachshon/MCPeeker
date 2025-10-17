"""
Health check utilities for Registry API

Reference: Phase 8 (Production readiness), T126
"""

import logging
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import SessionLocal

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health check coordinator"""

    def __init__(self):
        self.checks = {
            "database": self.check_database,
            "clickhouse": self.check_clickhouse,
            "nats": self.check_nats,
        }

    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
        }

        all_healthy = True

        for check_name, check_func in self.checks.items():
            try:
                check_result = await check_func()
                results["checks"][check_name] = check_result

                if not check_result.get("healthy", False):
                    all_healthy = False

            except Exception as e:
                logger.error(f"Health check '{check_name}' failed: {e}")
                results["checks"][check_name] = {
                    "healthy": False,
                    "error": str(e),
                }
                all_healthy = False

        results["status"] = "healthy" if all_healthy else "unhealthy"
        return results

    async def check_database(self) -> Dict[str, Any]:
        """Check PostgreSQL database connectivity"""
        try:
            db: Session = SessionLocal()

            # Execute simple query
            result = db.execute(text("SELECT 1")).scalar()

            db.close()

            return {
                "healthy": result == 1,
                "message": "PostgreSQL connection successful",
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    async def check_clickhouse(self) -> Dict[str, Any]:
        """Check ClickHouse connectivity"""
        try:
            from .services.clickhouse_client import ClickHouseClient

            ch_client = ClickHouseClient()
            ch_client.connect()

            # Execute simple query
            result = ch_client.client.execute("SELECT 1")

            ch_client.disconnect()

            return {
                "healthy": result[0][0] == 1,
                "message": "ClickHouse connection successful",
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    async def check_nats(self) -> Dict[str, Any]:
        """Check NATS connectivity"""
        try:
            from nats.aio.client import Client as NATS

            nc = NATS()
            await nc.connect("nats://localhost:4222", connect_timeout=2)

            # Check if connected
            is_connected = nc.is_connected

            await nc.close()

            return {
                "healthy": is_connected,
                "message": "NATS connection successful",
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }


# Global instance
health_checker = HealthChecker()
