# Quickstart Guide: MCPeeker Local Development

**Feature Branch**: `001-mcp-detection-platform`
**Phase**: 1 (Design - Local Setup)
**Date**: 2025-10-16

## Overview

This guide helps developers set up a local MCPeeker environment for testing and development. The local setup uses Docker Compose to run all dependencies (NATS, ClickHouse, PostgreSQL) and provides step-by-step instructions for running backend services and the frontend UI.

**Constitution Compliance**:
- **Privacy by Design**: Local environment uses test certificates for mTLS (not production CA)
- **YAML Configuration**: All services configured via YAML files in `infrastructure/configs/`
- **Observability**: Prometheus and Grafana included for local metrics visualization

---

## Prerequisites

Ensure you have the following installed on your development machine:

### Required Software

- **Docker Desktop** 24.0+ (with Docker Compose)
  - Download: https://www.docker.com/products/docker-desktop
  - Verify: `docker --version` and `docker compose version`

- **Go** 1.23+
  - Download: https://go.dev/dl/
  - Verify: `go version`

- **Python** 3.11+
  - Download: https://www.python.org/downloads/
  - Verify: `python3 --version`
  - Package manager: `pip3 --version`

- **Node.js** 18+ and npm
  - Download: https://nodejs.org/
  - Verify: `node --version` and `npm --version`

### Optional but Recommended

- **Make** (for convenient build commands)
  - macOS: Pre-installed via Xcode Command Line Tools
  - Linux: `sudo apt-get install build-essential`
  - Windows: Install via Chocolatey or WSL

- **Git** (for cloning repository and version control)
  - Verify: `git --version`

### System Requirements

- **Memory**: 8GB RAM minimum (16GB recommended for running all services)
- **Disk**: 5GB free space for Docker images and local data
- **Ports**: Ensure the following ports are available:
  - 4222 (NATS), 8123 (ClickHouse HTTP), 9000 (ClickHouse Native), 5432 (PostgreSQL)
  - 8000 (Registry API), 8001 (Findings API), 8002 (Judge service)
  - 3000 (Frontend dev server), 9090 (Prometheus), 3001 (Grafana)

---

## Quick Start (5 Minutes)

For the impatient, here's the fastest path to a running system:

```bash
# Clone repository
git clone https://github.com/example/mcpeeker.git
cd mcpeeker

# Start infrastructure (NATS, ClickHouse, PostgreSQL)
docker compose -f infrastructure/docker/docker-compose.yml up -d

# Wait for services to be ready (30 seconds)
sleep 30

# Run database migrations
make db-migrate

# Start all backend services (in separate terminals or use tmux)
make run-all

# Start frontend (in another terminal)
cd frontend
npm install
npm run dev

# Open browser to http://localhost:3000
```

---

## Detailed Setup Instructions

### Step 1: Clone Repository

```bash
git clone https://github.com/example/mcpeeker.git
cd mcpeeker
```

### Step 2: Start Infrastructure Services

Start NATS, ClickHouse, PostgreSQL, Prometheus, and Grafana using Docker Compose:

```bash
cd infrastructure/docker
docker compose up -d
```

**What this does**:
- Starts NATS JetStream cluster (3 nodes for HA testing)
- Starts ClickHouse server with pre-configured retention policies
- Starts PostgreSQL with RBAC schema
- Starts Prometheus for metrics collection
- Starts Grafana with pre-configured dashboards (admin/admin credentials)

**Verify services are running**:
```bash
docker compose ps
```

You should see all services in "Up" state:
```
NAME                    STATUS              PORTS
nats-1                  Up                  0.0.0.0:4222->4222/tcp
clickhouse              Up                  0.0.0.0:8123->8123/tcp, 0.0.0.0:9000->9000/tcp
postgres                Up                  0.0.0.0:5432->5432/tcp
prometheus              Up                  0.0.0.0:9090->9090/tcp
grafana                 Up                  0.0.0.0:3001->3000/tcp
```

