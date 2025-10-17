// Package consumer provides NATS JetStream consumer for detection events.
// Reference: FR-001 (NATS messaging), FR-002 (Multi-layer detection)
package consumer

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/clickhouse"
	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/engine"
)

// Consumer consumes detection events from NATS JetStream
type Consumer struct {
	nc         *nats.Conn
	js         nats.JetStreamContext
	correlator *engine.Correlator
	chWriter   *clickhouse.Writer
	subjects   []string
}

// Config holds consumer configuration
type Config struct {
	NATSUrl    string
	Subjects   []string // e.g., ["endpoint.events", "network.events", "gateway.events"]
	StreamName string
	DurableName string
	BatchSize  int
}

// NewConsumer creates a new NATS consumer
func NewConsumer(
	config *Config,
	correlator *engine.Correlator,
	chWriter *clickhouse.Writer,
) (*Consumer, error) {
	// Connect to NATS
	nc, err := nats.Connect(
		config.NATSUrl,
		nats.MaxReconnects(-1),
		nats.ReconnectWait(2*time.Second),
		nats.DisconnectErrHandler(func(nc *nats.Conn, err error) {
			if err != nil {
				log.Printf("NATS disconnected: %v\n", err)
			}
		}),
		nats.ReconnectHandler(func(nc *nats.Conn) {
			log.Printf("NATS reconnected to %s\n", nc.ConnectedUrl())
		}),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	// Create JetStream context
	js, err := nc.JetStream()
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("failed to create JetStream context: %w", err)
	}

	return &Consumer{
		nc:         nc,
		js:         js,
		correlator: correlator,
		chWriter:   chWriter,
		subjects:   config.Subjects,
	}, nil
}

// Start starts consuming messages
func (c *Consumer) Start(ctx context.Context) error {
	log.Println("Starting NATS consumer...")

	// Subscribe to all subjects
	for _, subject := range c.subjects {
		if err := c.subscribeToSubject(ctx, subject); err != nil {
			return fmt.Errorf("failed to subscribe to %s: %w", subject, err)
		}
		log.Printf("Subscribed to subject: %s", subject)
	}

	// Wait for context cancellation
	<-ctx.Done()
	log.Println("Stopping NATS consumer...")

	return nil
}

// subscribeToSubject subscribes to a specific subject
func (c *Consumer) subscribeToSubject(ctx context.Context, subject string) error {
	// Create pull subscription
	sub, err := c.js.PullSubscribe(
		subject,
		"correlator",
		nats.ManualAck(),
		nats.AckWait(30*time.Second),
	)
	if err != nil {
		return fmt.Errorf("failed to create pull subscription: %w", err)
	}

	// Start message processing goroutine
	go c.processMessages(ctx, sub, subject)

	return nil
}

// processMessages processes messages from a subscription
func (c *Consumer) processMessages(ctx context.Context, sub *nats.Subscription, subject string) {
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			// Fetch batch of messages
			msgs, err := sub.Fetch(10, nats.MaxWait(100*time.Millisecond))
			if err != nil {
				// Timeout is expected when no messages available
				if err == nats.ErrTimeout {
					continue
				}
				log.Printf("Error fetching messages from %s: %v", subject, err)
				continue
			}

			// Process each message
			for _, msg := range msgs {
				if err := c.processMessage(ctx, msg, subject); err != nil {
					log.Printf("Error processing message from %s: %v", subject, err)
					// Negative ack to retry later
					msg.Nak()
				} else {
					// Ack successful processing
					msg.Ack()
				}
			}
		}
	}
}

// processMessage processes a single message
func (c *Consumer) processMessage(ctx context.Context, msg *nats.Msg, subject string) error {
	// Parse detection event
	var event engine.DetectionEvent
	if err := json.Unmarshal(msg.Data, &event); err != nil {
		return fmt.Errorf("failed to unmarshal event: %w", err)
	}

	// Process through correlator
	detection, err := c.correlator.ProcessEvent(ctx, &event)
	if err != nil {
		return fmt.Errorf("correlation failed: %w", err)
	}

	// Write to ClickHouse
	chDetection := c.convertToClickHouseDetection(detection)
	if err := c.chWriter.WriteDetection(ctx, chDetection); err != nil {
		return fmt.Errorf("failed to write to ClickHouse: %w", err)
	}

	log.Printf("Processed detection: %s (score: %d, classification: %s)",
		detection.CompositeID, detection.Score, detection.Classification)

	return nil
}

// convertToClickHouseDetection converts engine detection to ClickHouse format
func (c *Consumer) convertToClickHouseDetection(detection *engine.AggregatedDetection) *clickhouse.Detection {
	chDetection := &clickhouse.Detection{
		DetectionID:    "", // Will be generated
		Timestamp:      detection.Timestamp,
		HostIDHash:     detection.HostIDHash,
		CompositeID:    detection.CompositeID,
		Score:          detection.Score,
		Classification: detection.Classification,
		JudgeAvailable: detection.JudgeAvailable,
		Metadata:       detection.Metadata,
	}

	// Convert evidence
	for _, ev := range detection.Evidence {
		snippet, _ := json.Marshal(ev.Details)
		chDetection.Evidence = append(chDetection.Evidence, clickhouse.Evidence{
			Type:              ev.Type,
			Source:            ev.Source,
			ScoreContribution: ev.ScoreContribution,
			Snippet:           string(snippet),
		})
	}

	return chDetection
}

// Close closes the NATS connection
func (c *Consumer) Close() error {
	if c.nc != nil {
		c.nc.Close()
	}
	return nil
}

// GetStats returns consumer statistics
func (c *Consumer) GetStats() map[string]interface{} {
	stats := map[string]interface{}{
		"connected":         c.nc.IsConnected(),
		"active_detections": c.correlator.GetActiveDetections(),
		"window_size":       c.correlator.GetWindowSize().String(),
	}

	if c.nc.IsConnected() {
		stats["server_url"] = c.nc.ConnectedUrl()
	}

	return stats
}
