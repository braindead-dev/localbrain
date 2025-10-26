#!/bin/bash
# Quick deployment script for MCP-compliant bridge

set -e

SERVER="mcpuser@146.190.120.44"
REMOTE_DIR="~/localbrain/remote-mcp"

echo "=========================================="
echo "Deploying MCP-Compliant Bridge"
echo "=========================================="
echo ""

# Upload new server
echo "📤 Uploading server files..."
scp server/mcp_http_server.py $SERVER:$REMOTE_DIR/
scp server/.env.example $SERVER:$REMOTE_DIR/ 2>/dev/null || echo "  (no .env.example)"

echo ""
echo "🔄 Updating systemd service..."
ssh $SERVER << 'EOF'
cd ~/localbrain/remote-mcp

# Stop old service
sudo systemctl stop mcp-bridge 2>/dev/null || true

# Update service file
sudo tee /etc/systemd/system/mcp-bridge.service > /dev/null << 'SERVICE'
[Unit]
Description=LocalBrain MCP-Compliant Bridge
After=network.target

[Service]
Type=simple
User=mcpuser
WorkingDirectory=/home/mcpuser/localbrain/remote-mcp
Environment="PATH=/home/mcpuser/localbrain/remote-mcp/venv/bin"
ExecStart=/home/mcpuser/localbrain/remote-mcp/venv/bin/python mcp_http_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable mcp-bridge
sudo systemctl start mcp-bridge

echo ""
echo "✅ Service started!"
echo ""
echo "Checking status..."
sleep 2
sudo systemctl status mcp-bridge --no-pager -l
EOF

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Test with:"
echo "  curl http://146.190.120.44:8767/health"
echo ""
echo "View logs:"
echo "  ssh $SERVER sudo journalctl -u mcp-bridge -f"
echo ""