**Wait for services to initialize** (approximately 30 seconds):
```bash
# Check ClickHouse is ready
curl http://localhost:8123/ping
# Expected output: Ok.

# Check PostgreSQL is ready
docker compose exec postgres pg_isready
# Expected output: /var/run/postgresql:5432 - accepting connections

# Check NATS is ready
docker compose exec nats-1 nats account info
```

### Step 3: Initialize Databases

#### 3.1 Create ClickHouse Tables

```bash
# Return to repository root
cd ../..

# Run ClickHouse migrations
docker compose -f infrastructure/docker/docker-compose.yml exec clickhouse clickhouse-client --queries-file /docker-entrypoint-initdb.d/init_tables.sql
```

Or use the Makefile shortcut:
```bash
make clickhouse-init
```

**What this creates**:
- `detections` table with MergeTree engine (data-model.md)
- `feedback_records` table
- `aggregated_metrics` materialized view
- Proper partitioning and TTL policies

**Verify tables exist**:
```bash
docker compose -f infrastructure/docker/docker-compose.yml exec clickhouse clickhouse-client --query "SHOW TABLES"
```

Expected output:
```
aggregated_metrics
detections
feedback_records
```

#### 3.2 Create PostgreSQL Schema

```bash
# Run PostgreSQL migrations (using golang-migrate)
make postgres-migrate
```

Or manually:
```bash
cd backend/registry-api
python3 -m alembic upgrade head
```

**What this creates**:
- `users` table with RBAC roles
- `registry_entries` table with composite identifier
- `notification_preferences` table
- `audit_logs` table with signature fields
- Foreign key constraints and indexes

**Verify tables exist**:
```bash
docker compose -f infrastructure/docker/docker-compose.yml exec postgres psql -U mcpeeker -d mcpeeker -c "\dt"
```

Expected output:
```
             List of relations
 Schema |          Name          | Type  |  Owner
--------+------------------------+-------+----------
 public | audit_logs             | table | mcpeeker
 public | notification_preferences| table | mcpeeker
 public | registry_entries       | table | mcpeeker
 public | users                  | table | mcpeeker
```

#### 3.3 Seed Test Data (Optional)

Load sample users and registry entries for testing:

```bash
make seed-data
```

This creates:
- Test users: `developer@example.com`, `analyst@example.com`, `admin@example.com` (all password: `password123`)
- Sample authorized MCP entries
- Test notification preferences

### Step 4: Generate mTLS Certificates (Development Only)

Generate self-signed certificates for inter-service mTLS (FR-010):

```bash
make generate-certs
```

**What this does**:
- Creates root CA certificate (valid 10 years)
- Generates service certificates for scanner, correlator, judge, registry-api (valid 90 days)
- Stores certificates in `infrastructure/certs/` (gitignored)

**Note**: Production deployments use cert-manager in Kubernetes. These certs are for local development only.

### Step 5: Configure Services

Copy example configuration files:

```bash
# Copy all example configs
cp infrastructure/configs/global.yaml.example infrastructure/configs/global.yaml
cp infrastructure/configs/scanner.yaml.example infrastructure/configs/scanner.yaml
cp infrastructure/configs/judge.yaml.example infrastructure/configs/judge.yaml
cp infrastructure/configs/correlator.yaml.example infrastructure/configs/correlator.yaml
```

**Edit configurations** (optional, defaults work for local dev):

**`global.yaml`**:
- NATS connection: `nats://localhost:4222`
- ClickHouse endpoint: `http://localhost:8123`
- PostgreSQL connection: `postgresql://mcpeeker:password@localhost:5432/mcpeeker`

**`scanner.yaml`**:
- Scan interval: `12h` (can reduce to `5m` for faster local testing)
- Filesystem roots: `["/tmp/mcp-test"]` (local test directory)

**`judge.yaml`**:
- Model path: `./models/distilbert-mcp-classifier` (downloaded separately)
- Inference timeout: `400ms`

### Step 6: Run Backend Services

Open **5 separate terminal windows** (or use tmux/screen) for backend services:

#### Terminal 1: Scanner Service (Go)

```bash
cd backend/scanner
go mod download
go run cmd/scanner/main.go --config ../../infrastructure/configs/scanner.yaml
```

