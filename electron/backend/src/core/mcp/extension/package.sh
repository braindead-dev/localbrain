#!/bin/bash
#
# LocalBrain Extension Packaging Script
# Creates a .mcpb bundle for Claude Desktop
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  LocalBrain Extension Packager${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../../../../../" && pwd )"
BACKEND_DIR="$PROJECT_ROOT/electron/backend"
EXTENSION_DIR="$SCRIPT_DIR"

echo -e "${GREEN}📂 Directories:${NC}"
echo "   Extension: $EXTENSION_DIR"
echo "   Backend:   $BACKEND_DIR"
echo

# Clean previous build
if [ -d "$EXTENSION_DIR/server" ]; then
    echo -e "${GREEN}🧹 Cleaning previous build...${NC}"
    rm -rf "$EXTENSION_DIR/server"
fi

if [ -f "$EXTENSION_DIR/localbrain.mcpb" ]; then
    rm "$EXTENSION_DIR/localbrain.mcpb"
fi

# Create server directory
echo -e "${GREEN}📁 Creating server directory...${NC}"
mkdir -p "$EXTENSION_DIR/server"

# Copy stdio_server.py
echo -e "${GREEN}📄 Copying stdio_server.py...${NC}"
cp "$BACKEND_DIR/src/core/mcp/stdio_server.py" "$EXTENSION_DIR/server/"

# Create minimal requirements.txt for the extension
echo -e "${GREEN}📋 Creating requirements.txt...${NC}"
cat > "$EXTENSION_DIR/server/requirements.txt" << EOF
# LocalBrain Extension Dependencies
mcp>=1.0.0
httpx>=0.28.0
python-dotenv>=1.0.0
EOF

# Copy README for the extension
echo -e "${GREEN}📝 Creating README.md...${NC}"
cat > "$EXTENSION_DIR/server/README.md" << EOF
# LocalBrain Extension Server

This is the stdio server component for the LocalBrain Claude Desktop extension.

## Requirements

- Python 3.10+
- LocalBrain Electron app running (auto-starts both services):
  - Daemon on http://127.0.0.1:8765
  - MCP FastAPI server on http://127.0.0.1:8766
- Vault path configured in ~/.localbrain/config.json

## Installation

Dependencies are automatically installed by Claude Desktop when the extension is loaded.

If you need to install manually:

\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Usage

This server is launched automatically by Claude Desktop. It acts as a bridge between
Claude's stdio-based MCP protocol and the LocalBrain MCP FastAPI server (port 8766),
which in turn forwards requests to the daemon (port 8765).

Do not run this directly - it's designed to be launched by Claude Desktop.
EOF

# Verify manifest.json exists
if [ ! -f "$EXTENSION_DIR/manifest.json" ]; then
    echo -e "${RED}❌ Error: manifest.json not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Validating manifest.json...${NC}"
if ! python3 -m json.tool "$EXTENSION_DIR/manifest.json" > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: manifest.json is not valid JSON!${NC}"
    exit 1
fi

# Create the .mcpb bundle (it's just a ZIP file with .mcpb extension)
echo -e "${GREEN}📦 Creating .mcpb bundle...${NC}"
cd "$EXTENSION_DIR"
zip -r localbrain.mcpb manifest.json server/ > /dev/null 2>&1

if [ -f "localbrain.mcpb" ]; then
    SIZE=$(du -h "localbrain.mcpb" | cut -f1)
    echo
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Success! Extension packaged${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    echo -e "${BLUE}📦 Package: ${NC}localbrain.mcpb ($SIZE)"
    echo -e "${BLUE}📍 Location:${NC} $EXTENSION_DIR/localbrain.mcpb"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Start LocalBrain Electron app (auto-starts both daemon and MCP server)"
    echo "     cd electron && npm run dev"
    echo "  2. Open Claude Desktop"
    echo "  3. Drag localbrain.mcpb into the Claude Desktop window"
    echo "  4. Accept the API key default (dev-key-local-only)"
    echo "  5. Enable the extension and start using it!"
    echo
else
    echo -e "${RED}❌ Error: Failed to create .mcpb bundle${NC}"
    exit 1
fi
