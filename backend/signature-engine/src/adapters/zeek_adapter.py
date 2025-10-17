"""
Zeek to NATS adapter - converts Zeek conn.log to NATS events

Reference: US4 (Network monitoring), T067
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

from nats.aio.client import Client as NATS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ZeekAdapter:
    """Adapter to read Zeek logs and publish to NATS"""

    def __init__(
        self,
        log_file: str,
        nats_url: str,
        publish_subject: str,
        poll_interval: int = 5,
    ):
        self.log_file = Path(log_file)
        self.nats_url = nats_url
        self.publish_subject = publish_subject
        self.poll_interval = poll_interval

        self.nc: NATS = None
        self.js = None
        self.last_position = 0
        self.events_published = 0

    async def connect(self) -> None:
        """Connect to NATS"""
        self.nc = NATS()
        await self.nc.connect(self.nats_url)
        self.js = self.nc.jetstream()
        logger.info(f"Connected to NATS at {self.nats_url}")

    async def disconnect(self) -> None:
        """Disconnect from NATS"""
        if self.nc:
            await self.nc.close()
            logger.info("Disconnected from NATS")

    async def run(self) -> None:
        """Main loop - read Zeek logs and publish to NATS"""
        logger.info(f"Starting Zeek adapter, monitoring {self.log_file}")

        while True:
            try:
                # Read new lines from log file
                new_events = self._read_new_events()

                # Publish each event to NATS
                for event in new_events:
                    await self._publish_event(event)

                # Sleep before next poll
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in Zeek adapter loop: {e}")
                await asyncio.sleep(self.poll_interval)

    def _read_new_events(self) -> list[Dict[str, Any]]:
        """Read new events from Zeek log file"""
        if not self.log_file.exists():
            return []

        events = []

        try:
            with open(self.log_file, 'r') as f:
                # Seek to last position
                f.seek(self.last_position)

                # Read new lines
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Parse JSON line
                    try:
                        event = json.loads(line)

                        # Filter for MCP-relevant connections
                        if self._is_mcp_relevant(event):
                            events.append(event)

                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse Zeek log line: {line[:100]}")

                # Update position
                self.last_position = f.tell()

        except Exception as e:
            logger.error(f"Error reading Zeek log file: {e}")

        return events

    def _is_mcp_relevant(self, event: Dict[str, Any]) -> bool:
        """Check if Zeek event is relevant to MCP detection"""
        # Check if connection is on MCP port range (3000-3100)
        resp_port = event.get("id", {}).get("resp_p")
        if resp_port and 3000 <= resp_port <= 3100:
            return True

        # Check for JSON-RPC service detection
        service = event.get("service", "")
        if "json" in service.lower() or "rpc" in service.lower():
            return True

        # Check for HTTP service with MCP patterns
        if service == "http":
            # Could look at HTTP headers/URIs if available
            return True

        return False

    async def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish Zeek event to NATS"""
        try:
            # Convert Zeek event to standardized format
            nats_event = self._convert_to_nats_format(event)

            # Publish to NATS
            await self.js.publish(
                self.publish_subject,
                json.dumps(nats_event).encode('utf-8')
            )

            self.events_published += 1
            if self.events_published % 100 == 0:
                logger.info(f"Published {self.events_published} Zeek events to NATS")

        except Exception as e:
            logger.error(f"Failed to publish Zeek event: {e}")

    def _convert_to_nats_format(self, zeek_event: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Zeek event to NATS event format"""
        conn_id = zeek_event.get("id", {})

        return {
            "event_id": f"zeek-{zeek_event.get('uid', 'unknown')}",
            "timestamp": zeek_event.get("ts", time.time()),
            "source": "network.zeek",
            "detection_type": "network",
            "id": conn_id,
            "proto": zeek_event.get("proto", "tcp"),
            "service": zeek_event.get("service"),
            "duration": zeek_event.get("duration"),
            "orig_bytes": zeek_event.get("orig_bytes"),
            "resp_bytes": zeek_event.get("resp_bytes"),
            "conn_state": zeek_event.get("conn_state"),
            "uid": zeek_event.get("uid"),
            "orig_h": conn_id.get("orig_h"),
            "orig_p": conn_id.get("orig_p"),
            "resp_h": conn_id.get("resp_h"),
            "resp_p": conn_id.get("resp_p"),
        }


async def main():
    """Main entry point"""
    LOG_FILE = "/var/log/zeek/mcp/conn.json"
    NATS_URL = "nats://localhost:4222"
    PUBLISH_SUBJECT = "network.events"
    POLL_INTERVAL = 5

    adapter = ZeekAdapter(
        log_file=LOG_FILE,
        nats_url=NATS_URL,
        publish_subject=PUBLISH_SUBJECT,
        poll_interval=POLL_INTERVAL,
    )

    await adapter.connect()
    await adapter.run()


if __name__ == "__main__":
    asyncio.run(main())