**Expected output**:
```
2025-10-16T10:00:00Z INFO  Starting endpoint scanner service
2025-10-16T10:00:00Z INFO  Configuration loaded from scanner.yaml
2025-10-16T10:00:00Z INFO  Connected to NATS: nats://localhost:4222
2025-10-16T10:00:00Z INFO  Starting file scanner (interval: 5m)
2025-10-16T10:00:00Z INFO  Scanning filesystem roots: [/tmp/mcp-test]
```

#### Terminal 2: Signature Engine (Python)

```bash
cd backend/signature-engine
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/main.py --config ../../infrastructure/configs/signature-engine.yaml
```

**Expected output**:
```
2025-10-16 10:00:01 INFO     Starting signature engine service
2025-10-16 10:00:01 INFO     Loaded 42 Knostik signatures
2025-10-16 10:00:01 INFO     Subscribed to NATS streams: endpoint.events, network.events
```

#### Terminal 3: Correlator Service (Go)

```bash
cd backend/correlator
go run cmd/correlator/main.go --config ../../infrastructure/configs/correlator.yaml
```

**Expected output**:
```
2025-10-16T10:00:02Z INFO  Starting correlator service
2025-10-16T10:00:02Z INFO  Connected to ClickHouse: http://localhost:8123
2025-10-16T10:00:02Z INFO  Connected to PostgreSQL (registry lookup)
2025-10-16T10:00:02Z INFO  Subscribed to enriched events (5-minute dedup window)
```

#### Terminal 4: Judge Service (Python)

```bash
cd backend/judge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Download pre-trained DistilBERT model (if not already present)
python scripts/download_model.py

# Start Judge service
uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8002 (Press CTRL+C to quit)
INFO:     Started reloader process [12345]
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Loaded DistilBERT model: distilbert-mcp-classifier-v3
```

#### Terminal 5: Registry API (Python FastAPI)

```bash
cd backend/registry-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
INFO:     Registry API ready (RBAC enabled)
INFO:     Swagger UI: http://localhost:8000/docs
```

**Verify all services are healthy**:
```bash
# Check Registry API
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Check Judge service
curl http://localhost:8002/health
# Expected: {"status": "healthy", "model_loaded": true}
```

### Step 7: Run Frontend (React)

In a **6th terminal window**:

```bash
cd frontend
npm install
npm run dev
```

**Expected output**:
```
VITE v5.0.0  ready in 342 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.1.100:3000/
  ➜  press h to show help
```

**Open browser**: Navigate to http://localhost:3000

**Login with test credentials**:
- Email: `analyst@example.com`
- Password: `password123`

You should see the MCPeeker dashboard with:
- Detection feed (empty initially)
- Score distribution chart
- Active hosts count

---

## Sample Test Workflow

Now that all services are running, test the end-to-end detection pipeline:

### 1. Trigger Endpoint Detection

Create a fake MCP manifest file in the scanned directory:

```bash
# Create test directory
mkdir -p /tmp/mcp-test/.mcp

# Create manifest file
cat > /tmp/mcp-test/.mcp/manifest.json <<EOF
{
  "name": "test-mcp-server",
  "version": "1.0.0",
  "protocol": "mcp/1.0",
  "description": "Test MCP server for local development",
  "server": {
    "command": "node",
    "args": ["/usr/local/bin/mcp-server"],
    "port": 3000
  }
}
EOF
```

**Wait for scanner to run** (5 minutes if you set interval to `5m`, or manually trigger):

```bash
# Manually trigger scan (if scanner supports SIGHUP reload)
pkill -HUP scanner
```

### 2. View Detection in UI

Within 60 seconds (FR-011), you should see:

1. **Scanner** detects manifest file → publishes `endpoint.events` message
2. **Signature Engine** enriches event → republishes to correlator
3. **Correlator** scores detection (score ~11 for manifest file) → writes to ClickHouse
4. **Frontend** polls Findings API → displays detection in feed

