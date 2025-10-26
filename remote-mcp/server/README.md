# MCP Bridge Server

**Deploy this to your remote server (`146.190.120.44`)**

This is the MCP-compliant bridge that runs 24/7 and accepts connections from MCP clients worldwide.

## What It Does

- Accepts JSON-RPC 2.0 requests from MCP clients (Claude, Cursor, etc.)
- Forwards requests through WebSocket tunnels to local machines
- Returns responses via HTTP or SSE streaming
- Runs continuously as a systemd service

## One-Time Setup

### 1. SSH into Server

```bash
ssh mcpuser@146.190.120.44
```

### 2. Navigate to Directory

```bash
cd ~/localbrain/remote-mcp
```

### 3. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn websockets httpx loguru python-dotenv
```

### 4. Configure Environment

```bash
cp server/.env.example server/.env
nano server/.env
```

Set:
```env
BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=8767
BRIDGE_SECRET=<generate-strong-secret>
```

Generate secret:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. Create Systemd Service

```bash
sudo nano /etc/systemd/system/mcp-bridge.service
```

Paste:
```ini
[Unit]
Description=LocalBrain MCP-Compliant Bridge
After=network.target

[Service]
Type=simple
User=mcpuser
WorkingDirectory=/home/mcpuser/localbrain/remote-mcp/server
Environment="PATH=/home/mcpuser/localbrain/remote-mcp/venv/bin"
ExecStart=/home/mcpuser/localbrain/remote-mcp/venv/bin/python mcp_http_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6. Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-bridge
sudo systemctl start mcp-bridge
```

### 7. Verify Running

```bash
sudo systemctl status mcp-bridge
curl http://localhost:8767/health
```

## Firewall

Port 8767 must be open:
```bash
sudo ufw allow 8767/tcp
sudo ufw status
```

## Monitoring

**View logs:**
```bash
sudo journalctl -u mcp-bridge -f
```

**Check status:**
```bash
sudo systemctl status mcp-bridge
```

**Restart:**
```bash
sudo systemctl restart mcp-bridge
```

## Updating

When you update the code:

```bash
cd ~/localbrain/remote-mcp/server
# Upload new mcp_http_server.py (via scp or git pull)
sudo systemctl restart mcp-bridge
```

## Testing

```bash
# Health check
curl http://146.190.120.44:8767/health

# Initialize (MCP protocol)
curl -X POST http://146.190.120.44:8767/mcp \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

## Files

- `mcp_http_server.py` - MCP-compliant bridge server
- `.env` - Configuration (not in git)
- `README.md` - This file

---

**This runs 24/7 on the server. Client connections come from your local machine (see `../client/`).**
