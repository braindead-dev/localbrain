#!/bin/bash
# Start Remote MCP Bridge Server
#
# This script starts the public bridge server that accepts tunnel connections
# and forwards requests to local MCP servers.
#
# Usage:
#   ./start_bridge.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "  LocalBrain Remote MCP Bridge Server"
echo "=================================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "IMPORTANT: Edit .env and set BRIDGE_SECRET before deploying!"
    echo ""
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

# Check dependencies
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

echo "🚀 Starting bridge server..."
echo ""

# Start bridge server
python3 bridge_server.py
