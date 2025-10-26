# Remote MCP Bridge - Architecture

Technical architecture overview for the Remote MCP Bridge system.

## System Overview

The Remote MCP Bridge is a relay service that connects your local MCP server to a publicly accessible bridge server via encrypted WebSocket tunnels, enabling external access without exposing your local machine.

## Component Stack

```
┌─────────────────────────────────────────────────────────┐
│                    External Tools                        │
│            (ChatGPT, Claude, Custom Apps)                │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTPS + X-API-Key
                    ▼
┌─────────────────────────────────────────────────────────┐
│              Bridge Server (NEW)                         │
│          bridge_server.py on VPS/Cloud                   │
│                                                           │
│  • Accept public requests                                │
│  • Authenticate remote API keys                          │
│  • Manage WebSocket tunnels                              │
│  • Rate limiting (60 req/min)                            │
│  • No data storage (100% relay)                          │
└───────────────────┬─────────────────────────────────────┘
                    │ WebSocket Tunnel (WSS)
                    ▼
┌─────────────────────────────────────────────────────────┐
│             Tunnel Client (NEW)                          │
│         tunnel_client.py on Local Machine                │
│                                                           │
│  • Maintain persistent WebSocket connection              │
│  • Forward requests to local MCP                         │
│  • Send responses back through tunnel                    │
│  • Auto-reconnect on disconnect                          │
│  • Keepalive pings every 30s                             │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP + X-API-Key (Local)
                    ▼
┌─────────────────────────────────────────────────────────┐
│          MCP Server (EXISTING - Port 8766)               │
│       electron/backend/src/core/mcp/server.py            │
│                                                           │
│  • FastAPI server with auth & audit                      │
│  • 5 MCP tools: search, search_agentic, open,           │
│    summarize, list                                       │
│  • Proxies to daemon                                     │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP (localhost only)
                    ▼
┌─────────────────────────────────────────────────────────┐
│           Daemon (EXISTING - Port 8765)                  │
│         electron/backend/src/daemon.py                   │
│                                                           │
│  • Core backend service                                  │
│  • Ingestion & search endpoints                          │
│  • File operations                                       │
│  • Gmail connector                                       │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                LocalBrain Vault                          │
│              (Your markdown files)                       │
└─────────────────────────────────────────────────────────┘
```

## Authentication Flow

Multi-layer authentication ensures security at each step:

```
1. External Tool → Bridge
   X-API-Key: REMOTE_API_KEY
   (Bridge validates and checks tunnel exists)

2. Bridge ↔ Tunnel
   WebSocket authenticated with USER_ID + REMOTE_API_KEY
   (Established during tunnel connection)

3. Tunnel → Local MCP Server
   X-API-Key: LOCAL_API_KEY (dev-key-local-only)
   (Tunnel authenticates to MCP)

4. MCP Server → Daemon
   localhost HTTP (no external auth needed)
   (MCP proxies to daemon)

5. Daemon → Vault
   File system access
   (Direct file operations)
```

## Request Flow Example

**External Search Request:**

```
1. External Tool:
   POST https://bridge.com/u/USER_ID/search
   Headers: X-API-Key: REMOTE_API_KEY
   Body: {"query": "internship applications", "top_k": 5}

2. Bridge Server:
   - Validates REMOTE_API_KEY
   - Checks USER_ID has active tunnel
   - Verifies "search" tool is allowed
   - Checks rate limit (60/min)
   - Forwards via WebSocket:
     {
       "tool": "search",
       "params": {"query": "...", "top_k": 5},
       "request_id": "req-123"
     }

3. Tunnel Client:
   - Receives from WebSocket
   - Forwards to local MCP:
     POST http://127.0.0.1:8766/mcp/search
     Headers: X-API-Key: dev-key-local-only
     Body: {"query": "...", "top_k": 5}

4. MCP Server:
   - Authenticates local API key
   - Proxies to daemon:
     POST http://127.0.0.1:8765/protocol/search
     Body: {"q": "internship applications"}

5. Daemon:
   - Performs semantic search in vault
   - Returns contexts and results

6. Response flows back:
   Daemon → MCP → Tunnel → Bridge → External Tool
```

## Data Privacy

**Bridge Server Stores (in-memory only):**
- Active WebSocket connections
- USER_ID → REMOTE_API_KEY mappings
- Rate limit counters
- Connection timestamps

**Bridge Server NEVER Stores:**
- Search queries
- File contents
- Search results
- Any vault data

**All data is ephemeral** - lost when WebSocket closes or server restarts.

## Port Allocation

| Service | Port | Accessibility |
|---------|------|---------------|
| Daemon | 8765 | localhost only |
| MCP Server | 8766 | localhost only |
| Bridge Server | 8767 | public (0.0.0.0) |

**Critical:** Daemon and MCP server must NEVER be exposed to the internet. Only the bridge server should be public-facing.

## Concurrency Handling

The bridge uses a **Single Receiver + Future-based routing** pattern to handle multiple concurrent requests over a single WebSocket:

**Single Receiver:**
```python
# Only tunnel_connect() receives from WebSocket
while True:
    message = await websocket.receive_json()

    if message.get("type") == "ping":
        await websocket.send_json({"type": "pong"})

    elif "request_id" in message:
        tunnel_manager.handle_response(tunnel_id, message)
```

