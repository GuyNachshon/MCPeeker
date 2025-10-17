"""Judge service FastAPI application.

Reference: FR-020 (≤400ms p95 latency), FR-022 (LLM judge), US4
"""
import os
import time
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from starlette.responses import Response

from ..judge.classifier import JudgeClassifier


# Prometheus metrics
INFERENCE_DURATION = Histogram(
    "judge_inference_latency_seconds",
    "Judge inference latency in seconds",
    buckets=[0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 2.0, 5.0],
)
REQUESTS_TOTAL = Counter(
    "judge_requests_total",
    "Total number of judge requests",
    ["status"],
)
CACHE_HITS = Counter("judge_cache_hits_total", "Total cache hits")
CACHE_MISSES = Counter("judge_cache_misses_total", "Total cache misses")
CLASSIFICATION_DISTRIBUTION = Counter(
    "judge_classification_total",
    "Distribution of classifications",
    ["classification"],
)
ACTIVE_WORKERS = Gauge("judge_active_workers", "Number of active workers")
QUEUE_DEPTH = Gauge("judge_queue_depth", "Number of requests in queue")


# Pydantic models
class Evidence(BaseModel):
    """Evidence for classification."""
    type: str = Field(..., description="Evidence type (endpoint, network, gateway)")
    source: str = Field(..., description="Evidence source")
    file_path: str | None = None
    process_name: str | None = None
    snippet: str | None = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ClassificationRequest(BaseModel):
    """Request for classification."""
    detection_id: str = Field(..., description="Detection ID")
    host_id: str = Field(..., description="Host ID (hashed)")
    timestamp: str = Field(..., description="Detection timestamp")
    evidence: List[Evidence] = Field(..., description="Evidence list")
    bypass_cache: bool = Field(False, description="Bypass cache")


class ClassificationResponse(BaseModel):
    """Classification result."""
    detection_id: str
    classification: str  # authorized, suspect, unauthorized
    confidence: int  # 0-100
    score_contribution: int  # Judge weight contribution
    reasoning: str
    inference_time_ms: float
    cache_hit: bool
    model: str


class BatchClassificationRequest(BaseModel):
    """Batch classification request."""
    detections: List[ClassificationRequest]


# Initialize FastAPI app
app = FastAPI(
    title="MCPeeker Judge Service",
    description="LLM-based MCP detection classifier",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize judge classifier
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

judge = JudgeClassifier(
    api_key=ANTHROPIC_API_KEY,
    model=os.getenv("JUDGE_MODEL", "claude-3-5-sonnet-20241022"),
    cache_enabled=True,
    cache_ttl_seconds=int(os.getenv("JUDGE_CACHE_TTL", "3600")),
)


@app.post("/api/v1/classify", response_model=ClassificationResponse)
async def classify_detection(request: ClassificationRequest):
    """Classify a single detection.

    Returns classification with confidence and reasoning.
    """
    start_time = time.time()
    ACTIVE_WORKERS.inc()
    QUEUE_DEPTH.inc()

    try:
        # Convert request to detection data
        detection_data = {
            "detection_id": request.detection_id,
            "host_id": request.host_id,
            "timestamp": request.timestamp,
            "evidence": [ev.dict() for ev in request.evidence],
        }

        # Classify
        result = judge.classify(detection_data, bypass_cache=request.bypass_cache)

        # Update metrics
        REQUESTS_TOTAL.labels(status="success").inc()
        CLASSIFICATION_DISTRIBUTION.labels(classification=result["classification"]).inc()

        if result.get("cache_hit"):
            CACHE_HITS.inc()
        else:
            CACHE_MISSES.inc()

        inference_time = result["inference_time_ms"] / 1000.0
        INFERENCE_DURATION.observe(inference_time)

        return ClassificationResponse(
            detection_id=request.detection_id,
            classification=result["classification"],
            confidence=result["confidence"],
            score_contribution=result["score_contribution"],
            reasoning=result["reasoning"],
            inference_time_ms=result["inference_time_ms"],
            cache_hit=result.get("cache_hit", False),
            model=result.get("model", "unknown"),
        )

    except Exception as e:
        REQUESTS_TOTAL.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        ACTIVE_WORKERS.dec()
        QUEUE_DEPTH.dec()


@app.post("/api/v1/classify/batch")
async def classify_batch(request: BatchClassificationRequest):
    """Classify multiple detections in batch.

    Returns list of classification results.
    """
    QUEUE_DEPTH.inc()

    try:
        detections = []
        for det_request in request.detections:
            detection_data = {
                "detection_id": det_request.detection_id,
                "host_id": det_request.host_id,
                "timestamp": det_request.timestamp,
                "evidence": [ev.dict() for ev in det_request.evidence],
            }
            detections.append(detection_data)

        # Batch classify
        results = judge.batch_classify(detections)

        # Update metrics
        for result in results:
            if "error" in result:
                REQUESTS_TOTAL.labels(status="error").inc()
            else:
                REQUESTS_TOTAL.labels(status="success").inc()
                CLASSIFICATION_DISTRIBUTION.labels(
                    classification=result["classification"]
                ).inc()

                if result.get("cache_hit"):
                    CACHE_HITS.inc()
                else:
                    CACHE_MISSES.inc()

        return {"results": results}

    except Exception as e:
        REQUESTS_TOTAL.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        QUEUE_DEPTH.dec()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # Check cache health
    cache_stats = judge.get_cache_stats()
    if cache_stats.get("cache_enabled") and not cache_stats.get("redis_connected"):
        raise HTTPException(status_code=503, detail="Redis cache unavailable")

    return {"status": "ready"}


@app.get("/stats")
async def get_stats():
    """Get service statistics."""
    cache_stats = judge.get_cache_stats()

    return {
        "cache": cache_stats,
        "model": judge.model,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )
