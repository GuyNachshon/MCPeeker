// Package clickhouse provides ClickHouse persistence for aggregated detections.
// Reference: FR-007 (ClickHouse analytics), FR-029 (90-day retention)
package clickhouse

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	_ "github.com/ClickHouse/clickhouse-go/v2"
	"github.com/google/uuid"
)

// Detection represents a detection to be written to ClickHouse
type Detection struct {
	DetectionID    string
	Timestamp      time.Time
	HostIDHash     string
	CompositeID    string
	Score          int
	Classification string
	Evidence       []Evidence
	JudgeAvailable bool
	Metadata       map[string]interface{}
}

// Evidence represents a single evidence record
type Evidence struct {
	Type              string
	Source            string
	ScoreContribution int
	Snippet           string
}

// Writer writes detections to ClickHouse
type Writer struct {
	db *sql.DB
}

// Config holds ClickHouse configuration
type Config struct {
	DSN             string
	MaxOpenConns    int
	MaxIdleConns    int
	ConnMaxLifetime time.Duration
}

// NewWriter creates a new ClickHouse writer
func NewWriter(config *Config) (*Writer, error) {
	db, err := sql.Open("clickhouse", config.DSN)
	if err != nil {
		return nil, fmt.Errorf("failed to open ClickHouse connection: %w", err)
	}

	// Configure connection pool
	db.SetMaxOpenConns(config.MaxOpenConns)
	db.SetMaxIdleConns(config.MaxIdleConns)
	db.SetConnMaxLifetime(config.ConnMaxLifetime)

	// Test connection
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping ClickHouse: %w", err)
	}

	return &Writer{db: db}, nil
}

// WriteDetection writes a detection to ClickHouse
func (w *Writer) WriteDetection(ctx context.Context, detection *Detection) error {
	// Generate UUID if not provided
	if detection.DetectionID == "" {
		detection.DetectionID = uuid.New().String()
	}

	// Prepare evidence arrays for nested columns
	var evidenceTypes []string
	var evidenceSources []string
	var evidenceScores []uint8
	var evidenceSnippets []string

	for _, ev := range detection.Evidence {
		evidenceTypes = append(evidenceTypes, ev.Type)
		evidenceSources = append(evidenceSources, ev.Source)
		evidenceScores = append(evidenceScores, uint8(ev.ScoreContribution))

		// Truncate snippet to 1KB for privacy (FR-009)
		snippet := ev.Snippet
		if len(snippet) > 1024 {
			snippet = snippet[:1024]
		}
		evidenceSnippets = append(evidenceSnippets, snippet)
	}

	// Insert query
	query := `
		INSERT INTO detections (
			detection_id,
			timestamp,
			host_id_hash,
			composite_id,
			score,
			classification,
			evidence.type,
			evidence.source,
			evidence.score_contribution,
			evidence.snippet,
			judge_available
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`

	_, err := w.db.ExecContext(
		ctx,
		query,
		detection.DetectionID,
		detection.Timestamp,
		detection.HostIDHash,
		detection.CompositeID,
		detection.Score,
		detection.Classification,
		evidenceTypes,
		evidenceSources,
		evidenceScores,
		evidenceSnippets,
		detection.JudgeAvailable,
	)

	if err != nil {
		return fmt.Errorf("failed to write detection to ClickHouse: %w", err)
	}

	return nil
}

