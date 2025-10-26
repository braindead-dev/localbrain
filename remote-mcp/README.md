# Remote MCP Bridge

MCP-compliant bridge for accessing your LocalBrain from anywhere.

## What Is This?

A bridge system that makes your LocalBrain accessible to MCP clients (Claude, Cursor, ChatGPT, etc.) from anywhere on the internet.

**Architecture:**
```
MCP Client (Claude/Cursor/etc)
    ↓ JSON-RPC 2.0
Server (146.190.120.44:8767) ← Runs 24/7
    ↓ WebSocket Tunnel
Client (your Mac) ← Run when you want remote access
    ↓ HTTP
Local MCP Server (127.0.0.1:8766)
    ↓
Your Vault
```

## Structure

```
remote-mcp/
├── server/              ← Deploy to 146.190.120.44 (runs 24/7)
│   ├── mcp_http_server.py
│   ├── .env.example
│   └── README.md
│
├── client/              ← Run on your local machine
│   ├── mcp_tunnel_client.py
│   ├── .env.example
│   └── README.md
│
├── deploy.sh            ← Deploy/update server
└── README.md            ← This file
```

## Quick Start

### 1. Deploy Server (One-Time)

```bash
./deploy.sh
```

This uploads the MCP bridge to your server and sets it up as a 24/7 service.

See [`server/README.md`](server/README.md) for manual setup.

### 2. Configure Client (One-Time)

```bash
cd client

# Generate credentials
python3 -c "import uuid; print(str(uuid.uuid4()))"  # USER_ID
python3 -c "import secrets; print('lb_' + secrets.token_urlsafe(32))"  # REMOTE_API_KEY

# Configure
cp .env.example .env
nano .env  # Fill in USER_ID and REMOTE_API_KEY
```

See [`client/README.md`](client/README.md) for details.

### 3. Start Tunnel (Daily)

**Terminal 1 - Local MCP Server:**
```bash
cd /Users/henry/Documents/GitHub/localbrain/electron/backend
python src/core/mcp/extension/start_servers.py
```

**Terminal 2 - Tunnel Client:**
```bash
cd client
/Users/henry/miniconda3/bin/python mcp_tunnel_client.py
```

You'll see:
```
✅ Tunnel established successfully!
  Remote MCP Endpoint: http://146.190.120.44:8767/mcp
```

Now your LocalBrain is accessible from anywhere!

## Usage

### Your Remote Endpoint

```
URL: http://146.190.120.44:8767/mcp
Authorization: Bearer <your-REMOTE_API_KEY>
```

Use this in:
- Claude Desktop
- Cursor
- Continue (VS Code)
- ChatGPT (with MCP plugin)
- Any MCP-compatible client

### Configuration Example (Claude Desktop)

`~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "localbrain": {
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

Replace `YOUR_REMOTE_API_KEY` with the key from `client/.env`.

## Testing

```bash
# Test server is running
curl http://146.190.120.44:8767/health

# Test MCP protocol
curl -X POST http://146.190.120.44:8767/mcp \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## How It Works

1. **Server runs 24/7** on `146.190.120.44`
   - Accepts MCP connections from anywhere
   - Waits for tunnel clients to connect

2. **Client runs on your Mac** when you want remote access
   - Connects to server via WebSocket tunnel
   - Forwards requests to local MCP server (port 8766)
   - Returns responses back through tunnel

3. **MCP clients** (Claude, Cursor, etc.) connect to server
   - Send JSON-RPC 2.0 requests
   - Get responses from your local vault
   - Works exactly like local MCP

## Features

✅ **MCP-Compliant** - Works with any MCP client (80+ clients supported)
✅ **JSON-RPC 2.0** - Standard protocol format
✅ **SSE Streaming** - Real-time responses
✅ **Session Management** - Stateful connections
✅ **Tool Discovery** - Clients can list available tools
✅ **Secure** - API key authentication
✅ **Always Available** - Server runs 24/7

## Documentation

- **[Server Setup](server/README.md)** - Deploy to remote server
- **[Client Usage](client/README.md)** - Run on your local machine
- **[Deployment Guide](DEPLOY_MCP_COMPLIANT.md)** - Full deployment instructions
- **[MCP Spec](https://modelcontextprotocol.io/)** - Official MCP documentation

## Workflow

### When Your Electron App is Running

Your electron app automatically starts the local MCP server (port 8766).

**To enable remote access:**
1. Open a terminal
2. Run `cd client && /Users/henry/miniconda3/bin/python mcp_tunnel_client.py`
3. Keep that terminal open
4. Now MCP clients can access your LocalBrain remotely

**To disable remote access:**
- Just close the tunnel terminal (Ctrl+C)

### Server is Always Running

The server part runs 24/7 on `146.190.120.44`. You don't need to touch it.

**To check server status:**
```bash
ssh mcpuser@146.190.120.44
sudo systemctl status mcp-bridge
```

**To restart server:**
```bash
ssh mcpuser@146.190.120.44
sudo systemctl restart mcp-bridge
```

## Troubleshooting

### Tunnel won't connect

1. Check local MCP server is running:
   ```bash
   curl http://127.0.0.1:8766/health
   ```

2. Check server is running:
   ```bash
   curl http://146.190.120.44:8767/health
   ```

3. Check credentials in `client/.env`

### MCP client can't connect

1. Make sure tunnel is connected (see "active_tunnels": 1)
2. Use correct API key in client config
3. Test with curl first

---

**Server runs 24/7. Client runs when you want remote access. Simple!** 🚀
