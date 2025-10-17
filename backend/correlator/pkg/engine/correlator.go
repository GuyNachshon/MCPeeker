// Package engine provides the core correlation engine for MCP detections.
// Reference: FR-002 (Multi-layer detection), FR-003 (Weighted scoring), US4
package engine

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/identifier"
	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/registry"
)

// DetectionEvent represents an incoming detection event from any source
type DetectionEvent struct {
	EventID      string                 `json:"event_id"`
	Timestamp    time.Time              `json:"timestamp"`
	HostID       string                 `json:"host_id"`
	DetectionType string                `json:"detection_type"` // "file", "process", "network", "gateway"
	Score        int                    `json:"score"`
	Evidence     map[string]interface{} `json:"evidence"`
}

// AggregatedDetection represents a correlated detection with evidence from multiple sources
type AggregatedDetection struct {
	CompositeID      string                   `json:"composite_id"`
	HostIDHash       string                   `json:"host_id_hash"` // SHA256(host_id)
	Timestamp        time.Time                `json:"timestamp"`    // First detection time
	LastUpdated      time.Time                `json:"last_updated"`
	Score            int                      `json:"score"`
	Classification   string                   `json:"classification"` // "authorized", "suspect", "unauthorized"
	Evidence         []EvidenceRecord         `json:"evidence"`
	RegistryMatched  bool                     `json:"registry_matched"`
	RegistryPenalty  int                      `json:"registry_penalty"`
	JudgeAvailable   bool                     `json:"judge_available"`
	Metadata         map[string]interface{}   `json:"metadata"`
}

// EvidenceRecord represents a single piece of evidence
type EvidenceRecord struct {
	Type              string                 `json:"type"`   // "endpoint", "network", "gateway"
	Source            string                 `json:"source"` // "scanner-v1.0.0", "zeek", "judge"
	ScoreContribution int                    `json:"score_contribution"`
	Timestamp         time.Time              `json:"timestamp"`
	Details           map[string]interface{} `json:"details"`
}

// CorrelationWindow holds detections within the deduplication window
type CorrelationWindow struct {
	detections map[string]*AggregatedDetection // key: composite_id
	mu         sync.RWMutex
	windowSize time.Duration
}

// Correlator is the main correlation engine
type Correlator struct {
	window          *CorrelationWindow
	registryClient  *registry.Client
	clickhouseURL   string
	scoringWeights  ScoringWeights
	classThresholds ClassificationThresholds
}

// ScoringWeights defines weight for each signal type (FR-003)
type ScoringWeights struct {
	Endpoint int // Default: 11
	Judge    int // Default: 5
	Network  int // Default: 3
	Registry int // Default: -6 (penalty for authorized)
}

// ClassificationThresholds defines score ranges for classification
type ClassificationThresholds struct {
	Authorized   int // <= this value = authorized (default: 4)
	Suspect      int // <= this value = suspect (default: 8)
	Unauthorized int // > suspect threshold = unauthorized (default: 9+)
}

// NewCorrelator creates a new correlation engine
func NewCorrelator(
	windowSize time.Duration,
	registryClient *registry.Client,
	clickhouseURL string,
	weights ScoringWeights,
	thresholds ClassificationThresholds,
) *Correlator {
	return &Correlator{
		window: &CorrelationWindow{
			detections: make(map[string]*AggregatedDetection),
			windowSize: windowSize,
		},
		registryClient:  registryClient,
		clickhouseURL:   clickhouseURL,
		scoringWeights:  weights,
		classThresholds: thresholds,
	}
}

// ProcessEvent processes an incoming detection event
func (c *Correlator) ProcessEvent(ctx context.Context, event *DetectionEvent) (*AggregatedDetection, error) {
	// Generate composite ID from event
	compositeID, err := c.generateCompositeID(event)
	if err != nil {
		return nil, fmt.Errorf("failed to generate composite ID: %w", err)
	}

	// Hash host ID for privacy (FR-008)
	hostIDHash := identifier.HashHostID(event.HostID)

	// Check if detection already exists in window
	c.window.mu.Lock()
	detection, exists := c.window.detections[compositeID]

	if !exists {
		// Create new aggregated detection
		detection = &AggregatedDetection{
			CompositeID:    compositeID,
			HostIDHash:     hostIDHash,
			Timestamp:      event.Timestamp,
			LastUpdated:    event.Timestamp,
			Score:          0,
			Evidence:       []EvidenceRecord{},
			JudgeAvailable: true,
			Metadata:       make(map[string]interface{}),
		}
		c.window.detections[compositeID] = detection
	}

	// Add evidence
	evidence := EvidenceRecord{
		Type:              c.mapDetectionTypeToEvidenceType(event.DetectionType),
		Source:            c.extractSource(event),
		ScoreContribution: c.calculateScoreContribution(event),
		Timestamp:         event.Timestamp,
		Details:           event.Evidence,
	}
	detection.Evidence = append(detection.Evidence, evidence)
	detection.LastUpdated = time.Now()

	c.window.mu.Unlock()

	// Recalculate score and classification
	if err := c.recalculateDetection(ctx, detection); err != nil {
		return nil, fmt.Errorf("failed to recalculate detection: %w", err)
	}

	return detection, nil
}

