# MCP Tunnel Client

**Run this on your local machine (Mac)**

Connects your local MCP server to the remote bridge, making your LocalBrain accessible from anywhere.

## What It Does

- Connects to remote bridge via WebSocket tunnel
- Forwards JSON-RPC requests from bridge to your local MCP server (port 8766)
- Returns responses back through the tunnel
- Keeps connection alive with ping/pong

## Prerequisites

Your local MCP server must be running:
```bash
cd /Users/henry/Documents/GitHub/localbrain/electron/backend
python src/core/mcp/extension/start_servers.py
```

This starts:
- Daemon on port 8765
- MCP server on port 8766

## Setup (One-Time)

### 1. Generate Credentials

```bash
# Generate USER_ID
python3 -c "import uuid; print(str(uuid.uuid4()))"

# Generate REMOTE_API_KEY
python3 -c "import secrets; print('lb_' + secrets.token_urlsafe(32))"
```

**Save these values!** You'll need the API key for MCP clients.

### 2. Configure Environment

```bash
cd /Users/henry/Documents/GitHub/localbrain/remote-mcp/client
cp .env.example .env
nano .env
```

Fill in:
```env
BRIDGE_URL=ws://146.190.120.44:8767/tunnel/connect
LOCAL_MCP_URL=http://127.0.0.1:8766
LOCAL_API_KEY=dev-key-local-only
USER_ID=<your-generated-uuid>
REMOTE_API_KEY=<your-generated-api-key>
KEEPALIVE_INTERVAL=30
SSL_VERIFY=false
```

### 3. Install Dependencies

```bash
# Already installed if you have conda environment
# If not:
pip install websockets httpx loguru python-dotenv
```

## Daily Usage

### Start Tunnel

**Terminal 1 - Local MCP Server:**
```bash
cd /Users/henry/Documents/GitHub/localbrain/electron/backend
python src/core/mcp/extension/start_servers.py
```

Wait for:
```
✅ Daemon running on http://127.0.0.1:8765
✅ MCP Server running on http://127.0.0.1:8766
```

**Terminal 2 - Tunnel Client:**
```bash
cd /Users/henry/Documents/GitHub/localbrain/remote-mcp/client
/Users/henry/miniconda3/bin/python mcp_tunnel_client.py
```

Expected output:
```
✅ Local MCP server is running
✅ Tunnel established successfully!
  Remote MCP Endpoint: http://146.190.120.44:8767/mcp

Your LocalBrain is now accessible via MCP at:
  http://146.190.120.44:8767/mcp

Configure MCP clients with:
  "url": "http://146.190.120.44:8767/mcp"
  "headers": {"Authorization": "Bearer lb_YOUR_API_KEY"}
```

### Stop Tunnel

Just press `Ctrl+C` in the tunnel terminal.

## Configure MCP Clients

### Your Remote Endpoint

```
URL: http://146.190.120.44:8767/mcp
API Key: <your-REMOTE_API_KEY>
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "localbrain-remote": {
      "command": "python3",
      "args": ["-c", "
import sys, json, http.client
API_URL = '146.190.120.44:8767'
API_KEY = 'YOUR_REMOTE_API_KEY'

for line in sys.stdin:
    conn = http.client.HTTPConnection(API_URL)
    conn.request('POST', '/mcp', line, {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    })
    resp = conn.getresponse()
    print(resp.read().decode())
    sys.stdout.flush()
"]
    }
  }
}
```

Replace `YOUR_REMOTE_API_KEY` with your actual key from `.env`.

### Cursor / Continue

Add to settings:
```json
{
  "mcp": {
    "servers": {
      "localbrain": {
        "url": "http://146.190.120.44:8767/mcp",
        "headers": {
          "Authorization": "Bearer YOUR_REMOTE_API_KEY"
        }
      }
    }
  }
}
```

## Testing

Test from anywhere:
```bash
curl -X POST http://146.190.120.44:8767/mcp \
  -H "Authorization: Bearer YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "search",
      "arguments": {
        "query": "test search",
        "top_k": 3
      }
    }
  }'
```

## Troubleshooting

### "Cannot connect to local MCP server"

Start your local MCP server first:
```bash
cd /Users/henry/Documents/GitHub/localbrain/electron/backend
python src/core/mcp/extension/start_servers.py
```

### "Connection failed"

Check bridge is running on server:
```bash
curl http://146.190.120.44:8767/health
```

### Wrong credentials

Regenerate and update `.env`:
```bash
python3 -c "import uuid; print(str(uuid.uuid4()))"
python3 -c "import secrets; print('lb_' + secrets.token_urlsafe(32))"
```

## Files

- `mcp_tunnel_client.py` - Tunnel client
- `.env` - Your credentials (not in git)
- `README.md` - This file

---

**Keep this running whenever you want remote MCP access to your LocalBrain.**
