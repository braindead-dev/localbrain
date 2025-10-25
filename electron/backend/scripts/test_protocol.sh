#!/bin/bash
#
# Test script for LocalBrain protocol system
#

set -e

echo "=========================================="
echo "LocalBrain Protocol System Test"
echo "=========================================="
echo ""

# Check if daemon is running
echo "1. Checking daemon status..."
if curl -s http://localhost:8765/health > /dev/null 2>&1; then
    echo "   ✅ Daemon is running"
else
    echo "   ❌ Daemon is not running"
    echo "   Start it with: python src/tray.py"
    exit 1
fi

echo ""
echo "2. Testing ingestion via API..."
response=$(curl -s -X POST http://localhost:8765/protocol/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Test ingestion from automated test script. This should create a note in the vault.",
    "platform": "TestScript",
    "timestamp": "2024-10-25T12:00:00Z"
  }')

if echo "$response" | grep -q "success"; then
    echo "   ✅ API ingestion successful"
    echo "   Response: $response"
else
    echo "   ❌ API ingestion failed"
    echo "   Response: $response"
    exit 1
fi

echo ""
echo "3. Testing protocol URL..."
echo "   Opening: localbrain://ingest?text=Test%20from%20URL%20protocol&platform=URLTest"

open "localbrain://ingest?text=Test%20from%20URL%20protocol&platform=URLTest"

echo "   ✅ Protocol URL sent to system"
echo "   Check logs: tail -f /tmp/localbrain-protocol.log"

echo ""
echo "=========================================="
echo "All tests passed! ✅"
echo "=========================================="
echo ""
echo "Check your vault for the ingested content:"
echo "  ~/Documents/GitHub/localbrain/my-vault/"
echo ""
