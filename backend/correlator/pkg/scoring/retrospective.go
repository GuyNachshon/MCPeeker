// Package scoring provides retrospective scoring for detections when Judge recovers
// Reference: FR-020c (Retrospective scoring), US5 (Transparency)
package scoring

import (
	"context"
	"fmt"
	"time"

	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/engine"
)

// RetrospectiveScorer handles re-scoring of detections when Judge service recovers
type RetrospectiveScorer struct {
	correlator     *engine.Correlator
	judgeClient    JudgeClient
	clickhouseConn ClickHouseConnection
	maxRetries     int
	retryInterval  time.Duration
}

// JudgeClient interface for calling Judge service
type JudgeClient interface {
	Classify(ctx context.Context, detection *engine.AggregatedDetection) (*JudgeClassification, error)
	HealthCheck(ctx context.Context) error
}

// ClickHouseConnection interface for querying detections
type ClickHouseConnection interface {
	QueryDetectionsWithoutJudge(ctx context.Context, limit int) ([]*engine.AggregatedDetection, error)
	UpdateDetection(ctx context.Context, detection *engine.AggregatedDetection) error
}

// JudgeClassification represents the result from Judge service
type JudgeClassification struct {
	Classification    string
	Confidence        float64
	Reasoning         string
	ScoreContribution int
}

// NewRetrospectiveScorer creates a new retrospective scorer
func NewRetrospectiveScorer(
	correlator *engine.Correlator,
	judgeClient JudgeClient,
	clickhouseConn ClickHouseConnection,
	maxRetries int,
	retryInterval time.Duration,
) *RetrospectiveScorer {
	return &RetrospectiveScorer{
		correlator:     correlator,
		judgeClient:    judgeClient,
		clickhouseConn: clickhouseConn,
		maxRetries:     maxRetries,
		retryInterval:  retryInterval,
	}
}

// RunRetrospectiveScoring performs retrospective scoring on detections without Judge evidence
// This function should be called periodically (e.g., every 10 minutes) or triggered when Judge recovers
func (rs *RetrospectiveScorer) RunRetrospectiveScoring(ctx context.Context, batchSize int) error {
	// Check if Judge is available
	if err := rs.judgeClient.HealthCheck(ctx); err != nil {
		return fmt.Errorf("judge service unavailable: %w", err)
	}

	// Query detections that don't have Judge evidence
	detections, err := rs.clickhouseConn.QueryDetectionsWithoutJudge(ctx, batchSize)
	if err != nil {
		return fmt.Errorf("failed to query detections: %w", err)
	}

	if len(detections) == 0 {
		return nil // Nothing to rescore
	}

	fmt.Printf("Found %d detections without Judge evidence, starting retrospective scoring\n", len(detections))

	successCount := 0
	errorCount := 0

	for _, detection := range detections {
		if err := rs.rescoreDetection(ctx, detection); err != nil {
			fmt.Printf("Failed to rescore detection %s: %v\n", detection.CompositeID, err)
			errorCount++
		} else {
			successCount++
		}

		// Check if context is cancelled
		select {
		case <-ctx.Done():
			return fmt.Errorf("retrospective scoring cancelled: %w", ctx.Err())
		default:
		}
	}

	fmt.Printf("Retrospective scoring complete: %d succeeded, %d failed\n", successCount, errorCount)
	return nil
}

// rescoreDetection re-scores a single detection with Judge classification
func (rs *RetrospectiveScorer) rescoreDetection(ctx context.Context, detection *engine.AggregatedDetection) error {
	// Call Judge service for classification
	classification, err := rs.judgeClient.Classify(ctx, detection)
	if err != nil {
		return fmt.Errorf("judge classification failed: %w", err)
	}

	// Add Judge evidence to detection
	judgeEvidence := engine.EvidenceRecord{
		Type:              "gateway",
		Source:            "judge-retrospective",
		ScoreContribution: classification.ScoreContribution,
		Timestamp:         time.Now(),
		Details: map[string]interface{}{
			"classification": classification.Classification,
			"confidence":     classification.Confidence,
			"reasoning":      classification.Reasoning,
			"retrospective":  true, // Mark as retrospectively added
		},
	}

	detection.Evidence = append(detection.Evidence, judgeEvidence)
	detection.JudgeAvailable = true
	detection.LastUpdated = time.Now()

	// Recalculate total score
	totalScore := 0
	for _, evidence := range detection.Evidence {
		totalScore += evidence.ScoreContribution
	}

	// Apply registry penalty if matched
	if detection.RegistryMatched {
		totalScore += detection.RegistryPenalty
	}

	// Ensure score doesn't go negative
	if totalScore < 0 {
		totalScore = 0
	}

	detection.Score = totalScore

	// Reclassify based on new score
	if totalScore <= 4 {
		detection.Classification = "authorized"
	} else if totalScore <= 8 {
		detection.Classification = "suspect"
	} else {
		detection.Classification = "unauthorized"
	}

	// Update detection in ClickHouse
	if err := rs.clickhouseConn.UpdateDetection(ctx, detection); err != nil {
		return fmt.Errorf("failed to update detection: %w", err)
	}

	fmt.Printf("Successfully rescored detection %s: new score=%d, classification=%s\n",
		detection.CompositeID, detection.Score, detection.Classification)

	return nil
}

// SchedulePeriodicScoring starts a background goroutine that performs retrospective scoring periodically
func (rs *RetrospectiveScorer) SchedulePeriodicScoring(ctx context.Context, interval time.Duration, batchSize int) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			// Run retrospective scoring
			if err := rs.RunRetrospectiveScoring(ctx, batchSize); err != nil {
				fmt.Printf("Retrospective scoring error: %v\n", err)
			}
		case <-ctx.Done():
			fmt.Println("Stopping retrospective scoring scheduler")
			return
		}
	}
}
