#!/bin/bash
# Start MCP Tunnel Client

set -e

cd "$(dirname "$0")"

echo "=========================================="
echo "  LocalBrain MCP Tunnel Client"
echo "=========================================="
echo ""

# Check .env exists
if [ ! -f .env ]; then
    echo "❌ No .env file found!"
    echo ""
    echo "Run setup first:"
    echo "  cp .env.example .env"
    echo "  nano .env  # Fill in USER_ID and REMOTE_API_KEY"
    echo ""
    exit 1
fi

# Check local MCP server
echo "Checking local MCP server..."
if ! curl -s http://127.0.0.1:8766/health > /dev/null 2>&1; then
    echo "❌ Local MCP server not running!"
    echo ""
    echo "Start it first:"
    echo "  cd /Users/henry/Documents/GitHub/localbrain/electron/backend"
    echo "  python src/core/mcp/extension/start_servers.py"
    echo ""
    exit 1
fi

echo "✅ Local MCP server is running"
echo ""

# Start tunnel
/Users/henry/miniconda3/bin/python mcp_tunnel_client.py
