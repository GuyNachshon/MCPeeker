"""Prometheus metrics for Judge service.

Reference: FR-014 (Prometheus metrics exposure), FR-020 (≤400ms latency), SC-006
"""
from prometheus_client import Counter, Histogram, Gauge

# Inference latency histogram (SC-006: ≤400ms p95 target)
inference_latency_seconds = Histogram(
    "judge_inference_latency_seconds",
    "LLM Judge inference latency in seconds",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0],  # 50ms to 1s
)

# Cache hit rate
cache_hit_rate = Counter(
    "judge_cache_hits_total",
    "Total number of cache hits for inference requests"
)

cache_miss_rate = Counter(
    "judge_cache_misses_total",
    "Total number of cache misses for inference requests"
)

# Classification distribution
classifications_total = Counter(
    "judge_classifications_total",
    "Total classifications by label",
    ["label"],  # mcp_server, json_rpc_client, generic_llm, unknown
)

# Confidence score distribution
confidence_score = Histogram(
    "judge_confidence_score",
    "Distribution of model confidence scores",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99],
)

# Request rate
requests_total = Counter(
    "judge_requests_total",
    "Total classification requests received",
    ["status"],  # success, error
)

# Model load time
model_load_duration_seconds = Gauge(
    "judge_model_load_duration_seconds",
    "Time taken to load model at startup"
)

# Active inference workers
active_workers = Gauge(
    "judge_active_workers",
    "Number of active inference worker threads"
)

# Queue depth
queue_depth = Gauge(
    "judge_queue_depth",
    "Number of inference requests waiting in queue"
)

# NATS publish metrics
nats_publish_total = Counter(
    "judge_nats_publish_total",
    "Total events published to NATS",
    ["status"],  # success, error
)

# Error counters
errors_total = Counter(
    "judge_errors_total",
    "Total Judge service errors",
    ["error_type"],
)
