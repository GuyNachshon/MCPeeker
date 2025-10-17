// Package publisher provides NATS event publishing with JSON Schema validation.
// Reference: FR-001 (NATS messaging), FR-016 (JSON Schema validation), US1
package publisher

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/xeipuuv/gojsonschema"
)

// Publisher publishes detection events to NATS JetStream
type Publisher struct {
	nc               *nats.Conn
	js               nats.JetStreamContext
	endpointSchema   *gojsonschema.Schema
	enableValidation bool
	subject          string
}

// Config holds publisher configuration
type Config struct {
	NATSUrl          string
	Subject          string
	SchemaPath       string
	EnableValidation bool
	ConnectTimeout   time.Duration
	PublishTimeout   time.Duration
}

// NewPublisher creates a new NATS publisher
func NewPublisher(config *Config) (*Publisher, error) {
	// Connect to NATS
	nc, err := nats.Connect(
		config.NATSUrl,
		nats.Timeout(config.ConnectTimeout),
		nats.MaxReconnects(-1), // Unlimited reconnects
		nats.ReconnectWait(2*time.Second),
		nats.DisconnectErrHandler(func(nc *nats.Conn, err error) {
			if err != nil {
				fmt.Printf("NATS disconnected: %v\n", err)
			}
		}),
		nats.ReconnectHandler(func(nc *nats.Conn) {
			fmt.Printf("NATS reconnected to %s\n", nc.ConnectedUrl())
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

	publisher := &Publisher{
		nc:               nc,
		js:               js,
		enableValidation: config.EnableValidation,
		subject:          config.Subject,
	}

	// Load and compile JSON Schema if validation is enabled
	if config.EnableValidation && config.SchemaPath != "" {
		if err := publisher.loadSchema(config.SchemaPath); err != nil {
			nc.Close()
			return nil, fmt.Errorf("failed to load schema: %w", err)
		}
	}

	return publisher, nil
}

// loadSchema loads and compiles the JSON Schema
func (p *Publisher) loadSchema(schemaPath string) error {
	// Read schema file
	schemaBytes, err := os.ReadFile(schemaPath)
	if err != nil {
		return fmt.Errorf("failed to read schema file: %w", err)
	}

	// Compile schema
	schemaLoader := gojsonschema.NewStringLoader(string(schemaBytes))
	schema, err := gojsonschema.NewSchema(schemaLoader)
	if err != nil {
		return fmt.Errorf("failed to compile schema: %w", err)
	}

	p.endpointSchema = schema
	return nil
}

// PublishDetection publishes a detection event to NATS
func (p *Publisher) PublishDetection(ctx context.Context, detection interface{}) error {
	// Marshal detection to JSON
	detectionJSON, err := json.Marshal(detection)
	if err != nil {
		return fmt.Errorf("failed to marshal detection: %w", err)
	}

	// Validate against schema if enabled
	if p.enableValidation && p.endpointSchema != nil {
		if err := p.validateEvent(detectionJSON); err != nil {
			return fmt.Errorf("schema validation failed: %w", err)
		}
	}

	// Publish to NATS JetStream
	_, err = p.js.Publish(p.subject, detectionJSON, nats.Context(ctx))
	if err != nil {
		return fmt.Errorf("failed to publish to NATS: %w", err)
	}

	return nil
}

// validateEvent validates event against JSON Schema
func (p *Publisher) validateEvent(eventJSON []byte) error {
	documentLoader := gojsonschema.NewStringLoader(string(eventJSON))
	result, err := p.endpointSchema.Validate(documentLoader)
	if err != nil {
		return fmt.Errorf("validation error: %w", err)
	}

	if !result.Valid() {
		// Collect all validation errors
		var errMessages []string
		for _, desc := range result.Errors() {
			errMessages = append(errMessages, desc.String())
		}
		return fmt.Errorf("validation failed: %v", errMessages)
	}

	return nil
}

// PublishBatch publishes multiple detections in a batch
func (p *Publisher) PublishBatch(ctx context.Context, detections []interface{}) error {
	for i, detection := range detections {
		if err := p.PublishDetection(ctx, detection); err != nil {
			return fmt.Errorf("failed to publish detection %d: %w", i, err)
		}
	}
	return nil
}

// Close closes the NATS connection
func (p *Publisher) Close() error {
	if p.nc != nil {
		p.nc.Close()
	}
	return nil
}

// StreamInfo returns information about the JetStream stream
func (p *Publisher) StreamInfo(streamName string) (*nats.StreamInfo, error) {
	return p.js.StreamInfo(streamName)
}

// WaitForAck publishes with acknowledgment waiting
func (p *Publisher) PublishDetectionWithAck(ctx context.Context, detection interface{}, timeout time.Duration) error {
	// Marshal detection to JSON
	detectionJSON, err := json.Marshal(detection)
	if err != nil {
		return fmt.Errorf("failed to marshal detection: %w", err)
	}

	// Validate against schema if enabled
	if p.enableValidation && p.endpointSchema != nil {
		if err := p.validateEvent(detectionJSON); err != nil {
			return fmt.Errorf("schema validation failed: %w", err)
		}
	}

	// Publish with acknowledgment
	ackFuture, err := p.js.PublishAsync(p.subject, detectionJSON, nats.Context(ctx))
	if err != nil {
		return fmt.Errorf("failed to publish to NATS: %w", err)
	}

	// Wait for ack with timeout
	select {
	case <-ackFuture.Ok():
		return nil
	case <-ackFuture.Err():
		return fmt.Errorf("publish ack failed: %w", <-ackFuture.Err())
	case <-time.After(timeout):
		return fmt.Errorf("publish ack timeout after %v", timeout)
	case <-ctx.Done():
		return ctx.Err()
	}
}
