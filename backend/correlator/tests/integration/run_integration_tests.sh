#!/usr/bin/env bash
# Integration Test Orchestration Script
# Purpose: Run integration tests with Docker Compose environment
# Usage: ./run_integration_tests.sh

set -e  # Exit on error
set -u  # Exit on undefined variable

echo "========================================="
echo "MCPeeker Integration Test Suite"
echo "========================================="

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Cleaning up Docker Compose environment...${NC}"
    docker-compose -f docker-compose.test.yml down -v > /dev/null 2>&1 || true
}

# Trap cleanup on script exit
trap cleanup EXIT

# Step 1: Start Docker Compose services
echo ""
echo -e "${YELLOW}Step 1: Starting Docker Compose services...${NC}"
docker-compose -f docker-compose.test.yml up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to start Docker Compose services${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Services started${NC}"

# Step 2: Wait for services to be healthy
echo ""
echo -e "${YELLOW}Step 2: Waiting for services to be ready...${NC}"
echo "This may take up to 30 seconds..."

# Wait for PostgreSQL
MAX_ATTEMPTS=15
ATTEMPT=0
until docker-compose -f docker-compose.test.yml exec -T postgres pg_isready -U test > /dev/null 2>&1; do
    ATTEMPT=$((ATTEMPT+1))
    if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
        echo -e "${RED}PostgreSQL did not become ready in time${NC}"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""
echo -e "${GREEN}✓ PostgreSQL ready${NC}"

# Wait for NATS
sleep 5  # Additional wait for NATS JetStream initialization
echo -e "${GREEN}✓ NATS ready${NC}"

# Step 3: Seed database
echo ""
echo -e "${YELLOW}Step 3: Seeding database...${NC}"
docker-compose -f docker-compose.test.yml exec -T postgres \
    psql -U test -d mcpeeker_test -f /fixtures/seed.sql > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to seed database${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Database seeded${NC}"

# Step 4: Run integration tests
echo ""
echo -e "${YELLOW}Step 4: Running integration tests...${NC}"
START_TIME=$(date +%s)

# Run tests with verbose output
go test -v -timeout 30s ./... 2>&1

TEST_EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================="
    echo -e "✓ All integration tests passed!"
    echo -e "Duration: ${DURATION}s"
    echo -e "=========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================="
    echo -e "✗ Integration tests failed"
    echo -e "Duration: ${DURATION}s"
    echo -e "=========================================${NC}"
    exit 1
fi
