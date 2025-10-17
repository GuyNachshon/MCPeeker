#!/bin/bash
# MCPeeker Quickstart Script
# Automated local development environment setup

set -e  # Exit on error

echo "======================================"
echo "  MCPeeker Quickstart Setup"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_info "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check Go
if ! command -v go &> /dev/null; then
    print_warn "Go is not installed. Scanner and Correlator services will not run."
    GO_INSTALLED=false
else
    print_info "Go version: $(go version)"
    GO_INSTALLED=true
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    print_warn "Python 3 is not installed. Backend services will not run."
    PYTHON_INSTALLED=false
else
    print_info "Python version: $(python3 --version)"
    PYTHON_INSTALLED=true
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    print_warn "Node.js is not installed. Frontend will not run."
    NODE_INSTALLED=false
else
    print_info "Node.js version: $(node --version)"
    NODE_INSTALLED=true
fi

echo ""
print_info "Starting infrastructure services..."

# Navigate to docker directory
cd infrastructure/docker

# Start infrastructure with Docker Compose
print_info "Starting NATS, ClickHouse, PostgreSQL, Redis, Prometheus, Grafana..."
docker-compose up -d

# Wait for services to be healthy
print_info "Waiting for services to be ready..."
sleep 10

# Check service health
print_info "Checking service health..."

services=("nats" "clickhouse" "postgres" "redis")
for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        print_info "✓ $service is running"
    else
        print_error "✗ $service failed to start"
    fi
done

cd ../..

echo ""
print_info "Infrastructure services are ready!"
echo ""
echo "Service URLs:"
echo "  - NATS: nats://localhost:4222 (monitoring: http://localhost:8222)"
echo "  - ClickHouse: http://localhost:8123 (native: localhost:9000)"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3001 (admin/admin)"
echo ""

# Initialize databases
print_info "Initializing databases..."

# ClickHouse initialization (tables already created via init script)
print_info "ClickHouse tables initialized"

# PostgreSQL migrations
if [ "$PYTHON_INSTALLED" = true ]; then
    print_info "Running PostgreSQL migrations..."
    cd backend/registry-api

    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    if [ ! -f ".installed" ]; then
        print_info "Installing Python dependencies..."
        pip install -q -r requirements.txt
        touch .installed
    fi

    print_info "Running Alembic migrations..."
    alembic upgrade head

    deactivate
    cd ../..
else
    print_warn "Skipping PostgreSQL migrations (Python not installed)"
fi

echo ""
print_info "Database initialization complete!"
echo ""

# Provide next steps
echo "======================================"
echo "  Setup Complete!"
echo "======================================"
echo ""
echo "Infrastructure is running. To start the application services:"
echo ""

if [ "$GO_INSTALLED" = true ]; then
    echo "1. Start Scanner (Terminal 1):"
    echo "   cd backend/scanner"
    echo "   go run cmd/scanner/main.go"
    echo ""
    echo "2. Start Correlator (Terminal 2):"
    echo "   cd backend/correlator"
    echo "   go run cmd/correlator/main.go"
    echo ""
fi

if [ "$PYTHON_INSTALLED" = true ]; then
    echo "3. Start Signature Engine (Terminal 3):"
    echo "   cd backend/signature-engine"
    echo "   pip install -r requirements.txt"
    echo "   python src/main.py"
    echo ""
    echo "4. Start Judge Service (Terminal 4):"
    echo "   cd backend/judge"
    echo "   pip install -r requirements.txt"
    echo "   export ANTHROPIC_API_KEY=your_key_here"
    echo "   uvicorn src.api.main:app --reload --port 8003"
    echo ""
    echo "5. Start Registry API (Terminal 5):"
    echo "   cd backend/registry-api"
    echo "   source venv/bin/activate"
    echo "   uvicorn src.main:app --reload --port 8000"
    echo ""
fi

if [ "$NODE_INSTALLED" = true ]; then
    echo "6. Start Frontend (Terminal 6):"
    echo "   cd frontend"
    echo "   npm install"
    echo "   npm run dev"
    echo ""
    echo "Then access the UI at: http://localhost:5173"
    echo ""
fi

echo "To stop infrastructure services:"
echo "   cd infrastructure/docker && docker-compose down"
echo ""

print_info "For more details, see README.md"
echo ""

# Create .env template if it doesn't exist
if [ ! -f ".env.example" ]; then
    print_info "Creating .env.example template..."
    cat > .env.example << 'EOF'
# MCPeeker Environment Variables

# Anthropic API Key (required for Judge service)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# NATS Configuration
NATS_URL=nats://localhost:4222

# ClickHouse Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_DB=mcpeeker
CLICKHOUSE_USER=mcpeeker
CLICKHOUSE_PASSWORD=mcpeeker_dev

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mcpeeker_registry
POSTGRES_USER=mcpeeker
POSTGRES_PASSWORD=mcpeeker_dev

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Frontend Configuration
VITE_API_BASE_URL=http://localhost:8000

# SMTP Configuration (for notifications)
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@mcpeeker.local

# Slack Webhook (optional)
SLACK_WEBHOOK_URL=

# PagerDuty (optional)
PAGERDUTY_API_KEY=
PAGERDUTY_ROUTING_KEY=
EOF
    print_info "Created .env.example - copy to .env and fill in values"
fi

print_info "Quickstart complete! 🎉"
