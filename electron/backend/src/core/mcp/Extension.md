# LocalBrain Claude Desktop Extension

Official guide for creating and installing the LocalBrain extension for Claude Desktop using the `.mcpb` format.

## Overview

LocalBrain provides Claude Desktop with direct access to your personal knowledge vault through the Model Context Protocol (MCP). This extension implements the official `.mcpb` format for seamless integration.

### Architecture

The system uses a **two-component architecture**:

1. **FastAPI Server** (`server.py`) - Main REST API server that must run in the background
2. **Stdio Wrapper** (`stdio_server.py`) - MCP protocol adapter that Claude Desktop launches
3. **Extension Package** (`.mcpb`) - Bundle containing the stdio wrapper and configuration

```
Claude Desktop
      ↓ (stdio/MCP protocol)
stdio_server.py (in .mcpb)
      ↓ (HTTP)
FastAPI Server (port 8765)
      ↓
LocalBrain Vault
```

### Access Options

LocalBrain provides two ways to integrate with AI tools:

**1. Claude Desktop Extension (This Guide)**
- **Use case**: Direct integration with Claude Desktop app
- **Architecture**: stdio wrapper + local MCP server
- **Security**: Local-only, no external access
- **Setup**: Install .mcpb extension in Claude Desktop

**2. Remote Bridge (Optional)**
- **Use case**: External access (ChatGPT, mobile apps, other AI tools)
- **Architecture**: WebSocket tunnel + public bridge server
- **Security**: Multi-layer auth, zero data storage
- **Setup**: See [Remote MCP Bridge](../../../../../remote-mcp/README.md)

**This guide covers Claude Desktop integration.** For external/remote access, see the Remote MCP Bridge documentation.

---

## Prerequisites

### 1. Python Environment

Ensure you have Python 3.10+ installed:

```bash
python3 --version  # Should be 3.10 or higher
```

### 2. Install Dependencies

```bash
cd electron/backend
pip install -r requirements.txt
```

This installs all required packages including:
- `mcp` - Model Context Protocol SDK
- `fastapi` - REST API framework
- `httpx` - HTTP client
- `chromadb` - Vector database
- And other dependencies

### 3. Configure Environment

Create or update your `.env` file:

```bash
cp src/core/mcp/examples/.env.example .env
vim .env
```

**Required variables:**
```env
VAULT_PATH=my-vault
CHROMA_API_KEY=your_chroma_api_key_here
CHROMA_TENANT=default-tenant
CHROMA_DATABASE=default-database
```

### 4. Start FastAPI Server

The FastAPI server must be running before using the extension:

```bash
# Terminal 1: Start the server
python -m src.core.mcp.server
```

Keep this terminal open. You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8765
MCP server ready on 127.0.0.1:8765
```

---

## Building the Extension

### Step 1: Navigate to Extension Directory

```bash
cd electron/backend/src/core/mcp/extension
```

### Step 2: Run Package Script

```bash
./package.sh
```

This script will:
1. Create the `server/` directory
2. Copy `stdio_server.py`
3. Create `requirements.txt` for the extension
4. Validate `manifest.json`
5. Package everything into `localbrain.mcpb`

Expected output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LocalBrain Extension Packager
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 Directories:
   Extension: .../extension
   Backend:   .../backend

📁 Creating server directory...
📄 Copying stdio_server.py...
📋 Creating requirements.txt...
📝 Creating README.md...
✅ Validating manifest.json...
📦 Creating .mcpb bundle...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Success! Extension packaged
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Package: localbrain.mcpb (XX KB)
```

---

## Installing the Extension

### Method 1: Drag and Drop (Recommended)

1. **Open Claude Desktop**
2. **Drag `localbrain.mcpb`** into the Claude Desktop window
3. Claude will prompt you to install the extension
4. Click **"Install"**

### Method 2: Settings Menu

1. Open Claude Desktop
2. Go to **Settings** → **Extensions**
3. Click **"Install Extension"**
4. Select `localbrain.mcpb`

---

## Configuring the Extension

After installation, Claude Desktop will show a configuration screen:

### Required Fields:

1. **Vault Directory** (`vault_path`)
   - Click "Browse" and select your vault directory
   - Example: `/Users/you/Projects/localbrain/my-vault`

2. **ChromaDB API Key** (`chroma_api_key`)
   - Enter your ChromaDB Cloud API key
   - This is marked as sensitive and stored securely

### Optional Fields:

3. **MCP API Key** (`api_key`)
   - Default: `dev-key-local-only`
   - Only change if you've customized authentication

4. **ChromaDB Tenant** (`chroma_tenant`)
   - Default: `default-tenant`

5. **ChromaDB Database** (`chroma_database`)
   - Default: `default-database`

Click **"Save"** when done.

---

## Verifying Installation

### 1. Check for Tools Icon

Look for the **🔨 hammer icon** in the bottom-right corner of Claude Desktop. This indicates that MCP servers (including LocalBrain) are connected.

### 2. Test the Extension

Try these commands in Claude Desktop:

**Search your vault:**
```
Search my vault for "internship applications"
```

**List directory:**
```
List files in my career folder
```

**Open a file:**
```
Open career/job-search.md
```

**Get a summary:**
```
Summarize my personal/goals.md file
```

---

## Available Tools

