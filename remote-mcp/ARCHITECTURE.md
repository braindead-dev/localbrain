# Remote MCP Bridge - Architecture Overview

## Integration with LocalBrain

The Remote MCP Bridge extends LocalBrain's existing architecture to enable secure external access without modifying core components.

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
                    │ WebSocket Tunnel
                    ▼
┌─────────────────────────────────────────────────────────┐
│             Tunnel Client (NEW)                          │
│         tunnel_client.py on Local Machine                │
│                                                           │
│  • Maintain persistent WebSocket connection              │
│  • Forward requests to local MCP                         │
│  • Send responses back through tunnel                    │
│  • Auto-reconnect on disconnect                          │
│  • Keepalive pings                                       │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP + X-API-Key
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
                    │ HTTP
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

The bridge adds an additional authentication layer without modifying existing auth:

```
1. External Request
   ↓
   X-API-Key: REMOTE_API_KEY (bridge validates)
   ↓
2. Bridge → Tunnel
   ↓
   WebSocket connection authenticated with USER_ID + REMOTE_API_KEY
   ↓
3. Tunnel → MCP Server
   ↓
   X-API-Key: dev-key-local-only (existing MCP auth)
   ↓
4. MCP Server → Daemon
   ↓
   localhost only (existing proxy)
   ↓
5. Daemon → Vault
   ↓
   File system access
```

## Request Flow Example

**External Search Request:**

```
1. External tool sends:
   POST https://bridge.com/u/abc123/search
   Headers: X-API-Key: lb_xyz789...
   Body: {"query": "internship applications", "top_k": 5}

2. Bridge server:
   - Validates REMOTE_API_KEY (lb_xyz789...)
   - Checks USER_ID (abc123) has active tunnel
   - Verifies "search" tool is allowed
   - Checks rate limit (60/min)
   - Forwards via WebSocket:
     {
       "tool": "search",
       "params": {"query": "...", "top_k": 5},
       "request_id": "req-123"
     }

3. Tunnel client:
   - Receives from WebSocket
   - Forwards to local MCP:
     POST http://127.0.0.1:8766/mcp/search
     Headers: X-API-Key: dev-key-local-only
     Body: {"query": "...", "top_k": 5}

4. MCP server:
   - Authenticates local API key
   - Forwards to daemon:
     POST http://127.0.0.1:8765/protocol/search
     Body: {"q": "internship applications"}

5. Daemon:
   - Performs semantic search in vault
   - Returns contexts and results

6. Response flows back:
   Daemon → MCP → Tunnel → Bridge → External Tool
```

## Data Privacy Guarantees

**Bridge Server:**
- Stores in memory:
  - Active WebSocket connections
  - USER_ID → REMOTE_API_KEY mappings
  - Rate limit counters
  - Connection timestamps
- **Never stores:**
  - Search queries
  - File contents
  - Search results
  - Any vault data

**All data is ephemeral and lost when:**
- WebSocket connection closes
- Bridge server restarts
- User disconnects tunnel

## Port Allocation

| Service | Port | Accessibility |
|---------|------|---------------|
| Daemon | 8765 | localhost only |
| MCP Server | 8766 | localhost only |
| Bridge Server | 8767 | public (0.0.0.0) |

**Security Note:** Daemon and MCP server should NEVER be exposed to the internet. Only the bridge server is public-facing.

## File Organization

```
remote-mcp/
├── bridge_server.py         # Public relay server
├── tunnel_client.py         # Local tunnel client
├── requirements.txt         # Dependencies
├── .env.example             # Configuration template
├── .env                     # User config (git-ignored)
├── .gitignore               # Prevent committing secrets
├── start_bridge.sh          # Start bridge script
├── start_tunnel.sh          # Start tunnel script
├── test_bridge.py           # Integration tests
├── README.md                # Overview and quick start
├── IMPLEMENTATION.md        # Complete setup guide
└── ARCHITECTURE.md          # This file
```

## Zero Modification Integration

The bridge integrates with LocalBrain **without modifying any existing code**:

✅ **No changes to:**
- daemon.py
- server.py (MCP server)
- Any ingestion or search logic
- Any existing authentication
- Any file operations

✅ **Only additions:**
- New bridge server (separate process)
- New tunnel client (separate process)
- New configuration (.env)
- New documentation

✅ **Benefits:**
- No risk to existing functionality
- Can be disabled by stopping tunnel client
- Can be removed completely without affecting LocalBrain
- Updates to LocalBrain don't affect bridge
- Bridge updates don't affect LocalBrain

## Deployment Scenarios

### Scenario 1: Local Testing

```
Bridge:  localhost:8767
Tunnel:  localhost → localhost:8767
MCP:     localhost:8766
Daemon:  localhost:8765
```

All components run on same machine for development/testing.

### Scenario 2: Self-Hosted Bridge

