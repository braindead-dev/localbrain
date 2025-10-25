# Remote MCP Bridge - Quick Start Guide

## Prerequisites

✅ LocalBrain daemon running (port 8765)
✅ MCP server running (port 8766)
✅ Python 3.10+

## 5-Minute Setup

### 1. Install Dependencies (2 minutes)

```bash
cd remote-mcp
pip install -r requirements.txt
```

### 2. Configure Environment (1 minute)

```bash
# Copy template
cp .env.example .env

# Generate credentials
python3 -c "import uuid; print('USER_ID=' + str(uuid.uuid4()))"
python3 -c "import secrets; print('REMOTE_API_KEY=lb_' + secrets.token_urlsafe(32))"

# Edit .env and paste your USER_ID and REMOTE_API_KEY
vim .env
```

### 3. Start Bridge (Local Testing) (30 seconds)

**Terminal 1:**
```bash
./start_bridge.sh
# Bridge runs on http://localhost:8767
```

### 4. Start Tunnel (30 seconds)

**Terminal 2:**
```bash
./start_tunnel.sh
# Wait for: ✅ Tunnel established successfully!
```

### 5. Test It (1 minute)

**Terminal 3:**
```bash
python3 test_bridge.py
# Should see: 🎉 All tests passed!
```

## Usage

### From curl

```bash
# Replace USER_ID and REMOTE_API_KEY with your values from .env

# Search
curl -X POST http://localhost:8767/u/YOUR_USER_ID/search \
  -H "X-API-Key: YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "internship applications", "top_k": 5}'

# List files
curl -X POST http://localhost:8767/u/YOUR_USER_ID/list \
  -H "X-API-Key: YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"path": ""}'

# Open file
curl -X POST http://localhost:8767/u/YOUR_USER_ID/open \
  -H "X-API-Key: YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filepath": "career/resume.md"}'
```

### From Python

```python
import httpx

USER_ID = "your-user-id"
API_KEY = "your-remote-api-key"
BRIDGE_URL = "http://localhost:8767"

async def search(query: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BRIDGE_URL}/u/{USER_ID}/search",
            json={"query": query, "top_k": 5},
            headers={"X-API-Key": API_KEY}
        )
        return response.json()

# Use with: asyncio.run(search("my query"))
```

## Production Deployment

### Deploy Bridge to VPS

```bash
# On your VPS
git clone <repo>
cd localbrain/remote-mcp

# Configure for production
cp .env.example .env
vim .env
# Set BRIDGE_HOST=0.0.0.0
# Set BRIDGE_SECRET=<strong-random-secret>

# Run with systemd/supervisord
python3 bridge_server.py
```

### Update Tunnel Client

```bash
# On local machine
vim .env
# Change BRIDGE_URL to your VPS:
# BRIDGE_URL=wss://your-vps.com:8767  # use wss:// for secure WebSocket

./start_tunnel.sh
```

### Add HTTPS (nginx)

```nginx
server {
    listen 443 ssl;
    server_name your-vps.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Bridge HTTP endpoints
    location /u/ {
        proxy_pass http://127.0.0.1:8767;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        proxy_pass http://127.0.0.1:8767;
    }

    # WebSocket tunnel endpoint
    location /tunnel/ {
        proxy_pass http://127.0.0.1:8767;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }
}
```

## Troubleshooting

### "Cannot connect to bridge"
```bash
# Check bridge is running
curl http://localhost:8767/health

# Should return: {"status":"healthy",...}
```

### "No active tunnel"
```bash
# Verify tunnel client is running and connected
# Check tunnel client logs for:
# ✅ Tunnel established successfully!

# Restart tunnel if needed
./start_tunnel.sh
```

### "Cannot connect to local MCP server"
```bash
# Check MCP server is running
curl http://localhost:8766/health

# Start MCP server if needed
cd electron/backend
python -m src.core.mcp.server
```

### "Cannot connect to daemon"
```bash
# Check daemon is running
curl http://localhost:8765/health

# Start daemon if needed
cd electron/backend
python src/daemon.py
```

## Common Commands

```bash
# Start all LocalBrain services (from project root)
python electron/backend/src/core/mcp/extension/start_servers.py

# Start bridge (Terminal 1)
cd remote-mcp && ./start_bridge.sh

# Start tunnel (Terminal 2)
cd remote-mcp && ./start_tunnel.sh

# Test everything (Terminal 3)
cd remote-mcp && python3 test_bridge.py

# View bridge health
curl http://localhost:8767/health

# List active tunnels (admin)
curl http://localhost:8767/admin/tunnels \
  -H "X-Admin-Secret: YOUR_BRIDGE_SECRET"

# Revoke user access (admin)
curl -X POST http://localhost:8767/admin/tunnel/USER_ID/revoke \
  -H "X-Admin-Secret: YOUR_BRIDGE_SECRET"
```

## File Reference

| File | Purpose |
|------|---------|
| `README.md` | Overview and architecture |
| `QUICKSTART.md` | This file - quick setup |
| `IMPLEMENTATION.md` | Complete implementation guide |
| `ARCHITECTURE.md` | Detailed architecture docs |
| `bridge_server.py` | Bridge server code |
| `tunnel_client.py` | Tunnel client code |
| `test_bridge.py` | Integration tests |
| `.env.example` | Configuration template |

## Next Steps

1. **Local Testing**: Follow this guide to test locally
2. **Production**: Deploy bridge to VPS with HTTPS
3. **Integration**: Connect external tools (ChatGPT, Claude, etc.)
4. **Monitor**: Use admin endpoints and logs
5. **Docs**: Read IMPLEMENTATION.md for advanced features

## Security Checklist

- [ ] Generated strong USER_ID (UUID)
- [ ] Generated strong REMOTE_API_KEY (32+ random bytes)
- [ ] Never committed .env to git
- [ ] Bridge uses HTTPS in production (not HTTP)
- [ ] Changed BRIDGE_SECRET from default
- [ ] Firewall blocks ports 8765 and 8766 from internet
- [ ] Firewall allows port 8767 from internet (bridge only)
- [ ] Regular monitoring of active tunnels
- [ ] Periodic rotation of REMOTE_API_KEY

## Getting Help

- **Troubleshooting**: See IMPLEMENTATION.md troubleshooting section
- **Architecture**: See ARCHITECTURE.md for detailed design
- **Issues**: File on GitHub with logs from bridge and tunnel
- **Security**: Report security issues privately

## Key Points

✅ Bridge is **optional** - LocalBrain works without it
✅ Bridge stores **zero data** - it's a pure relay
✅ Stop tunnel = instant access revocation
✅ Self-hosted = complete control
✅ No modifications to LocalBrain core

**You're in control of your data at all times.**
