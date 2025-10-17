"""
Endpoint event parser - parses endpoint detection events

Reference: US4 (Multi-layer correlation), T053
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


# Event schemas
class EndpointDetectionEvent(BaseModel):
    """Schema for endpoint.detection events"""
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    host_id: str = Field(..., description="Host identifier (will be hashed)")
    detection_type: str = Field(..., description="file or process")
    evidence: Dict[str, Any] = Field(..., description="Detection evidence")

    class Config:
        extra = "allow"


class EndpointParser:
    """Parser for endpoint detection events from scanner"""

    def __init__(self, validate_schema: bool = True):
        self.validate_schema = validate_schema

    def parse(self, raw_event: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse raw endpoint detection event.

        Args:
            raw_event: Raw event bytes from NATS

        Returns:
            Parsed and validated event dict, or None if parsing fails
        """
        try:
            # Decode JSON
            event_data = json.loads(raw_event.decode('utf-8'))

            # Validate schema if enabled
            if self.validate_schema:
                event = EndpointDetectionEvent(**event_data)
                event_data = event.dict()

            # Extract and normalize fields
            parsed = {
                "event_id": event_data["event_id"],
                "timestamp": self._parse_timestamp(event_data["timestamp"]),
                "host_id": event_data["host_id"],
                "detection_type": event_data["detection_type"],
                "source": "endpoint",
                "evidence": self._extract_evidence(event_data),
                "metadata": {
                    "parser": "endpoint_parser",
                    "version": "1.0.0",
                }
            }

            logger.debug(f"Parsed endpoint event: {parsed['event_id']}")
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            return None
        except ValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing endpoint event: {e}")
            return None

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO 8601 timestamp"""
        try:
            # Handle both with and without timezone
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}, using now()")
            return datetime.utcnow()

    def _extract_evidence(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize evidence from event"""
        evidence = event_data.get("evidence", {})

        # Normalize evidence structure
        normalized = {
            "detection_type": event_data.get("detection_type"),
        }

        # File detection evidence
        if "file_path" in evidence:
            normalized["file_path"] = evidence["file_path"]
        if "file_hash" in evidence:
            normalized["file_hash"] = evidence["file_hash"]
        if "manifest_hash" in evidence:
            normalized["manifest_hash"] = evidence["manifest_hash"]

        # Process detection evidence
        if "process_name" in evidence:
            normalized["process_name"] = evidence["process_name"]
        if "process_hash" in evidence:
            normalized["process_hash"] = evidence["process_hash"]
        if "command_line" in evidence:
            normalized["command_line"] = evidence["command_line"]

        # Port information
        if "port" in evidence:
            normalized["port"] = int(evidence["port"])

        # Snippet (limited to 1KB per FR-009)
        if "snippet" in evidence:
            snippet = evidence["snippet"]
            if len(snippet) > 1024:
                snippet = snippet[:1024]
            normalized["snippet"] = snippet

        # Source information
        if "source" in evidence:
            normalized["source"] = evidence["source"]

        # Score contribution (default for endpoint)
        normalized["score_contribution"] = 11  # Endpoint weight per FR-003

        return normalized

    def parse_batch(self, raw_events: list[bytes]) -> list[Dict[str, Any]]:
        """Parse multiple events in batch"""
        parsed_events = []
        for raw_event in raw_events:
            parsed = self.parse(raw_event)
            if parsed:
                parsed_events.append(parsed)
        return parsed_events