Once installed, Claude has access to these LocalBrain tools:

| Tool | Description | Example Use |
|------|-------------|-------------|
| **search** | Natural language search | "Find information about internships" |
| **open** | Read full file contents | "Open career/resume.md" |
| **summarize** | Generate file summaries | "Summarize my goals document" |
| **list** | Browse directory structure | "List all files in projects/" |

---

## Troubleshooting

### Issue: "Cannot connect to FastAPI server"

**Solution:**
1. Ensure FastAPI server is running: `python -m src.core.mcp.server`
2. Check it's accessible: `curl http://localhost:8765/health`
3. Look for error messages in the server terminal

### Issue: "No hammer icon appears"

**Solution:**
1. Check Claude Desktop logs: **Settings** → **Developer** → **View Logs**
2. Verify extension is installed: **Settings** → **Extensions**
3. Restart Claude Desktop completely
4. Reinstall the extension if needed

### Issue: "Vault path not found"

**Solution:**
1. Go to **Settings** → **Extensions** → **LocalBrain** → **Configure**
2. Browse to your actual vault directory
3. Ensure it's an absolute path (not relative)
4. The directory should contain your vault files

### Issue: "Authentication failed"

**Solution:**
1. Check MCP API key matches what's configured in `~/.localbrain/mcp/clients.json`
2. Default is `dev-key-local-only` - use this unless you've changed it
3. Verify the client is enabled in clients.json

### Issue: "ChromaDB connection failed"

**Solution:**
1. Verify ChromaDB API key is correct
2. Check tenant and database names
3. Ensure you have an active ChromaDB Cloud account
4. Test connection from command line: `python -c "import chromadb; client = chromadb.HttpClient(...)"`

---

## Extension File Structure

After packaging, your `.mcpb` file contains:

```
localbrain.mcpb (ZIP archive)
├── manifest.json           # Extension configuration
└── server/
    ├── stdio_server.py     # MCP stdio wrapper
    ├── requirements.txt    # Python dependencies
    └── README.md           # Server documentation
```

### Manifest.json Features

- **User Configuration:** Interactive UI for vault path, API keys
- **Template Variables:** `${__dirname}`, `${user_config.*}`
- **Sensitive Data:** ChromaDB API key stored in OS keychain
- **Cross-Platform:** Works on macOS, Linux, Windows

---

## Updating the Extension

To update after making changes:

1. **Rebuild the package:**
   ```bash
   cd electron/backend/src/core/mcp/extension
   ./package.sh
   ```

2. **Uninstall old version:**
   - Claude Desktop → Settings → Extensions → LocalBrain → Uninstall

3. **Install new version:**
   - Drag new `localbrain.mcpb` into Claude Desktop

---

## Development Tips

### Testing Changes to stdio_server.py

1. Make changes to `stdio_server.py`
2. Run `./package.sh` to rebuild
3. Reinstall extension in Claude Desktop
4. Test with simple queries

### Debugging

**Enable verbose logging:**

Edit `stdio_server.py` and add at the top of `main()`:

```python
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
```

**View Claude Desktop logs:**
- macOS: `~/Library/Logs/Claude/`
- Windows: `%APPDATA%\Claude\logs\`
- Linux: `~/.config/Claude/logs/`

**Test stdio_server directly:**

```bash
cd server
python stdio_server.py
# Type MCP commands manually, e.g.:
# {"jsonrpc":"2.0","method":"tools/list","id":1}
```

---

## Manifest.json Customization

You can customize the extension by editing `manifest.json`:

### Change Extension Name

```json
"display_name": "My Custom Name"
```

### Add More Configuration Options

```json
"user_config": {
  "my_option": {
    "type": "string",
    "title": "My Option",
    "description": "Description here",
    "required": false,
    "default": "default_value"
  }
}
```

### Supported Config Types

- `string` - Text input
- `number` - Numeric input
- `directory` - Directory picker
- `boolean` - Checkbox
- `select` - Dropdown menu

### Using Config in Environment

```json
"env": {
  "MY_VAR": "${user_config.my_option}"
}
```

---

## Packaging for Distribution

### Create Release Package

```bash
# Build the extension
./package.sh

# Create a release archive
cd ..
tar -czf localbrain-extension-v1.0.0.tar.gz extension/localbrain.mcpb extension/manifest.json
```

### Share with Others

Users can install by:
1. Downloading `localbrain.mcpb`
2. Dragging it into Claude Desktop
3. Configuring their vault path and API keys

**Note:** They'll need:
- Their own LocalBrain installation
- FastAPI server running
- ChromaDB Cloud account

---

## Additional Resources

### LocalBrain Documentation
- [LocalBrain MCP Server Usage](./USAGE.md) - Complete MCP server usage guide
- [LocalBrain MCP Server README](./README.md) - MCP server overview and architecture
- [Remote MCP Bridge](../../../../../remote-mcp/README.md) - External access option

### External Documentation
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Claude Desktop Extensions Guide](https://www.anthropic.com/engineering/desktop-extensions)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Claude Desktop logs
3. Verify FastAPI server is running correctly
4. File an issue in the LocalBrain repository

---

**Extension Version:** 1.0.0
**Last Updated:** 2025-01-25
**Compatible with:** Claude Desktop 1.0.0+
