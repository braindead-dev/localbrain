#!/bin/bash
#
# Test natural language search
# Usage: ./test_search.sh "What was my Meta offer?"
#

set -e

QUERY="${1:-What was my Meta offer?}"

echo "=========================================="
echo "LocalBrain Natural Language Search Test"
echo "=========================================="
echo ""
echo "Query: $QUERY"
echo ""

# Check if daemon is running
echo "1. Checking daemon..."
if curl -s http://localhost:8765/health > /dev/null 2>&1; then
    echo "   ✅ Daemon is running"
else
    echo "   ❌ Daemon is not running"
    echo "   Start it with: npm run dev (from electron/)"
    exit 1
fi

echo ""
echo "2. Running search..."

# Call search API
response=$(curl -s -X POST http://localhost:8765/protocol/search \
  -H "Content-Type: application/json" \
  -d "{\"q\": \"$QUERY\"}")

echo ""
echo "3. Response:"
echo "$response" | python3 -m json.tool

echo ""
echo "=========================================="
echo ""

# Check if successful
if echo "$response" | grep -q '"success": true'; then
    echo "✅ Search successful!"
    echo ""
    echo "Answer:"
    echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['answer'])"
else
    echo "❌ Search failed"
    echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error', 'Unknown error'))"
    exit 1
fi

echo ""
echo "=========================================="
echo ""
