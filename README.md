# MCPeeker: MCP Detection and Registry Platform

**Version:** 1.0.0
**Status:** Production Ready
**License:** MIT

## Overview

MCPeeker is a comprehensive detection and management platform for Model Context Protocol (MCP) servers. It provides multi-layer detection, scoring, correlation, and lifecycle management for MCP instances across your organization.

### Key Features

- **Multi-Layer Detection**: Endpoint (file + process), Network (Zeek/Suricata), Gateway (LLM analysis)
- **Weighted Scoring**: Intelligent scoring algorithm with configurable thresholds
- **Registry Management**: Self-service registration with admin approval workflow
- **SOC Analyst Investigation**: Collaborative feedback and investigation tracking
- **AI-Powered Classification**: Claude 3.5 Sonnet for context-aware analysis
- **Observability**: Real-time dashboards, metrics, and transparency features

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Scanner   │────▶│     NATS     │────▶│ Correlator  │
│  (Go)       │     │  JetStream   │     │    (Go)     │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                     │
                           │                     ▼
                    ┌──────────────┐     ┌─────────────┐
                    │    Judge     │     │ ClickHouse  │
                    │  (Python)    │     │  (Analytics)│
                    └──────────────┘     └─────────────┘
                                                │
                    ┌──────────────────┐        │
                    │  Registry API    │◀───────┘
                    │   (FastAPI)      │
                    └──────────────────┘
                           │
                           ▼
                    ┌──────────────────┐
                    │  React Frontend  │
                    │   (TypeScript)   │
                    └──────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Go 1.21+
- Python 3.11+
- Node.js 18+
- Kubernetes cluster (for production deployment)

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/ozlabs/mcpeeker.git
cd mcpeeker

# 2. Start infrastructure services
cd infrastructure/docker
docker-compose up -d

# 3. Start backend services
# Terminal 1: Scanner
cd backend/scanner
go run cmd/scanner/main.go

# Terminal 2: Correlator
cd backend/correlator
go run cmd/correlator/main.go

# Terminal 3: Judge
cd backend/judge
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
uvicorn src.api.main:app --reload

# Terminal 4: Registry API
cd backend/registry-api
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload

# 4. Start frontend
cd frontend
npm install
npm run dev

# Access UI at http://localhost:5173
```

### Production Deployment

```bash
# Deploy to Kubernetes using Helm
helm install mcpeeker infrastructure/helm/mcpeeker \
  --set global.domain=mcpeeker.example.com \
  --set judge.anthropic_api_key=$ANTHROPIC_API_KEY \
  --set nats.replicas=3 \
  --set clickhouse.shards=2
```

## Configuration

### Global Configuration

See `infrastructure/configs/global.yaml` for shared settings:

```yaml
nats:
  url: nats://localhost:4222
  cluster_name: mcpeeker-cluster

clickhouse:
  host: localhost
  port: 9000
  database: mcpeeker

postgresql:
  host: localhost
  port: 5432
  database: registry

security:
  mtls_enabled: true
  certificate_path: /etc/mcpeeker/certs
```

### Service-Specific Configuration

- **Scanner**: `infrastructure/configs/scanner.yaml`
- **Correlator**: `infrastructure/configs/correlator.yaml`
- **Judge**: `infrastructure/configs/judge.yaml`
- **Registry API**: `infrastructure/configs/registry-api.yaml`

## User Roles

### Developer
- View own detections and registrations
- Self-register MCPs with business justification
- Receive expiration notifications

### Analyst
- View all detections across organization
- Investigate high-risk detections
- Submit feedback (true positive, false positive, etc.)
- Collaborate with notes and timelines

### Admin
- All Analyst permissions
- Approve/reject/revoke registrations
- Manage users and notification preferences
- Access full analytics dashboard

## API Documentation

### Authentication

All API requests require a Bearer token:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api.mcpeeker.example.com/api/v1/detections
```

### Key Endpoints

#### Detections API
- `GET /api/v1/detections` - List detections
- `GET /api/v1/detections/{id}` - Get detection details

#### Registry API
- `POST /api/v1/registry/entries` - Register MCP
- `GET /api/v1/registry/entries` - List registrations
- `POST /api/v1/registry/entries/{id}/approve` - Approve (Admin)
- `POST /api/v1/registry/entries/{id}/reject` - Reject (Admin)

#### Feedback API
- `POST /api/v1/feedback` - Submit analyst feedback
- `GET /api/v1/feedback/detection/{id}/timeline` - Investigation timeline

