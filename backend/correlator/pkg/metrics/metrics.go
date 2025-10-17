// Package metrics provides Prometheus metrics for the correlator service.
// Reference: FR-014 (Prometheus metrics exposure), SC-015 (≥95% instrumentation)
package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// DetectionProcessedTotal counts total detections processed
	DetectionProcessedTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "correlator_detections_processed_total",
			Help: "Total number of detections processed and correlated",
		},
		[]string{"source_type"}, // endpoint, network, gateway
	)

	// ClickHouseWriteLatencySeconds measures ClickHouse write latency
	ClickHouseWriteLatencySeconds = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "correlator_clickhouse_write_latency_seconds",
			Help:    "ClickHouse write latency in seconds",
			Buckets: prometheus.ExponentialBuckets(0.001, 2, 10), // 1ms to ~1s
		},
	)

	// RegistryLookupLatencySeconds measures registry lookup latency
	RegistryLookupLatencySeconds = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "correlator_registry_lookup_latency_seconds",
			Help:    "Registry lookup latency via HTTP API",
			Buckets: prometheus.ExponentialBuckets(0.01, 2, 8), // 10ms to ~1.3s
		},
	)

	// DeduplicationMatchesTotal counts deduplicated detections
	DeduplicationMatchesTotal = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "correlator_deduplication_matches_total",
			Help: "Total number of detections deduplicated within 5-minute window",
		},
	)

	// CorrelationScoreDistribution tracks score distribution
	CorrelationScoreDistribution = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "correlator_correlation_score",
			Help:    "Distribution of correlation scores assigned to detections",
			Buckets: []float64{1, 3, 5, 7, 9, 11, 13, 15, 20}, // Score thresholds
		},
	)

	// ClassificationDistributionTotal counts detections by classification
	ClassificationDistributionTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "correlator_classification_total",
			Help: "Total detections by classification type",
		},
		[]string{"classification"}, // authorized, suspect, unauthorized
	)

	// RegistryMatchedTotal counts registry-matched detections
	RegistryMatchedTotal = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "correlator_registry_matched_total",
			Help: "Total detections matched to authorized registry entries",
		},
	)

	// ErrorsTotal counts correlator errors
	ErrorsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "correlator_errors_total",
			Help: "Total correlator errors",
		},
		[]string{"error_type"},
	)
)
