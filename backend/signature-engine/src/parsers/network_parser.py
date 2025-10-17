"""
Network event parser - parses Zeek and Suricata events

Reference: US4 (Multi-layer correlation), T054
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class NetworkParser:
    """Parser for network detection events from Zeek/Suricata"""

    def __init__(self):
        pass

    def parse(self, raw_event: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse raw network detection event.

        Supports both Zeek conn.log format and Suricata alert format.

        Args:
            raw_event: Raw event bytes from NATS

        Returns:
            Parsed and validated event dict, or None if parsing fails
        """
        try:
            # Decode JSON
            event_data = json.loads(raw_event.decode('utf-8'))

            # Determine event source (Zeek or Suricata)
            event_source = self._detect_source(event_data)

            if event_source == "zeek":
                return self._parse_zeek(event_data)
            elif event_source == "suricata":
                return self._parse_suricata(event_data)
            else:
                logger.warning(f"Unknown network event source: {event_data}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing network event: {e}")
            return None

    def _detect_source(self, event_data: Dict[str, Any]) -> str:
        """Detect if event is from Zeek or Suricata"""
        # Zeek events have 'id' and 'conn' fields
        if "id" in event_data and ("orig_h" in event_data.get("id", {}) or "conn_state" in event_data):
            return "zeek"

        # Suricata events have 'event_type' and 'alert' fields
        if "event_type" in event_data or "alert" in event_data:
            return "suricata"

        return "unknown"

    def _parse_zeek(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Zeek conn.log event"""
        # Extract connection 5-tuple
        conn_id = event_data.get("id", {})

        parsed = {
            "event_id": f"zeek-{event_data.get('uid', 'unknown')}",
            "timestamp": self._parse_timestamp(event_data.get("ts")),
            "host_id": conn_id.get("orig_h", "unknown"),  # Source IP
            "detection_type": "network",
            "source": "network.zeek",
            "evidence": {
                "detection_type": "network",
                "source_ip": conn_id.get("orig_h"),
                "source_port": conn_id.get("orig_p"),
                "dest_ip": conn_id.get("resp_h"),
                "dest_port": conn_id.get("resp_p"),
                "protocol": event_data.get("proto", "tcp"),
                "service": event_data.get("service"),
                "conn_state": event_data.get("conn_state"),
                "duration": event_data.get("duration"),
                "orig_bytes": event_data.get("orig_bytes"),
                "resp_bytes": event_data.get("resp_bytes"),
                "port": conn_id.get("resp_p"),  # MCP server port
                "score_contribution": 3,  # Network weight per FR-003
                "source": "zeek",
            },
            "metadata": {
                "parser": "network_parser",
                "version": "1.0.0",
                "zeek_uid": event_data.get("uid"),
            }
        }

        return parsed

    def _parse_suricata(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Suricata alert event"""
        alert = event_data.get("alert", {})
        src_ip = event_data.get("src_ip", "unknown")
        dest_port = event_data.get("dest_port")

        parsed = {
            "event_id": f"suricata-{event_data.get('flow_id', 'unknown')}",
            "timestamp": self._parse_timestamp(event_data.get("timestamp")),
            "host_id": src_ip,  # Source IP
            "detection_type": "network",
            "source": "network.suricata",
            "evidence": {
                "detection_type": "network",
                "source_ip": src_ip,
                "source_port": event_data.get("src_port"),
                "dest_ip": event_data.get("dest_ip"),
                "dest_port": dest_port,
                "protocol": event_data.get("proto", "TCP"),
                "alert_signature": alert.get("signature"),
                "alert_category": alert.get("category"),
                "alert_severity": alert.get("severity"),
                "port": dest_port,  # MCP server port
                "score_contribution": 3,  # Network weight per FR-003
                "source": "suricata",
            },
            "metadata": {
                "parser": "network_parser",
                "version": "1.0.0",
                "flow_id": event_data.get("flow_id"),
                "signature_id": alert.get("signature_id"),
            }
        }

        return parsed

    def _parse_timestamp(self, timestamp) -> datetime:
        """Parse timestamp from various formats"""
        if isinstance(timestamp, (int, float)):
            # Unix timestamp
            return datetime.utcfromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            # ISO 8601 or other string format
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
