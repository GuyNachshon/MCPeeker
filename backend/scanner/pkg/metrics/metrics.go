// Package metrics provides Prometheus metrics for the scanner service.
// Reference: FR-014 (Prometheus metrics exposure), SC-015 (≥95% instrumentation)
package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// EventPublishedTotal counts total events published to NATS
	EventPublishedTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "scanner_events_published_total",
			Help: "Total number of detection events published to NATS",
		},
		[]string{"detection_type"}, // file, process
	)

	// ScanDurationSeconds measures scan duration
	ScanDurationSeconds = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "scanner_scan_duration_seconds",
			Help:    "Time taken to complete filesystem scan",
			Buckets: prometheus.ExponentialBuckets(1, 2, 10), // 1s to ~17min
		},
		[]string{"scan_type"}, // file, process
	)

	// FilesScannedTotal counts total files scanned
	FilesScannedTotal = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "scanner_files_scanned_total",
			Help: "Total number of files scanned",
		},
	)

	// DetectionsFoundTotal counts detections found
	DetectionsFoundTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "scanner_detections_found_total",
			Help: "Total number of MCP detections found",
		},
		[]string{"detection_type"},
	)

	// NATSPublishErrorsTotal counts NATS publish failures
	NATSPublishErrorsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "scanner_nats_publish_errors_total",
			Help: "Total number of NATS publish failures",
		},
		[]string{"error_type"},
	)

	// ScanErrorsTotal counts scan errors
	ScanErrorsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "scanner_errors_total",
			Help: "Total number of scan errors",
		},
		[]string{"error_type"},
	)
)
