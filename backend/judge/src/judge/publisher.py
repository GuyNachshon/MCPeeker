"""
NATS event publisher for Judge classifications

Reference: US5 (Transparency), T085
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class JudgePublisher:
    """Publishes Judge classification events to NATS JetStream"""

    def __init__(self, nats_url: str):
        self.nats_url = nats_url
        self.nc: NATS = None
        self.js: JetStreamContext = None

    async def connect(self) -> None:
        """Connect to NATS JetStream"""
        self.nc = NATS()
        await self.nc.connect(self.nats_url)
        self.js = self.nc.jetstream()
        logger.info(f"Connected to NATS at {self.nats_url}")

    async def disconnect(self) -> None:
        """Disconnect from NATS"""
        if self.nc:
            await self.nc.close()
            logger.info("Disconnected from NATS")

    async def publish_classification(
        self,
        detection_id: str,
        classification: str,
        confidence: float,
        reasoning: str,
        score_contribution: int,
        model_version: str = "claude-3-5-sonnet-20241022"
    ) -> None:
        """
        Publish Judge classification event to NATS

        Args:
            detection_id: Unique detection identifier
            classification: AUTHORIZED, SUSPECT, or UNAUTHORIZED
            confidence: Confidence score (0-100)
            reasoning: Plain-language explanation
            score_contribution: Points to add to total score
            model_version: Model identifier
        """
        event = {
            "event_id": f"judge-{detection_id}-{int(datetime.now(timezone.utc).timestamp())}",
            "detection_id": detection_id,
            "source": "gateway.judge",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "classification": classification,
            "confidence": confidence,
            "reasoning": reasoning,
            "score_contribution": score_contribution,
            "model_version": model_version,
            "metadata": {
                "service": "judge",
                "version": "1.0.0"
            }
        }

        try:
            # Publish to gateway.events stream (gateway.classification.judge subject)
            subject = "gateway.classification.judge"
            await self.js.publish(
                subject,
                json.dumps(event).encode('utf-8')
            )
            logger.info(
                f"Published classification event: detection_id={detection_id}, "
                f"classification={classification}, confidence={confidence:.2f}"
            )
        except Exception as e:
            logger.error(f"Failed to publish classification event: {e}")
            raise

    async def publish_batch(self, events: list[Dict[str, Any]]) -> None:
        """Publish multiple classification events"""
        for event_data in events:
            await self.publish_classification(**event_data)
