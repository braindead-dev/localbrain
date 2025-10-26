# Deploy MCP-Compliant Bridge

This guide shows how to deploy the MCP-compliant HTTP/SSE bridge server to your remote server.

## What Changed

**Old bridge** (`bridge_server.py`):
- Custom HTTP API (not MCP-compliant)
- Endpoints like `/u/USER_ID/search`
- Won't work with MCP clients

**New bridge** (`mcp_http_server.py`):
- ✅ MCP-compliant JSON-RPC 2.0
- ✅ Single `/mcp` endpoint
- ✅ SSE streaming support
- ✅ Works with Claude, ChatGPT, Continue, etc.

---

## Deployment Steps

### 1. Upload New Server Code

**From your local machine:**

```bash
cd /Users/henry/Documents/GitHub/localbrain/remote-mcp

# Upload the new MCP-compliant server
scp mcp_http_server.py mcpuser@146.190.120.44:~/localbrain/remote-mcp/
```

### 2. SSH into Server

```bash
ssh mcpuser@146.190.120.44
cd ~/localbrain/remote-mcp
```

### 3. Stop Old Bridge

```bash
sudo systemctl stop mcp-bridge
sudo systemctl disable mcp-bridge
```

### 4. Update Systemd Service

```bash
sudo nano /etc/systemd/system/mcp-bridge.service
```

**Replace contents with:**

```ini
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
```

### 5. Start New Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-bridge
sudo systemctl start mcp-bridge

# Check status
sudo systemctl status mcp-bridge

# View logs
sudo journalctl -u mcp-bridge -f
```

### 6. Test Bridge Health

```bash
curl http://146.190.120.44:8767/health
# Should return: {"status":"healthy","active_tunnels":0,...}
```

---

## Local Machine Setup

### 1. Update Tunnel Client

Your local machine needs to use the new MCP tunnel client:

```bash
cd /Users/henry/Documents/GitHub/localbrain/remote-mcp

# Your .env should already have:
# BRIDGE_URL=ws://146.190.120.44:8767/tunnel/connect
# USER_ID=769b6715-8af2-4eb0-af28-6136283d1753
# REMOTE_API_KEY=lb_pW8BXgttpAjUK4Bc5KK8rJrl_hGSlZ4-KyfLsVJje3w
```

### 2. Start Local Services

**Terminal 1 - Local MCP Server:**
```bash
cd /Users/henry/Documents/GitHub/localbrain/electron/backend
python src/core/mcp/extension/start_servers.py
```

**Terminal 2 - Tunnel Client:**
```bash
cd /Users/henry/Documents/GitHub/localbrain/remote-mcp
/Users/henry/miniconda3/bin/python mcp_tunnel_client.py
```

You should see:
```
✅ Tunnel established successfully!
  Remote MCP Endpoint: http://146.190.120.44:8767/mcp
```

---

## Configure MCP Clients

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "localbrain-remote": {
      "command": "node",
      "args": ["-e", "
        const http = require('http');
        const API_URL = 'http://146.190.120.44:8767/mcp';
        const API_KEY = 'lb_pW8BXgttpAjUK4Bc5KK8rJrl_hGSlZ4-KyfLsVJje3w';
        
        process.stdin.on('data', async (data) => {
          try {
            const req = http.request(API_URL, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${API_KEY}`
              }
            }, (res) => {
              let body = '';
              res.on('data', chunk => body += chunk);
              res.on('end', () => process.stdout.write(body + '\\n'));
            });
            req.write(data);
            req.end();
          } catch (e) {
            console.error(e);
          }
        });
      "]
    }
  }
}
```

### Continue (VS Code)

Add to `.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "localbrain",
      "url": "http://146.190.120.44:8767/mcp",
      "headers": {
        "Authorization": "Bearer lb_pW8BXgttpAjUK4Bc5KK8rJrl_hGSlZ4-KyfLsVJje3w"
      }
    }
  ]
}
```

### Cursor

Add to Cursor settings:

```json
{
  "mcp": {
    "servers": {
      "localbrain": {
        "url": "http://146.190.120.44:8767/mcp",
        "headers": {
          "Authorization": "Bearer lb_pW8BXgttpAjUK4Bc5KK8rJrl_hGSlZ4-KyfLsVJje3w"
        }
      }
    }
  }
}
```

---

## Testing

### 1. Test with curl (JSON-RPC)

**Initialize connection:**
```bash
curl -X POST http://146.190.120.44:8767/mcp \
  -H "Authorization: Bearer lb_pW8BXgttpAjUK4Bc5KK8rJrl_hGSlZ4-KyfLsVJje3w" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "1.0"}
    }
  }'
```

**List tools:**
```bash
curl -X POST http://146.190.120.44:8767/mcp \
  -H "Authorization: Bearer lb_pW8BXgttpAjUK4Bc5KK8rJrl_hGSlZ4-KyfLsVJje3w" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }'
```

**Search:**
```bash
curl -X POST http://146.190.120.44:8767/mcp \
  -H "Authorization: Bearer lb_pW8BXgttpAjUK4Bc5KK8rJrl_hGSlZ4-KyfLsVJje3w" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "search",
      "arguments": {
        "query": "Ballard lab lockbox",
        "top_k": 3
      }
    }
  }'
```

### 2. Test with Python MCP SDK

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import httpx

async def test_mcp():
    async with httpx.AsyncClient() as client:
        # Initialize
        response = await client.post(
            "http://146.190.120.44:8767/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"}
                }
            },
            headers={"Authorization": "Bearer lb_pW8BXgttpAjUK4Bc5KK8rJrl_hGSlZ4-KyfLsVJje3w"}
        )
        print(response.json())

import asyncio
asyncio.run(test_mcp())
```

---

## Troubleshooting

### Bridge not responding

```bash
# Check if service is running
ssh mcpuser@146.190.120.44
sudo systemctl status mcp-bridge

# View recent logs
sudo journalctl -u mcp-bridge -n 50

# Restart service
sudo systemctl restart mcp-bridge
```

### Tunnel not connecting

```bash
# Check local MCP server
curl http://127.0.0.1:8766/health

# Check if bridge accepts tunnels
curl http://146.190.120.44:8767/health

# View tunnel client logs
# (in terminal where you ran mcp_tunnel_client.py)
```

### MCP client can't connect

1. **Check tunnel is connected:**
   - Bridge health should show `"active_tunnels": 1`

2. **Verify API key:**
   - Must match `REMOTE_API_KEY` in local `.env`
   - Pass in `Authorization: Bearer <key>` header

3. **Test with curl first:**
   - Use curl commands above to verify bridge works

---

## What This Gives You

✅ **MCP-compliant bridge** - Works with any MCP client
✅ **JSON-RPC 2.0** - Standard protocol format
✅ **SSE streaming** - Real-time responses
✅ **Session management** - Stateful connections
✅ **Tool discovery** - Clients can list available tools
✅ **Full MCP features** - Resources, prompts, tools, sampling

Your LocalBrain is now accessible from:
- Claude Desktop
- ChatGPT
- Cursor
- Continue
- Any MCP-compatible client

All through a single, standard endpoint! 🚀