// recalculateDetection recalculates score and classification for a detection
func (c *Correlator) recalculateDetection(ctx context.Context, detection *AggregatedDetection) error {
	// Check if Judge evidence is present - indicates Judge availability (FR-020a)
	hasJudgeEvidence := false
	for _, evidence := range detection.Evidence {
		if evidence.Type == "gateway" {
			hasJudgeEvidence = true
			break
		}
	}
	detection.JudgeAvailable = hasJudgeEvidence

	// Sum all evidence scores
	totalScore := 0
	for _, evidence := range detection.Evidence {
		totalScore += evidence.ScoreContribution
	}

	// Check registry for match
	registryMatch, err := c.registryClient.CheckMatch(ctx, registry.MatchRequest{
		CompositeID:  detection.CompositeID,
		HostIDHash:   detection.HostIDHash,
		ManifestHash: c.extractManifestHash(detection),
	})
	if err != nil {
		// Log error but continue
		fmt.Printf("Warning: Registry check failed: %v\n", err)
	}

	// Apply registry penalty if matched (FR-005)
	if registryMatch.Matched {
		detection.RegistryMatched = true
		detection.RegistryPenalty = c.scoringWeights.Registry
		totalScore += c.scoringWeights.Registry
	}

	// Ensure score doesn't go negative
	if totalScore < 0 {
		totalScore = 0
	}

	detection.Score = totalScore

	// Classify based on thresholds
	detection.Classification = c.classify(totalScore)

	return nil
}

// classify determines classification based on score
func (c *Correlator) classify(score int) string {
	if score <= c.classThresholds.Authorized {
		return "authorized"
	}
	if score <= c.classThresholds.Suspect {
		return "suspect"
	}
	return "unauthorized"
}

// generateCompositeID generates a composite identifier for the event
func (c *Correlator) generateCompositeID(event *DetectionEvent) (string, error) {
	// Extract components from evidence
	host := event.HostID
	port := c.extractPort(event)
	manifestHash := c.extractManifestHashFromEvent(event)
	processSignature := c.extractProcessSignature(event)

	// Generate composite ID
	return identifier.GenerateCompositeID(host, port, manifestHash, processSignature), nil
}

// Helper functions to extract data from evidence

func (c *Correlator) extractPort(event *DetectionEvent) int {
	if evidence, ok := event.Evidence["port"]; ok {
		if port, ok := evidence.(float64); ok {
			return int(port)
		}
		if port, ok := evidence.(int); ok {
			return port
		}
	}
	return 0
}

func (c *Correlator) extractManifestHashFromEvent(event *DetectionEvent) string {
	if hash, ok := event.Evidence["file_hash"].(string); ok {
		return hash
	}
	if hash, ok := event.Evidence["manifest_hash"].(string); ok {
		return hash
	}
	return ""
}

func (c *Correlator) extractProcessSignature(event *DetectionEvent) string {
	if sig, ok := event.Evidence["process_hash"].(string); ok {
		return sig
	}
	return ""
}

func (c *Correlator) extractManifestHash(detection *AggregatedDetection) string {
	// Extract from evidence details
	for _, evidence := range detection.Evidence {
		if hash, ok := evidence.Details["file_hash"].(string); ok {
			return hash
		}
		if hash, ok := evidence.Details["manifest_hash"].(string); ok {
			return hash
		}
	}
	return ""
}

func (c *Correlator) extractSource(event *DetectionEvent) string {
	if source, ok := event.Evidence["source"].(string); ok {
		return source
	}
	return "unknown"
}

func (c *Correlator) mapDetectionTypeToEvidenceType(detectionType string) string {
	switch detectionType {
	case "file", "process":
		return "endpoint"
	case "network":
		return "network"
	case "gateway", "judge":
		return "gateway"
	default:
		return "endpoint"
	}
}

func (c *Correlator) calculateScoreContribution(event *DetectionEvent) int {
	evidenceType := c.mapDetectionTypeToEvidenceType(event.DetectionType)

	// Use configured weights
	switch evidenceType {
	case "endpoint":
		return c.scoringWeights.Endpoint
	case "gateway":
		return c.scoringWeights.Judge
	case "network":
		return c.scoringWeights.Network
	default:
		return event.Score // Use event's own score if type unknown
	}
}

// GetDetection retrieves a detection from the window
func (c *Correlator) GetDetection(compositeID string) (*AggregatedDetection, bool) {
	c.window.mu.RLock()
	defer c.window.mu.RUnlock()

	detection, exists := c.window.detections[compositeID]
	return detection, exists
}

// CleanupExpired removes detections older than the window size
func (c *Correlator) CleanupExpired() int {
	c.window.mu.Lock()
	defer c.window.mu.Unlock()

	now := time.Now()
	cutoff := now.Add(-c.window.windowSize)
	removed := 0

	for compositeID, detection := range c.window.detections {
		if detection.LastUpdated.Before(cutoff) {
			delete(c.window.detections, compositeID)
			removed++
		}
	}

	return removed
}

// GetWindowSize returns the current deduplication window size
func (c *Correlator) GetWindowSize() time.Duration {
	return c.window.windowSize
}

// GetActiveDetections returns the number of detections in the window
func (c *Correlator) GetActiveDetections() int {
	c.window.mu.RLock()
	defer c.window.mu.RUnlock()
	return len(c.window.detections)
}