```
Bridge:  your-vps.com:8767 (public)
Tunnel:  local machine → your-vps.com:8767 (WebSocket)
MCP:     localhost:8766
Daemon:  localhost:8765
```

Bridge on VPS, everything else local. Recommended for personal use.

### Scenario 3: Official Hosted Service (Future)

```
Bridge:  mcp.localbrain.app (managed service)
Tunnel:  local machine → mcp.localbrain.app (WebSocket)
MCP:     localhost:8766
Daemon:  localhost:8765
```

Official LocalBrain relay service. Coming soon.

## Performance Characteristics

**Latency Added:**
- Bridge relay: ~10-50ms
- WebSocket overhead: ~5-10ms
- Total added latency: ~15-60ms

**Throughput:**
- Limited by rate limiting (60 req/min default)
- Can be increased per-user by bridge admin

**Scalability:**
- Bridge server: Handles 100s of concurrent tunnels
- Memory usage: ~1-5MB per active tunnel
- No disk I/O (everything in-memory)

## Security Architecture

### Defense in Depth

1. **Network Level:**
   - Firewall: Block ports 8765, 8766 from internet
   - Only port 8767 (bridge) exposed

2. **Application Level:**
   - Bridge: Remote API key authentication
   - MCP: Local API key authentication
   - Daemon: localhost-only binding

3. **Transport Level:**
   - HTTPS for public endpoints (with reverse proxy)
   - WSS for WebSocket tunnels (with reverse proxy)

4. **Access Control:**
   - Per-user tool allowlist
   - Rate limiting per user
   - Revocable access (stop tunnel anytime)

### Attack Surface

**What attackers CAN do:**
- Try to guess REMOTE_API_KEYs (mitigated by strong random keys)
- Flood bridge with requests (mitigated by rate limiting)
- Attempt to connect fake tunnels (requires USER_ID + REMOTE_API_KEY)

**What attackers CANNOT do:**
- Access MCP or daemon directly (not exposed)
- Bypass authentication (enforced at multiple layers)
- Access data without valid tunnel connection
- Perform DoS on local machine (rate limited at bridge)

## Monitoring and Observability

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
```
GET /admin/tunnels
  → List all active tunnels with stats

POST /admin/tunnel/{user_id}/revoke
  → Force disconnect a user's tunnel
```

## Failure Modes and Recovery

| Failure | Impact | Recovery |
|---------|--------|----------|
| Bridge server down | External access unavailable | Auto-reconnect when back up |
| Tunnel disconnected | External access unavailable | Auto-reconnect in 5 seconds |
| MCP server down | Requests fail | Restart MCP server |
| Daemon down | Requests fail | Restart daemon |
| Network interruption | Tunnel disconnects | Auto-reconnect when network restored |

All failures are **graceful** - they don't affect LocalBrain's local functionality.

## Comparison with Alternatives

### vs. ngrok/localtunnel

**Bridge Approach:**
- ✅ Complete control over security
- ✅ Custom authentication
- ✅ No third-party exposure
- ✅ Can self-host
- ❌ Requires VPS/cloud for bridge

**ngrok/localtunnel:**
- ❌ Third-party has tunnel access
- ❌ Limited authentication control
- ❌ Potential security/privacy concerns
- ✅ No infrastructure needed

### vs. Direct Port Forwarding

**Bridge Approach:**
- ✅ No home IP exposure
- ✅ Additional auth layer
- ✅ Rate limiting
- ✅ Can revoke access instantly

**Port Forwarding:**
- ❌ Exposes home IP
- ❌ Direct access to MCP server
- ❌ No rate limiting
- ❌ Network reconfiguration needed

### vs. VPN

**Bridge Approach:**
- ✅ No VPN client needed
- ✅ Works from any device/network
- ✅ Per-tool permissions

**VPN:**
- ❌ VPN client required
- ❌ More complex setup
- ❌ Network configuration needed
- ✅ Full local network access

## Future Architecture Considerations

**Load Balancing:**
```
External Tools
    ↓
Load Balancer
    ↓
Bridge 1    Bridge 2    Bridge 3
    ↓          ↓          ↓
  Tunnel Client (picks least loaded bridge)
```

**Geographic Distribution:**
```
US Users → US Bridge → Tunnel → Local MCP
EU Users → EU Bridge → Tunnel → Local MCP
Asia Users → Asia Bridge → Tunnel → Local MCP
```

**Multi-Device Sync:**
```
Bridge Server
    ↓
Multiple Tunnel Clients
    ↓
Multiple LocalBrain Instances
    ↓
Sync via Bridge (with conflict resolution)
```

## Conclusion

The Remote MCP Bridge provides secure, optional external access to LocalBrain while:
- Maintaining zero-knowledge architecture
- Requiring no modifications to existing code
- Adding minimal latency and overhead
- Being completely removable if not needed

It's designed as a **pure relay** - no data processing, no data storage, just forwarding.
