"""
Gateway event parser - parses Judge classification events

Reference: US4 (Multi-layer correlation), T055
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GatewayParser:
    """Parser for gateway classification events from Judge service"""

    def __init__(self):
        pass

    def parse(self, raw_event: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse raw gateway classification event from Judge.

        Args:
            raw_event: Raw event bytes from NATS

        Returns:
            Parsed and validated event dict, or None if parsing fails
        """
        try:
            # Decode JSON
            event_data = json.loads(raw_event.decode('utf-8'))

            # Extract classification info
            classification = event_data.get("classification", "SUSPECT")
            confidence = event_data.get("confidence", 0.0)
            reasoning = event_data.get("reasoning", "No reasoning provided")
            score_contribution = event_data.get("score_contribution", 5)

            parsed = {
                "event_id": event_data.get("event_id", "unknown"),
                "timestamp": self._parse_timestamp(event_data.get("timestamp")),
                "host_id": event_data.get("host_id", "unknown"),
                "detection_type": "gateway",
                "source": "gateway.judge",
                "evidence": {
                    "detection_type": "gateway",
                    "classification": classification,
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "score_contribution": score_contribution,
                    "model_version": event_data.get("model_version", "unknown"),
                    "source": event_data.get("source", "gateway.judge"),
                    # Store reasoning as snippet for display (limited to 1KB)
                    "snippet": reasoning[:1024] if len(reasoning) > 1024 else reasoning,
                },
                "metadata": {
                    "parser": "gateway_parser",
                    "version": "1.0.0",
                    "detection_id": event_data.get("detection_id"),
                }
            }

            logger.debug(f"Parsed gateway event: {parsed['event_id']} - {classification}")
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing gateway event: {e}")
            return None

    def _parse_timestamp(self, timestamp) -> datetime:
        """Parse timestamp from various formats"""
        if isinstance(timestamp, (int, float)):
            return datetime.utcfromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            try:
                if timestamp.endswith('Z'):
                    timestamp = timestamp[:-1] + '+00:00'
                return datetime.fromisoformat(timestamp)
            except:
                pass

        logger.warning(f"Failed to parse timestamp: {timestamp}, using now()")
        return datetime.utcnow()

    def parse_batch(self, raw_events: list[bytes]) -> list[Dict[str, Any]]:
        """Parse multiple events in batch"""
        parsed_events = []
        for raw_event in raw_events:
            parsed = self.parse(raw_event)
            if parsed:
                parsed_events.append(parsed)
        return parsed_events