// WriteBatch writes multiple detections in a batch
func (w *Writer) WriteBatch(ctx context.Context, detections []*Detection) error {
	if len(detections) == 0 {
		return nil
	}

	tx, err := w.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	stmt, err := tx.PrepareContext(ctx, `
		INSERT INTO detections (
			detection_id,
			timestamp,
			host_id_hash,
			composite_id,
			score,
			classification,
			evidence.type,
			evidence.source,
			evidence.score_contribution,
			evidence.snippet,
			judge_available
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`)
	if err != nil {
		return fmt.Errorf("failed to prepare statement: %w", err)
	}
	defer stmt.Close()

	for _, detection := range detections {
		// Generate UUID if not provided
		if detection.DetectionID == "" {
			detection.DetectionID = uuid.New().String()
		}

		// Prepare evidence arrays
		var evidenceTypes []string
		var evidenceSources []string
		var evidenceScores []uint8
		var evidenceSnippets []string

		for _, ev := range detection.Evidence {
			evidenceTypes = append(evidenceTypes, ev.Type)
			evidenceSources = append(evidenceSources, ev.Source)
			evidenceScores = append(evidenceScores, uint8(ev.ScoreContribution))

			snippet := ev.Snippet
			if len(snippet) > 1024 {
				snippet = snippet[:1024]
			}
			evidenceSnippets = append(evidenceSnippets, snippet)
		}

		_, err := stmt.ExecContext(
			ctx,
			detection.DetectionID,
			detection.Timestamp,
			detection.HostIDHash,
			detection.CompositeID,
			detection.Score,
			detection.Classification,
			evidenceTypes,
			evidenceSources,
			evidenceScores,
			evidenceSnippets,
			detection.JudgeAvailable,
		)
		if err != nil {
			return fmt.Errorf("failed to write detection %s: %w", detection.DetectionID, err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit batch: %w", err)
	}

	return nil
}

// QueryDetections queries detections from ClickHouse
func (w *Writer) QueryDetections(ctx context.Context, query string, args ...interface{}) (*sql.Rows, error) {
	rows, err := w.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query detections: %w", err)
	}
	return rows, nil
}

// GetDetectionCount returns the total number of detections
func (w *Writer) GetDetectionCount(ctx context.Context) (int64, error) {
	var count int64
	err := w.db.QueryRowContext(ctx, "SELECT count() FROM detections").Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("failed to get detection count: %w", err)
	}
	return count, nil
}

// GetDetectionsByTimeRange queries detections within a time range
func (w *Writer) GetDetectionsByTimeRange(
	ctx context.Context,
	startTime time.Time,
	endTime time.Time,
	limit int,
) ([]*Detection, error) {
	query := `
		SELECT
			detection_id,
			timestamp,
			host_id_hash,
			composite_id,
			score,
			classification,
			evidence.type,
			evidence.source,
			evidence.score_contribution,
			evidence.snippet,
			judge_available
		FROM detections
		WHERE timestamp >= ? AND timestamp < ?
		ORDER BY timestamp DESC
		LIMIT ?
	`

	rows, err := w.db.QueryContext(ctx, query, startTime, endTime, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to query detections: %w", err)
	}
	defer rows.Close()

	var detections []*Detection
	for rows.Next() {
		var detection Detection
		var evidenceTypes []string
		var evidenceSources []string
		var evidenceScores []uint8
		var evidenceSnippets []string

		err := rows.Scan(
			&detection.DetectionID,
			&detection.Timestamp,
			&detection.HostIDHash,
			&detection.CompositeID,
			&detection.Score,
			&detection.Classification,
			&evidenceTypes,
			&evidenceSources,
			&evidenceScores,
			&evidenceSnippets,
			&detection.JudgeAvailable,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		// Reconstruct evidence
		for i := range evidenceTypes {
			detection.Evidence = append(detection.Evidence, Evidence{
				Type:              evidenceTypes[i],
				Source:            evidenceSources[i],
				ScoreContribution: int(evidenceScores[i]),
				Snippet:           evidenceSnippets[i],
			})
		}

		detections = append(detections, &detection)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("row iteration error: %w", err)
	}

	return detections, nil
}

// Close closes the ClickHouse connection
func (w *Writer) Close() error {
	return w.db.Close()
}

// HealthCheck verifies ClickHouse connection is healthy
func (w *Writer) HealthCheck(ctx context.Context) error {
	var result int
	err := w.db.QueryRowContext(ctx, "SELECT 1").Scan(&result)
	if err != nil {
		return fmt.Errorf("health check failed: %w", err)
	}
	return nil
}
