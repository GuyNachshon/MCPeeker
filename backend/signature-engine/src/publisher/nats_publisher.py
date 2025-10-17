"""
NATS publisher for enriched events

Reference: US4 (Multi-layer correlation), T057
"""

import asyncio
import json
import logging
from typing import Dict, Any

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class NATSPublisher:
    """Publisher for enriched detection events to NATS JetStream"""

    def __init__(self, nats_url: str):
        self.nats_url = nats_url
        self.nc: NATS = None
        self.js: JetStreamContext = None

    async def connect(self) -> None:
        """Connect to NATS JetStream"""
        try:
            self.nc = NATS()
            await self.nc.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info(f"Connected to NATS at {self.nats_url}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from NATS"""
        if self.nc:
            await self.nc.close()
            logger.info("Disconnected from NATS")

    async def publish_enriched_event(self, event: Dict[str, Any]) -> None:
        """
        Publish enriched event to NATS for correlator consumption.

        Events are published to subjects based on their source:
        - endpoint events -> enriched.endpoint
        - network events -> enriched.network
        - gateway events -> enriched.gateway
        """
        if not self.js:
            raise RuntimeError("Not connected to NATS")

        try:
            # Determine subject based on event source
            source = event.get("source", "unknown")
            subject = self._get_subject_for_source(source)

            # Serialize event
            event_json = json.dumps(event, default=str)

            # Publish to JetStream
            await self.js.publish(
                subject,
                event_json.encode('utf-8')
            )

            logger.debug(f"Published enriched event to {subject}: {event.get('event_id')}")

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    def _get_subject_for_source(self, source: str) -> str:
        """Map event source to NATS subject"""
        if "endpoint" in source:
            return "enriched.endpoint"
        elif "network" in source:
            return "enriched.network"
        elif "gateway" in source or "judge" in source:
            return "enriched.gateway"
        else:
            return "enriched.unknown"

    async def publish_batch(self, events: list[Dict[str, Any]]) -> None:
        """Publish multiple enriched events in batch"""
        for event in events:
            await self.publish_enriched_event(event)

        logger.info(f"Published batch of {len(events)} enriched events")
