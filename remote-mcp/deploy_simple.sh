#!/bin/bash
# Simple deployment script - just uploads files
# Run setup commands manually on server

set -e

SERVER="mcpuser@146.190.120.44"

echo "=========================================="
echo "Uploading MCP Bridge Server Files"
echo "=========================================="
echo ""

# Check if server files exist
if [ ! -f "server/mcp_http_server.py" ]; then
    echo "❌ Error: server/mcp_http_server.py not found"
    exit 1
fi

echo "📤 Uploading files to server..."
echo ""

# Create directory first
ssh $SERVER "mkdir -p ~/localbrain/remote-mcp/server"

# Upload files
scp server/mcp_http_server.py $SERVER:~/localbrain/remote-mcp/server/
scp server/.env.example $SERVER:~/localbrain/remote-mcp/server/
scp server/README.md $SERVER:~/localbrain/remote-mcp/server/

echo ""
echo "=========================================="
echo "✅ Files Uploaded Successfully!"
echo "=========================================="
echo ""
echo "Next steps (run these ON THE SERVER):"
echo ""
echo "1. SSH into server:"
echo "   ssh $SERVER"
echo ""
echo "2. Setup Python environment:"
echo "   cd ~/localbrain/remote-mcp"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install aiohttp aiohttp-cors python-dotenv"
echo ""
echo "3. Configure your API key:"
echo "   cd server"
echo "   cp .env.example .env"
echo "   nano .env"
echo "   # Add: API_KEY_PRANAV=lb_your_key_here"
echo ""
echo "4. Test it manually first:"
echo "   cd ~/localbrain/remote-mcp/server"
echo "   source ../venv/bin/activate"
echo "   python mcp_http_server.py"
echo ""
echo "5. Then setup as service (see manual_deploy.md)"
echo ""
