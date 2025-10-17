"""
Suricata to NATS adapter - converts Suricata eve.json alerts to NATS events

Reference: US4 (Network monitoring), T068
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any

from nats.aio.client import Client as NATS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SuricataAdapter:
    """Adapter to read Suricata EVE logs and publish to NATS"""

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
        """Main loop - read Suricata logs and publish to NATS"""
        logger.info(f"Starting Suricata adapter, monitoring {self.log_file}")

        while True:
            try:
                # Read new events from EVE log
                new_events = self._read_new_events()

                # Publish each event to NATS
                for event in new_events:
                    await self._publish_event(event)

                # Sleep before next poll
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in Suricata adapter loop: {e}")
                await asyncio.sleep(self.poll_interval)

    def _read_new_events(self) -> list[Dict[str, Any]]:
        """Read new events from Suricata EVE log file"""
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
                    if not line:
                        continue

                    # Parse JSON line
                    try:
                        event = json.loads(line)

                        # Filter for MCP-relevant alerts
                        if self._is_mcp_relevant(event):
                            events.append(event)

                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse Suricata log line: {line[:100]}")

                # Update position
                self.last_position = f.tell()

        except Exception as e:
            logger.error(f"Error reading Suricata log file: {e}")

        return events

    def _is_mcp_relevant(self, event: Dict[str, Any]) -> bool:
        """Check if Suricata event is relevant to MCP detection"""
        # Only process alert events
        if event.get("event_type") != "alert":
            return False

        # Check if alert is in MCP signature range (1000001-1000999)
        alert = event.get("alert", {})
        signature_id = alert.get("signature_id", 0)
        if 1000001 <= signature_id <= 1000999:
            return True

        # Check for MCP-related signature names
        signature = alert.get("signature", "").lower()
        if "mcp" in signature or "json-rpc" in signature:
            return True

        # Check destination port range
        dest_port = event.get("dest_port")
        if dest_port and 3000 <= dest_port <= 3100:
            return True

        return False

    async def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish Suricata event to NATS"""
        try:
            # Convert Suricata event to standardized format
            nats_event = self._convert_to_nats_format(event)

            # Publish to NATS
            await self.js.publish(
                self.publish_subject,
                json.dumps(nats_event).encode('utf-8')
            )

            self.events_published += 1
            if self.events_published % 100 == 0:
                logger.info(f"Published {self.events_published} Suricata events to NATS")

        except Exception as e:
            logger.error(f"Failed to publish Suricata event: {e}")

    def _convert_to_nats_format(self, suricata_event: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Suricata event to NATS event format"""
        alert = suricata_event.get("alert", {})
        flow = suricata_event.get("flow", {})

        return {
            "event_id": f"suricata-{suricata_event.get('flow_id', 'unknown')}",
            "timestamp": suricata_event.get("timestamp", time.time()),
            "source": "network.suricata",
            "detection_type": "network",
            "src_ip": suricata_event.get("src_ip"),
            "src_port": suricata_event.get("src_port"),
            "dest_ip": suricata_event.get("dest_ip"),
            "dest_port": suricata_event.get("dest_port"),
            "proto": suricata_event.get("proto", "TCP"),
            "alert": {
                "signature": alert.get("signature"),
                "signature_id": alert.get("signature_id"),
                "category": alert.get("category"),
                "severity": alert.get("severity"),
                "action": alert.get("action"),
            },
            "flow": {
                "pkts_toserver": flow.get("pkts_toserver"),
                "pkts_toclient": flow.get("pkts_toclient"),
                "bytes_toserver": flow.get("bytes_toserver"),
                "bytes_toclient": flow.get("bytes_toclient"),
                "start": flow.get("start"),
            },
            "flow_id": suricata_event.get("flow_id"),
            "metadata": suricata_event.get("metadata", {}),
        }


async def main():
    """Main entry point"""
    LOG_FILE = "/var/log/suricata/eve.json"
    NATS_URL = "nats://localhost:4222"
    PUBLISH_SUBJECT = "network.events"
    POLL_INTERVAL = 5

    adapter = SuricataAdapter(
        log_file=LOG_FILE,
        nats_url=NATS_URL,
        publish_subject=PUBLISH_SUBJECT,
        poll_interval=POLL_INTERVAL,
    )

    await adapter.connect()
    await adapter.run()


if __name__ == "__main__":
    asyncio.run(main())
