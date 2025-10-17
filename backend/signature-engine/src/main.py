"""
Signature Engine main entry point

Subscribes to detection events, enriches them with rules, and republishes.
Reference: US4 (Multi-layer correlation), T058
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from nats.aio.client import Client as NATS

from parsers.endpoint_parser import EndpointParser
from parsers.network_parser import NetworkParser
from parsers.gateway_parser import GatewayParser
from rules.engine import RuleEngine
from publisher.nats_publisher import NATSPublisher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SignatureEngine:
    """Main signature engine orchestrator"""

    def __init__(
        self,
        nats_url: str,
        rules_file: str,
    ):
        self.nats_url = nats_url
        self.rules_file = rules_file

        # Components
        self.nc: NATS = None
        self.js = None
        self.endpoint_parser = EndpointParser()
        self.network_parser = NetworkParser()
        self.gateway_parser = GatewayParser()
        self.rule_engine = RuleEngine(rules_file)
        self.publisher = NATSPublisher(nats_url)

        # State
        self.running = False
        self.processed_count = 0

    async def start(self) -> None:
        """Start the signature engine"""
        logger.info("Starting Signature Engine...")

        # Connect to NATS
        self.nc = NATS()
        await self.nc.connect(self.nats_url)
        self.js = self.nc.jetstream()
        logger.info(f"Connected to NATS at {self.nats_url}")

        # Connect publisher
        await self.publisher.connect()

        # Subscribe to raw detection streams
        await self._subscribe_to_streams()

        self.running = True
        logger.info("Signature Engine started successfully")

    async def _subscribe_to_streams(self) -> None:
        """Subscribe to detection event streams"""
        # Subscribe to endpoint events
        await self.js.subscribe(
            "endpoint.events",
            cb=self._handle_endpoint_event,
            durable="signature-engine-endpoint",
        )
        logger.info("Subscribed to endpoint.events")

        # Subscribe to network events
        await self.js.subscribe(
            "network.events",
            cb=self._handle_network_event,
            durable="signature-engine-network",
        )
        logger.info("Subscribed to network.events")

        # Subscribe to gateway events
        await self.js.subscribe(
            "gateway.events",
            cb=self._handle_gateway_event,
            durable="signature-engine-gateway",
        )
        logger.info("Subscribed to gateway.events")

    async def _handle_endpoint_event(self, msg) -> None:
        """Handle endpoint detection event"""
        try:
            # Parse event
            parsed = self.endpoint_parser.parse(msg.data)
            if not parsed:
                logger.warning("Failed to parse endpoint event")
                await msg.nak()
                return

            # Enrich with rules
            enriched = self.rule_engine.apply_rules(parsed)

            # Publish enriched event
            await self.publisher.publish_enriched_event(enriched)

            # Ack message
            await msg.ack()
            self.processed_count += 1

            if self.processed_count % 100 == 0:
                logger.info(f"Processed {self.processed_count} events")

        except Exception as e:
            logger.error(f"Error handling endpoint event: {e}")
            await msg.nak()

    async def _handle_network_event(self, msg) -> None:
        """Handle network detection event"""
        try:
            # Parse event
            parsed = self.network_parser.parse(msg.data)
            if not parsed:
                logger.warning("Failed to parse network event")
                await msg.nak()
                return

            # Enrich with rules
            enriched = self.rule_engine.apply_rules(parsed)

            # Publish enriched event
            await self.publisher.publish_enriched_event(enriched)

            # Ack message
            await msg.ack()
            self.processed_count += 1

        except Exception as e:
            logger.error(f"Error handling network event: {e}")
            await msg.nak()

    async def _handle_gateway_event(self, msg) -> None:
        """Handle gateway classification event"""
        try:
            # Parse event
            parsed = self.gateway_parser.parse(msg.data)
            if not parsed:
                logger.warning("Failed to parse gateway event")
                await msg.nak()
                return

            # Enrich with rules
            enriched = self.rule_engine.apply_rules(parsed)

            # Publish enriched event
            await self.publisher.publish_enriched_event(enriched)

            # Ack message
            await msg.ack()
            self.processed_count += 1

        except Exception as e:
            logger.error(f"Error handling gateway event: {e}")
            await msg.nak()

    async def stop(self) -> None:
        """Stop the signature engine gracefully"""
        logger.info("Stopping Signature Engine...")
        self.running = False

        # Disconnect from NATS
        if self.publisher:
            await self.publisher.disconnect()
        if self.nc:
            await self.nc.close()

        logger.info(f"Signature Engine stopped. Processed {self.processed_count} events total.")

    async def run_forever(self) -> None:
        """Run the engine until interrupted"""
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()


async def main():
    """Main entry point"""
    # Configuration (could be loaded from YAML)
    NATS_URL = "nats://localhost:4222"
    RULES_FILE = "/etc/mcpeeker/rules/community-signatures.yaml"

    # Create and start engine
    engine = SignatureEngine(
        nats_url=NATS_URL,
        rules_file=RULES_FILE,
    )

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(engine.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start engine
    await engine.start()

    # Run until stopped
    await engine.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