#### Analytics API
- `GET /api/v1/analytics/summary` - Dashboard summary
- `GET /api/v1/analytics/score-distribution` - Score histogram
- `GET /api/v1/analytics/trendlines` - Time-series data

Full API documentation available at: `https://api.mcpeeker.example.com/docs`

## Scoring Algorithm

MCPeeker uses a weighted scoring system:

| Evidence Type | Weight | Description |
|--------------|--------|-------------|
| Endpoint | +11 | File or process detection |
| Judge (LLM) | +5 | AI classification |
| Network | +3 | Traffic patterns |
| Registry | -6 | Approved MCP penalty |

### Classification Thresholds

- **Authorized** (≤4): Safe, registered MCP
- **Suspect** (5-8): Needs review
- **Unauthorized** (≥9): High risk, requires investigation

## Monitoring

### Prometheus Metrics

Metrics exposed on `:9090/metrics`:

```
# Scanner
mcpeeker_scanner_events_published_total
mcpeeker_scanner_scan_duration_seconds

# Correlator
mcpeeker_correlator_detections_processed_total
mcpeeker_correlator_clickhouse_write_latency_seconds

# Judge
mcpeeker_judge_inference_latency_seconds
mcpeeker_judge_cache_hit_rate
```

### Grafana Dashboards

Pre-built dashboards available in `infrastructure/configs/grafana/dashboards/`:

1. **Detection Overview**: Score distribution, classification breakdown, trendlines
2. **Pipeline Health**: Service health, NATS throughput, ClickHouse performance
3. **Investigation Metrics**: Feedback stats, response times, SLA tracking

## Security

### Privacy (FR-008, FR-009)

- Host IDs are SHA256-hashed before storage
- Snippets limited to ≤1KB
- No full file contents stored
- Network payloads not exposed in UI

### mTLS Support

All service-to-service communication supports mTLS:

```bash
# Generate certificates
./infrastructure/scripts/generate-certs.sh

# Certificates automatically rotated via cert-manager in Kubernetes
```

### Audit Logging

All registry operations are logged with HMAC-SHA256 signatures:

```sql
SELECT * FROM audit_logs
WHERE action = 'APPROVE'
  AND resource_type = 'registry_entry'
ORDER BY timestamp DESC;
```

## Troubleshooting

### Common Issues

#### Scanner not detecting MCPs

```bash
# Check filesystem permissions
ls -la /path/to/mcp/directory

# Verify scanner config
cat infrastructure/configs/scanner.yaml

# Check scanner logs
docker logs mcpeeker-scanner
```

#### Judge service errors

```bash
# Verify API key
echo $ANTHROPIC_API_KEY

# Check Redis connectivity
redis-cli ping

# View Judge logs
kubectl logs -l app=judge -n mcpeeker
```

#### ClickHouse write failures

```bash
# Check disk space
df -h /var/lib/clickhouse

# Verify connection
clickhouse-client --query "SELECT 1"

# Check correlator logs
kubectl logs -l app=correlator -n mcpeeker
```

## Performance

### Scale Targets

- **Endpoints**: 10,000 concurrent hosts
- **Event Rate**: 40 events/second sustained (100M/month)
- **Detection Latency**: ≤60 seconds end-to-end
- **API Response**: ≤2 seconds for queries
- **Judge Inference**: ≤400ms p95 with caching

### Optimization Tips

1. **ClickHouse**: Use materialized views for frequent aggregations
2. **NATS**: Increase stream retention for high-volume environments
3. **Judge**: Enable Redis caching (default: 1-hour TTL)
4. **Frontend**: Implement pagination for large detection lists

## Development

### Running Tests

```bash
# Backend tests
cd backend/scanner && go test ./...
cd backend/correlator && go test ./...
cd backend/judge && pytest
cd backend/registry-api && pytest

# Frontend tests
cd frontend && npm test

# Integration tests
cd tests/integration && pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Submit pull request

## Support

- **Documentation**: https://docs.mcpeeker.io
- **Issues**: https://github.com/ozlabs/mcpeeker/issues
- **Slack**: #mcpeeker on ozlabs.slack.com
- **Email**: support@mcpeeker.io

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- **Go**: High-performance scanning and correlation
- **Python/FastAPI**: Flexible API and LLM integration
- **React**: Modern, responsive UI
- **NATS JetStream**: Reliable event streaming
- **ClickHouse**: Fast analytics at scale
- **Claude**: AI-powered classification

---

**MCPeeker** - Secure MCP Lifecycle Management for Modern Organizations
