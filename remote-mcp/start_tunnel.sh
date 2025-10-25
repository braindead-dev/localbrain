#!/bin/bash
# Start Remote MCP Tunnel Client
#
# This script starts the tunnel client that connects your local MCP server
# to the remote bridge, enabling external access.
#
# Usage:
#   ./start_tunnel.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "  LocalBrain Remote MCP Tunnel Client"
echo "=================================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "IMPORTANT: Edit .env and configure:"
    echo "  - USER_ID (generate with: python3 -c \"import uuid; print(str(uuid.uuid4()))\")"
    echo "  - REMOTE_API_KEY (generate with: python3 -c \"import secrets; print('lb_' + secrets.token_urlsafe(32))\")"
    echo "  - BRIDGE_URL (if using remote bridge)"
    echo ""
    exit 1
fi

# Load environment
source .env

# Validate required variables
if [ -z "$USER_ID" ]; then
    echo "❌ USER_ID not set in .env"
    echo ""
    echo "Generate one with:"
    echo "  python3 -c \"import uuid; print(str(uuid.uuid4()))\""
    echo ""
    exit 1
fi

if [ -z "$REMOTE_API_KEY" ]; then
    echo "❌ REMOTE_API_KEY not set in .env"
    echo ""
    echo "Generate one with:"
    echo "  python3 -c \"import secrets; print('lb_' + secrets.token_urlsafe(32))\""
    echo ""
    exit 1
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

# Check dependencies
if ! python3 -c "import websockets" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

echo "🚀 Starting tunnel client..."
echo ""

# Start tunnel client
python3 tunnel_client.py
