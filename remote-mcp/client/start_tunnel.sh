#!/bin/bash
# Start tunnel client for remote MCP access

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "LocalBrain Remote MCP Tunnel"
echo "=================================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure your credentials"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Load environment variables
source .env

# Check if credentials are configured
if [ "$USER_ID" == "your_unique_user_id_here" ] || [ "$REMOTE_API_KEY" == "lb_your_api_key_here" ]; then
    echo -e "${RED}❌ Error: Credentials not configured${NC}"
    echo "Please edit .env and add your USER_ID and REMOTE_API_KEY"
    exit 1
fi

echo -e "${YELLOW}🔍 Checking local MCP server...${NC}"

# Check if local MCP server is running
if curl -s -f http://127.0.0.1:8766/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Local MCP server is running${NC}"
else
    echo -e "${RED}❌ Local MCP server is not running${NC}"
    echo ""
    echo "Please start the MCP server first:"
    echo "  cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/electron/backend"
    echo "  python src/core/mcp/extension/start_servers.py"
    echo ""
    read -p "Do you want me to start it for you? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Starting MCP server...${NC}"
        cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/electron/backend
        python src/core/mcp/extension/start_servers.py &
        MCP_PID=$!
        sleep 5
        echo -e "${GREEN}✅ MCP server started (PID: $MCP_PID)${NC}"
        cd - > /dev/null
    else
        exit 1
    fi
fi

echo -e "${YELLOW}🔌 Starting tunnel client...${NC}"
echo ""

# Start the tunnel client
python3 mcp_tunnel_client.py

# Cleanup on exit
if [ ! -z "$MCP_PID" ]; then
    echo -e "${YELLOW}Stopping MCP server...${NC}"
    kill $MCP_PID 2>/dev/null
fi

echo -e "${GREEN}✅ Tunnel closed${NC}"