**In the UI**:
- Navigate to **Detections** tab
- Filter: Score ≥9, Unregistered
- You should see new detection with:
  - Host: `localhost` or your machine hostname
  - Port: 3000
  - Score: 11 (endpoint evidence only)
  - Classification: **Unauthorized**
  - Evidence: Endpoint (manifest file snippet)

### 3. Register the MCP (Developer Workflow)

1. Click on the detection to open investigation panel
2. Click **"Confirm Ownership"** button
3. Fill registration form:
   - Purpose: "Local development test server"
   - Team: "engineering"
   - Expiration: 30 days from now (auto-populated)
4. Click **"Register MCP"**

**Expected result**:
- Registry entry created in PostgreSQL
- Future detections of this MCP will match registry (score reduced by 6 points)
- Classification changes from "Unauthorized" to "Authorized"

### 4. Verify Registry Match

Trigger another scan (or wait for next scan cycle):

```bash
# Touch the manifest to update timestamp
touch /tmp/mcp-test/.mcp/manifest.json
```

**Expected result**:
- New detection created with same composite_id
- Score: 5 (11 - 6 registry penalty)
- Classification: **Suspect** (score 5-8 range)
- Registry matched: ✓

### 5. Submit Feedback (Analyst Workflow)

Login as analyst (`analyst@example.com` / `password123`):

1. Navigate to **Detections** tab
2. Open the detection
3. Click **"Mark as True Positive"**
4. Add notes: "Confirmed with developer - authorized test server"
5. Submit feedback

**Expected result**:
- Feedback record created in ClickHouse
- Feedback displayed in detection history
- False positive rate metrics updated

---

## Observability and Monitoring

### Prometheus Metrics

Open http://localhost:9090 to access Prometheus UI.

**Example queries**:

```promql
# Detection event rate
rate(mcpeeker_events_published_total[5m])

# Average detection score
avg(mcpeeker_detection_score)

# Judge inference latency (p95)
histogram_quantile(0.95, rate(mcpeeker_judge_inference_latency_seconds_bucket[5m]))

# ClickHouse write errors
rate(mcpeeker_clickhouse_write_errors_total[5m])
```

### Grafana Dashboards

Open http://localhost:3001 (login: `admin` / `admin`)

Pre-configured dashboards:
1. **Detection Overview**: Real-time detection feed, score distribution, classification breakdown
2. **Pipeline Health**: Service health checks, NATS message rates, ClickHouse query latency
3. **Judge Performance**: Inference latency, cache hit rate, classification accuracy
4. **RBAC Audit**: User activity, registry changes, API request rates

### Logs

All services log to stdout/stderr. View logs with Docker Compose:

```bash
# View all logs
docker compose -f infrastructure/docker/docker-compose.yml logs -f

# View specific service logs
docker compose -f infrastructure/docker/docker-compose.yml logs -f nats-1
docker compose -f infrastructure/docker/docker-compose.yml logs -f clickhouse
docker compose -f infrastructure/docker/docker-compose.yml logs -f postgres
```

Backend service logs (running in terminals):
- Scanner: `backend/scanner/logs/scanner.log` (if configured)
- Correlator: `backend/correlator/logs/correlator.log`
- Judge: stdout (uvicorn logs)
- Registry API: stdout (FastAPI logs)

### NATS Monitoring

Use NATS CLI to inspect streams and consumers:

```bash
# List all streams
docker compose -f infrastructure/docker/docker-compose.yml exec nats-1 nats stream ls

# View endpoint.events stream details
docker compose -f infrastructure/docker/docker-compose.yml exec nats-1 nats stream info endpoint.events

# View correlator consumer lag
docker compose -f infrastructure/docker/docker-compose.yml exec nats-1 nats consumer info endpoint.events correlator-endpoint-consumer
```

---

## Troubleshooting

### Issue: Services can't connect to NATS

**Symptoms**: Error logs: `failed to connect to NATS: connection refused`

**Solution**:
1. Verify NATS is running: `docker compose ps nats-1`
2. Check NATS port is accessible: `nc -zv localhost 4222`
3. Restart NATS: `docker compose restart nats-1`

### Issue: ClickHouse tables not created

**Symptoms**: Error logs: `Table detections doesn't exist`

