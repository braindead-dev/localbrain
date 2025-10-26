#!/bin/bash
# Run this ON THE SERVER to fix port conflict and permissions

echo "🔍 Finding process using port 8767..."
PORT_PID=$(sudo lsof -ti:8767)

if [ ! -z "$PORT_PID" ]; then
    echo "⚠️  Port 8767 is being used by process: $PORT_PID"
    echo "🛑 Stopping it..."
    sudo kill -9 $PORT_PID
    echo "✅ Process killed"
else
    echo "✅ Port 8767 is free"
fi

echo ""
echo "🔧 Fixing permissions..."
sudo chown -R mcpuser:mcpuser ~/localbrain/remote-mcp
echo "✅ Permissions fixed"

echo ""
echo "📝 Creating .env file..."
cd ~/localbrain/remote-mcp/server
cat > .env << 'EOF'
# Server Configuration
PORT=8767
HOST=0.0.0.0

# Security
API_KEY_PREFIX=lb_

# Timeouts (in seconds)
SESSION_TIMEOUT=3600
TUNNEL_TIMEOUT=300
REQUEST_TIMEOUT=30

# API Keys - CHANGE THIS!
API_KEY_PRANAV=lb_test_key_123
EOF

echo "✅ .env file created"
echo ""
echo "⚠️  IMPORTANT: Edit .env and change the API key!"
echo "   nano .env"
echo ""
echo "Then test the server:"
echo "   source ~/localbrain/remote-mcp/venv/bin/activate"
echo "   python ~/localbrain/remote-mcp/server/mcp_http_server.py"
