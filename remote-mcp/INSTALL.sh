#!/bin/bash
# Complete installation script to run ON THE SERVER
# Copy this entire script and run it after SSHing into the server

echo "=========================================="
echo "Installing MCP Bridge Server"
echo "=========================================="

# Navigate to home
cd ~

# Create directories
echo "📁 Creating directories..."
mkdir -p ~/localbrain/remote-mcp/server
cd ~/localbrain/remote-mcp

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install aiohttp==3.9.1 aiohttp-cors==0.7.0 python-dotenv==1.0.0

echo ""
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your API key:"
echo "   cd ~/localbrain/remote-mcp/server"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "2. Test the server:"
echo "   source ~/localbrain/remote-mcp/venv/bin/activate"
echo "   python ~/localbrain/remote-mcp/server/mcp_http_server.py"
echo ""