**Solution**:
1. Run migrations manually: `make clickhouse-init`
2. Verify tables: `docker compose exec clickhouse clickhouse-client --query "SHOW TABLES"`
3. Check migration script: `infrastructure/docker/clickhouse/init_tables.sql`

### Issue: Frontend shows "API connection failed"

**Symptoms**: UI displays error banner: "Unable to connect to Registry API"

**Solution**:
1. Verify Registry API is running: `curl http://localhost:8000/health`
2. Check browser console for CORS errors (if running on different port)
3. Update frontend `.env.local` with correct API URL:
   ```
   VITE_REGISTRY_API_URL=http://localhost:8000/api/v1
   VITE_FINDINGS_API_URL=http://localhost:8000/api/v1
   ```

### Issue: Judge service fails to load model

**Symptoms**: Error: `FileNotFoundError: Model not found at ./models/distilbert-mcp-classifier`

**Solution**:
1. Download model: `cd backend/judge && python scripts/download_model.py`
2. Or use mock Judge (for testing without model):
   ```bash
   export JUDGE_MOCK_MODE=true
   uvicorn src.api.main:app --host 0.0.0.0 --port 8002
   ```

### Issue: Scanner doesn't detect manifest file

**Symptoms**: No detections appear after creating test manifest

**Solution**:
1. Verify scanner is scanning correct directory:
   - Check `scanner.yaml`: `filesystem_roots: ["/tmp/mcp-test"]`
2. Manually trigger scan: `pkill -HUP scanner` (if supported)
3. Check scanner logs for errors
4. Verify file permissions: `ls -la /tmp/mcp-test/.mcp/manifest.json`

### Issue: Port conflicts

**Symptoms**: Error: `bind: address already in use`

**Solution**:
1. Find conflicting process: `lsof -i :8000` (replace 8000 with conflicting port)
2. Kill process: `kill -9 <PID>`
3. Or change port in service config and restart

---

## Makefile Commands Reference

The repository includes a Makefile with convenient shortcuts:

```bash
# Infrastructure
make docker-up              # Start Docker Compose services
make docker-down            # Stop Docker Compose services
make docker-logs            # Tail all Docker logs

# Database
make clickhouse-init        # Create ClickHouse tables
make postgres-migrate       # Run PostgreSQL migrations
make seed-data              # Load test data

# Certificates
make generate-certs         # Generate mTLS certificates (dev only)

# Backend
make run-scanner            # Run scanner service
make run-correlator         # Run correlator service
make run-judge              # Run Judge service
make run-registry-api       # Run Registry API
make run-all                # Run all backend services (requires tmux)

# Frontend
make run-frontend           # Run frontend dev server

# Testing
make test-unit              # Run unit tests (Go + Python)
make test-integration       # Run integration tests (Docker Compose)
make test-contract          # Run JSON Schema validation tests

# Cleanup
make clean                  # Stop services and remove data volumes
make clean-certs            # Remove generated certificates
```

---

## Next Steps

After completing this quickstart:

1. **Explore the UI**: Navigate through Dashboard, Detections, Registry, and Settings pages
2. **Trigger network detections**: Use Zeek/Suricata signatures (requires network IDS setup)
3. **Test RBAC**: Login as different roles (developer, analyst, admin) to see permission differences
4. **Customize configurations**: Edit YAML files in `infrastructure/configs/` to test different detection thresholds
5. **Review API contracts**: Visit http://localhost:8000/docs (Registry API Swagger UI)
6. **Run tests**: Execute `make test-integration` to verify end-to-end workflows

---

## Additional Resources

- **Architecture Docs**: `/docs/architecture.md`
- **API Contracts**: `/specs/001-mcp-detection-platform/contracts/`
- **Data Model**: `/specs/001-mcp-detection-platform/data-model.md`
- **Research**: `/specs/001-mcp-detection-platform/research.md`
- **Constitution**: `/.specify/memory/constitution.md`

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/example/mcpeeker/issues
- Slack: #mcpeeker-dev channel
- Email: mcpeeker-team@example.com

**Happy hacking!**