**Future-Based Request Handling:**
```python
# Multiple forward_request() calls can run concurrently
response_future = asyncio.Future()
pending_responses[tunnel_id][request_id] = response_future

async with lock:  # Serialize sends
    await tunnel.send_json(request)

response = await asyncio.wait_for(response_future, timeout=30.0)
```

**Benefits:**
- No WebSocket recv() contention
- True concurrent request handling
- 30-second timeout per request
- Clean request/response matching

## Performance

**Latency Added:**
- Bridge relay: ~10-50ms
- WebSocket overhead: ~5-10ms
- Total added latency: ~15-60ms

**Scalability:**
- Bridge handles 100s of concurrent tunnels
- Memory: ~1-5MB per active tunnel
- No disk I/O (everything in-memory)
- Rate limited to 60 req/min per user

## Security

**Defense in Depth:**

1. **Network Level**
   - Firewall blocks ports 8765, 8766 from internet
   - Only bridge port exposed publicly

2. **Application Level**
   - Remote API key authentication at bridge
   - Local API key authentication at MCP
   - Daemon bound to localhost only

3. **Transport Level**
   - HTTPS for public endpoints (via reverse proxy)
   - WSS for WebSocket tunnels
   - SSL/TLS encryption

4. **Access Control**
   - Per-user tool allowlist
   - Rate limiting (60 req/min)
   - Revocable access (stop tunnel/change key)

**Attack Surface:**

What attackers CAN attempt:
- Guess REMOTE_API_KEYs (mitigated by strong random keys)
- Flood bridge with requests (mitigated by rate limiting)

What attackers CANNOT do:
- Access MCP or daemon directly (not exposed)
- Bypass authentication (enforced at multiple layers)
- Access data without valid tunnel
- DoS local machine (rate limited at bridge)

## Monitoring

**Bridge Server Logs:**
```
INFO: Tunnel registered: xyz-123 for user abc-456
INFO: Request forwarded: search for user abc-456
WARNING: Rate limit exceeded for user abc-456
INFO: Tunnel unregistered: xyz-123
```

**Tunnel Client Logs:**
```
INFO: ✅ Tunnel established successfully!
INFO: 📥 Received request: search (ID: req-123)
INFO: ✅ Request completed: search (245ms)
ERROR: HTTP error forwarding request: Connection refused
```

**Admin Endpoints:**
- `GET /admin/tunnels` - List active tunnels with stats
- `POST /admin/tunnel/{user_id}/revoke` - Force disconnect tunnel

## Failure Modes

| Failure | Impact | Recovery |
|---------|--------|----------|
| Bridge server down | External access unavailable | Auto-reconnect when back up |
| Tunnel disconnected | External access unavailable | Auto-reconnect in 5s |
| MCP server down | Requests fail | Restart MCP server |
| Daemon down | Requests fail | Restart daemon |
| Network interruption | Tunnel disconnects | Auto-reconnect on restore |

All failures are **graceful** - they don't affect LocalBrain's local functionality.

## Zero-Modification Integration

The bridge integrates with LocalBrain **without modifying any existing code**:

**No changes to:**
- daemon.py
- server.py (MCP server)
- Any ingestion or search logic
- Any existing authentication
- Any file operations

**Only additions:**
- New bridge server (separate process)
- New tunnel client (separate process)
- New configuration (.env)
- New documentation

**Benefits:**
- No risk to existing functionality
- Can be disabled by stopping tunnel client
- Can be removed completely without affecting LocalBrain
- Updates to LocalBrain don't affect bridge
- Bridge updates don't affect LocalBrain

## File Organization

```
remote-mcp/
├── bridge_server.py         # Public relay server
├── tunnel_client.py         # Local tunnel client
├── requirements.txt         # Dependencies
├── .env.example             # Configuration template
├── .gitignore               # Prevent committing secrets
├── Caddyfile.example        # HTTPS reverse proxy config
├── start_bridge.sh          # Start bridge script
├── start_tunnel.sh          # Start tunnel script
├── test_bridge.py           # Integration tests
├── README.md                # Overview and quick start
├── DEPLOY_DIGITALOCEAN.md   # Production deployment guide
└── ARCHITECTURE.md          # This file
```

## Deployment Architecture

**Typical Deployment:**

```
Bridge Server: VPS/Cloud (e.g., DigitalOcean droplet)
  - bridge_server.py running via systemd
  - Caddy reverse proxy for HTTPS/SSL
  - Public domain: bridge.example.com
  - Ports 80/443 open (for HTTPS)
  - Port 8767 internal only (bridge listens here)

Local Machine: Your computer
  - tunnel_client.py running
  - MCP server (port 8766)
  - Daemon (port 8765)
  - LocalBrain vault
  - Connects to bridge via WSS
```

**Configuration:**

Bridge `.env` (on VPS):
```env
BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=8767
BRIDGE_SECRET=<admin-secret>
MAX_TUNNEL_IDLE_SECONDS=300
```

Tunnel `.env` (on local machine):
```env
BRIDGE_URL=wss://bridge.example.com/tunnel/connect
LOCAL_MCP_URL=http://127.0.0.1:8766
LOCAL_API_KEY=dev-key-local-only
USER_ID=<your-uuid>
REMOTE_API_KEY=<your-api-key>
ALLOWED_TOOLS=search,search_agentic,open,summarize,list
```

---

**Design Philosophy:** The bridge is a **pure relay** - no data processing, no data storage, just forwarding. It maintains zero-knowledge architecture while enabling external access.
