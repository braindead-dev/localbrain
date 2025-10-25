# Remote MCP Bridge - Implementation Guide

This implementation provides a secure relay/proxy service that enables external access to your LocalBrain instance from anywhere.

## Architecture

The Remote MCP Bridge consists of two components:

### 1. Bridge Server (Public-Facing)

**Purpose:** Accept requests from external tools and relay them to local MCP servers via WebSocket tunnels.

**Deployment:** Runs on a VPS, cloud server, or any public-facing host.

**Technology:** FastAPI + WebSockets

**Endpoints:**
- `ws://<host>:<port>/tunnel/connect` - WebSocket endpoint for tunnel connections
- `/u/{user_id}/{tool}` - Public MCP tool endpoints (search, search_agentic, open, summarize, list)
- `/health` - Health check
- `/admin/tunnels` - Admin: list active tunnels
- `/admin/tunnel/{user_id}/revoke` - Admin: revoke user access

### 2. Tunnel Client (Local Machine)

**Purpose:** Connect your local MCP server to the bridge via persistent WebSocket tunnel.

**Deployment:** Runs on your local machine alongside your MCP server.

**Technology:** Python + websockets + httpx

**Function:**
- Establishes WebSocket connection to bridge
- Forwards incoming requests to local MCP server (http://127.0.0.1:8766)
- Sends responses back through tunnel
- Maintains keepalive pings

## Data Flow

```
External Tool (ChatGPT, Claude, etc.)
    ↓ HTTPS + API Key
Bridge Server (Public VPS)
    ↓ WebSocket Tunnel (authenticated)
Tunnel Client (Your Computer)
    ↓ HTTP + X-API-Key
MCP Server (Port 8766)
    ↓ HTTP
Daemon (Port 8765)
    ↓
LocalBrain Vault
```

## Security Model

### Authentication Layers

1. **External → Bridge:** API key in request headers (`X-API-Key`)
2. **Bridge ↔ Tunnel:** User ID + API key in WebSocket connection params
3. **Tunnel → MCP:** Local API key in HTTP headers (`X-API-Key: dev-key-local-only`)
4. **MCP → Daemon:** Forwarded internally (localhost only)

### What Gets Stored

**Bridge Server:**
- Active tunnel connections (in-memory only)
- User ID → API key mapping (in-memory only)
- Rate limit counters (in-memory only)
- **No query data, no file contents, no results**

**Tunnel Client:**
- Configuration only (USER_ID, REMOTE_API_KEY, etc.)
- **No query data, no logging beyond errors**

**Everything is ephemeral and discarded when connections close.**

### Encryption

- WebSocket tunnels use WSS (WebSocket Secure) in production
- All public endpoints use HTTPS/TLS
- No plaintext data transmission over the internet

### Rate Limiting

- 60 requests per minute per user (configurable)
- Enforced at bridge level before forwarding
- Prevents abuse and ensures fair usage

### Permissions

- Per-user tool allowlist (search, open, etc.)
- Configured when tunnel connects
- Enforced at bridge before forwarding requests

## Setup Instructions

### Prerequisites

1. **Local MCP Server Running:**
   ```bash
   cd electron/backend
   python -m src.core.mcp.server
   ```
   Should be accessible at `http://127.0.0.1:8766`

2. **Daemon Running:**
   ```bash
   cd electron/backend
   python src/daemon.py
   ```
   Should be accessible at `http://127.0.0.1:8765`

3. **Python 3.10+ installed**

### Step 1: Deploy Bridge Server (One-Time)

**Option A: Local Testing**

```bash
cd remote-mcp

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
vim .env
# Set BRIDGE_SECRET to a secure random string

# Start bridge
./start_bridge.sh
```

Bridge will run on `http://localhost:8767`

**Option B: Production Deployment (VPS/Cloud)**

```bash
# On your VPS
git clone <your-repo>
cd localbrain/remote-mcp

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
vim .env
# Set:
#   BRIDGE_HOST=0.0.0.0
#   BRIDGE_PORT=8767
#   BRIDGE_SECRET=<strong-random-secret>

# Run with process manager (systemd, supervisord, or screen)
python3 bridge_server.py
```

**For HTTPS:** Put bridge behind nginx/caddy with SSL certificates.

### Step 2: Configure Tunnel Client (On Your Local Machine)

```bash
cd remote-mcp

# Copy environment template
cp .env.example .env

# Generate USER_ID
python3 -c "import uuid; print(str(uuid.uuid4()))"
# Example output: a3f9c7d2-1e4a-4b8f-9c6d-8e2f5a7b3c1d

# Generate REMOTE_API_KEY
python3 -c "import secrets; print('lb_' + secrets.token_urlsafe(32))"
# Example output: lb_Xk8mP9qR2vL3wN4jT5fH6gY7zS8aD9bC0eF1xW2yM3n

# Edit .env
vim .env
```

**Configure these variables:**

```env
# Bridge WebSocket URL
BRIDGE_URL=ws://your-bridge-server.com:8767
# For local testing: ws://localhost:8767

# Local MCP server (default is correct)
LOCAL_MCP_URL=http://127.0.0.1:8766
LOCAL_API_KEY=dev-key-local-only

# Your generated credentials
USER_ID=a3f9c7d2-1e4a-4b8f-9c6d-8e2f5a7b3c1d
REMOTE_API_KEY=lb_Xk8mP9qR2vL3wN4jT5fH6gY7zS8aD9bC0eF1xW2yM3n

# Allowed tools (default is all)
ALLOWED_TOOLS=search,search_agentic,open,summarize,list
```

### Step 3: Start Tunnel

```bash
cd remote-mcp
./start_tunnel.sh
```

You should see:

```
✅ Tunnel established successfully!
  Tunnel ID: f8e2d3c1-9a7b-4c5d-8e6f-2a3b4c5d6e7f
  Remote URL: https://mcp.localbrain.app/u/a3f9c7d2-1e4a-4b8f-9c6d-8e2f5a7b3c1d

Your LocalBrain is now accessible remotely at:
  https://mcp.localbrain.app/u/a3f9c7d2-1e4a-4b8f-9c6d-8e2f5a7b3c1d

External tools can now access your vault using:
  URL: https://mcp.localbrain.app/u/a3f9c7d2-1e4a-4b8f-9c6d-8e2f5a7b3c1d/{tool}
  API Key: lb_Xk8mP9qR2vL3wN4jT5fH6gY7zS8aD9bC0eF1xW2yM3n
```

**Keep this terminal open.** The tunnel client must run continuously to maintain the connection.

## Usage

### Using with External Tools

Once your tunnel is active, external tools can access your LocalBrain:

**Example: Search**

```bash
curl -X POST https://your-bridge.com/u/YOUR_USER_ID/search \
  -H "X-API-Key: YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What internship applications did I submit?",
    "top_k": 5
  }'
```

**Example: List Files**

```bash
curl -X POST https://your-bridge.com/u/YOUR_USER_ID/list \
  -H "X-API-Key: YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "career"
  }'
```

**Example: Open File**

```bash
curl -X POST https://your-bridge.com/u/YOUR_USER_ID/open \
  -H "X-API-Key: YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filepath": "career/job-search.md"
  }'
```

### Available Tools

| Tool | Endpoint | Description |
|------|----------|-------------|
| search | `/u/{user_id}/search` | Natural language semantic search |
| search_agentic | `/u/{user_id}/search_agentic` | Structured search with filters |
| open | `/u/{user_id}/open` | Read full file contents |
| summarize | `/u/{user_id}/summarize` | Generate file summary |
| list | `/u/{user_id}/list` | List directory contents |

### Integration with AI Tools

**ChatGPT Custom GPT:**

Configure your GPT with:
- Base URL: `https://your-bridge.com/u/YOUR_USER_ID`
- Authentication: Custom header `X-API-Key: YOUR_REMOTE_API_KEY`
- Available actions: search, list, open, summarize

**Claude Projects:**

Add as an external tool with the same configuration.

**Custom Scripts:**

Use any HTTP client (curl, httpx, requests, etc.) with proper authentication headers.

## Administration

### List Active Tunnels

```bash
curl http://your-bridge.com/admin/tunnels \
  -H "X-Admin-Secret: YOUR_BRIDGE_SECRET"
```

### Revoke User Access

```bash
curl -X POST http://your-bridge.com/admin/tunnel/USER_ID/revoke \
  -H "X-Admin-Secret: YOUR_BRIDGE_SECRET"
```

### Monitor Logs

**Bridge Server:**
- Check server logs for connection/disconnection events
- Monitor for failed auth attempts
- Track request volume per user

**Tunnel Client:**
- Monitor for connection drops
- Check for forwarding errors
- Verify keepalive pings

## Troubleshooting

### Issue: Tunnel won't connect

**Solution:**
1. Verify bridge server is running: `curl http://bridge-host:8767/health`
2. Check firewall allows WebSocket connections
3. Verify BRIDGE_URL is correct in .env
4. Check bridge server logs for errors

### Issue: "No active tunnel" error

**Solution:**
1. Ensure tunnel client is running
2. Check tunnel client logs for connection errors
3. Verify USER_ID matches in both client and requests
4. Restart tunnel client

### Issue: "Invalid API key" error

**Solution:**
1. Verify REMOTE_API_KEY matches in .env and requests
2. Check bridge server logs for auth attempts
3. Ensure tunnel is connected before making requests

### Issue: Requests timeout

**Solution:**
1. Check local MCP server is running: `curl http://localhost:8766/health`
2. Verify daemon is running: `curl http://localhost:8765/health`
3. Check tunnel client logs for forwarding errors
4. Increase timeout in bridge_server.py if needed

### Issue: Rate limit exceeded

**Solution:**
1. Reduce request frequency
2. Adjust MAX_REQUESTS_PER_MINUTE in bridge config
3. Contact admin to increase your rate limit

## Production Deployment

### Bridge Server Best Practices

1. **Use HTTPS/WSS:**
   - Deploy behind nginx/caddy with SSL certificates
   - Use Let's Encrypt for free certificates
   - Configure proper CORS policies

2. **Secure Admin Endpoints:**
   - Use strong BRIDGE_SECRET
   - Restrict admin endpoints to specific IPs
   - Monitor admin access logs

3. **Process Management:**
   - Use systemd, supervisord, or Docker
   - Auto-restart on failure
   - Redirect logs to persistent storage

4. **Monitoring:**
   - Track active tunnels
   - Monitor resource usage (CPU, memory, connections)
   - Set up alerts for failures

5. **Backups:**
   - No data to backup (everything is ephemeral)
   - Keep .env configuration backed up securely

### Tunnel Client Best Practices

1. **Auto-Start:**
   - Add to systemd user service or launchd
   - Start automatically on login/boot

2. **Monitoring:**
   - Use process monitor to restart on crash
   - Log to file for debugging
   - Set up alerts for disconnections

3. **Security:**
   - Keep .env secure (600 permissions)
   - Never commit .env to git
   - Rotate REMOTE_API_KEY periodically

## Limitations

1. **Request/Response Size:** Limited by WebSocket message size (typically 16MB)
2. **Concurrent Requests:** One request at a time per tunnel (synchronous forwarding)
3. **Latency:** Added latency from extra network hops (bridge relay)
4. **Availability:** Depends on local machine being online and tunnel connected

## Future Enhancements

- [ ] Multiple concurrent requests per tunnel (async queue)
- [ ] Request/response compression
- [ ] Custom domain support
- [ ] Geographic routing (multiple bridge servers)
- [ ] Advanced rate limiting (per-tool, burst allowance)
- [ ] Audit log export
- [ ] Webhook notifications for tunnel events
- [ ] Multi-device sync through bridge
- [ ] Load balancing across multiple local instances

## Security Considerations

**Never expose your daemon (port 8765) or MCP server (port 8766) directly to the internet.**

The bridge architecture ensures:
- No direct access to your local machine
- Authentication at every layer
- No data storage on bridge
- Encrypted transmission
- Rate limiting and abuse prevention
- Revocable access (close tunnel anytime)

**The bridge is just a relay - all data processing happens locally on your machine.**

## Support

For issues and questions:
1. Check troubleshooting section above
2. Review tunnel client and bridge server logs
3. Verify all services are running correctly
4. File an issue in the LocalBrain repository
