#!/bin/bash
# Health Check Script for Iquitos EV Infrastructure

set -e

API_URL="${API_URL:-http://localhost:8000}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"

echo "=== Health Check Started ==="
echo "Date: $(date)"
echo ""

# Check API
echo "Checking API..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" || echo "000")
if [ "$API_RESPONSE" = "200" ]; then
    echo "✓ API is healthy (HTTP ${API_RESPONSE})"
    curl -s "${API_URL}/health" | python3 -m json.tool 2>/dev/null || true
else
    echo "✗ API is unhealthy (HTTP ${API_RESPONSE})"
fi
echo ""

# Check MongoDB
echo "Checking MongoDB..."
if mongosh --host "${MONGO_HOST}" --port "${MONGO_PORT}" --eval "db.adminCommand('ping')" --quiet 2>/dev/null; then
    echo "✓ MongoDB is healthy"
else
    echo "✗ MongoDB is unhealthy"
fi
echo ""

# Check Docker containers
echo "Checking Docker containers..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(fastapi|mongo|nginx)" || echo "No containers found"
echo ""

# Check disk space
echo "Checking disk space..."
df -h | grep -E "(Filesystem|/dev/)" | head -5
echo ""

# Check memory
echo "Checking memory..."
free -h 2>/dev/null || echo "Memory info not available"
echo ""

echo "=== Health Check Completed ==="
