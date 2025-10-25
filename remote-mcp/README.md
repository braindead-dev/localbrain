# Remote MCP Bridge

An optional online bridge that relays your local MCP server to a remote URL, enabling external access to LocalBrain from anywhere.

## Overview

The Remote MCP is **just a proxy/relay service** between the local MCP on your machine and a publicly accessible URL. It doesn't process any data itself - it simply forwards requests and responses via WebSocket tunnels.

**How It Works:**
```
External Tool → Bridge Server → WebSocket Tunnel → Local MCP Server → Daemon → LocalBrain
   (Internet)    (Public VPS)      (Encrypted)      (Port 8766)    (Port 8765)
```

This allows your local MCP to be used anywhere a remote MCP URL is accepted (ChatGPT, Claude, custom tools, etc.).

## Implementation Status

✅ **COMPLETE** - Fully implemented with:
- Bridge server (FastAPI + WebSockets)
- Tunnel client (persistent connection to bridge)
- Authentication at multiple layers
- Rate limiting (60 req/min per user)
- Tool-level permissions
- Audit logging
- Auto-reconnection
- Keepalive mechanism

See [IMPLEMENTATION.md](./IMPLEMENTATION.md) for complete setup and usage instructions.

## Quick Start

### Step 1: Install Dependencies

```bash
cd remote-mcp
pip install -r requirements.txt
```

### Step 2: Start Bridge Server (One-Time Setup)

**For local testing:**

```bash
./start_bridge.sh
# Bridge runs on http://localhost:8767
```

**For production:** Deploy to VPS/cloud with HTTPS (see IMPLEMENTATION.md)

### Step 3: Configure Tunnel Client

```bash
# Copy environment template
cp .env.example .env

# Generate credentials
python3 -c "import uuid; print('USER_ID=' + str(uuid.uuid4()))"
python3 -c "import secrets; print('REMOTE_API_KEY=lb_' + secrets.token_urlsafe(32))"

# Edit .env and paste your credentials
vim .env
```

### Step 4: Start Tunnel

**Ensure your MCP server is running first:**

```bash
# Terminal 1: Start servers (from project root)
python electron/backend/src/core/mcp/extension/start_servers.py

# Terminal 2: Start tunnel
cd remote-mcp
./start_tunnel.sh
```

You'll see your remote URL:
```
✅ Tunnel established successfully!
Remote URL: https://mcp.localbrain.app/u/YOUR_USER_ID
```

### Step 5: Use from External Tools

```bash
curl -X POST http://localhost:8767/u/YOUR_USER_ID/search \
  -H "X-API-Key: YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "internship applications", "top_k": 5}'
```

## Purpose

Enable external access to your LocalBrain instance without:
- Port forwarding or network configuration
- Exposing your home IP address
- Complex VPN setup
- Cloud hosting requirements

## Architecture

### Components

**1. Bridge Server** (bridge_server.py)
- FastAPI application deployed on public VPS/cloud
- WebSocket endpoint for tunnel connections (`/tunnel/connect`)
- Public MCP endpoints (`/u/{user_id}/{tool}`)
- In-memory tunnel registry (no persistent storage)
- Rate limiting: 60 requests/minute per user
- Admin endpoints for tunnel management

**2. Tunnel Client** (tunnel_client.py)
- Python script running on your local machine
- Maintains persistent WebSocket connection to bridge
- Forwards requests to local MCP server (http://127.0.0.1:8766)
- Sends responses back through tunnel
- Auto-reconnection on disconnection
- Keepalive pings every 30 seconds

**3. Local MCP Server** (existing)
- Your existing MCP server on port 8766
- Receives forwarded requests from tunnel client
- Authenticates with local API key
- Proxies to daemon on port 8765
- Returns responses to tunnel client

### Request Flow

```
1. External tool sends request to bridge
   POST https://bridge.com/u/USER_ID/search
   Header: X-API-Key: REMOTE_API_KEY

2. Bridge validates API key and permissions

3. Bridge forwards via WebSocket to tunnel client
   {tool: "search", params: {...}}

4. Tunnel client forwards to local MCP
   POST http://127.0.0.1:8766/mcp/search
   Header: X-API-Key: dev-key-local-only

5. MCP server proxies to daemon
   POST http://127.0.0.1:8765/protocol/search

6. Response flows back through same chain
```

### Security Layers

**Authentication:**
- External → Bridge: Remote API key verification
- Bridge ↔ Tunnel: User ID + Remote API key in WebSocket handshake
- Tunnel → MCP: Local API key (dev-key-local-only)

**Permissions:**
- Tool-level allowlist per user (search, open, list, etc.)
- Path restrictions (future enhancement)
- Result count limits (future enhancement)

**Data Privacy:**
- No query/response storage on bridge (100% ephemeral)
- All data processing happens locally
- Bridge only relays encrypted WebSocket messages

**What the Bridge Does:**
- Accept requests at public URL
- Authenticate API keys
- Forward requests via WebSocket tunnel
- Return responses to requester
- Rate limiting and abuse prevention
- Connection management (keepalive, cleanup)

**What the Bridge Does NOT Do:**
- Store queries, responses, or any user data
- Process or analyze content
- Cache responses
- Access your files directly
- Log request contents (only metadata)

## Files

- `bridge_server.py` - Bridge server (deploy to VPS/cloud)
- `tunnel_client.py` - Tunnel client (run locally)
- `requirements.txt` - Python dependencies
- `.env.example` - Environment configuration template
- `start_bridge.sh` - Script to start bridge server
- `start_tunnel.sh` - Script to start tunnel client
- `IMPLEMENTATION.md` - Complete implementation guide
- `README.md` - This file

## Configuration

The bridge uses environment variables for configuration. See `.env.example` for all options.

**Key Variables:**

```env
# Bridge Server (VPS/Cloud)
BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=8767
BRIDGE_SECRET=change-me-in-production

# Tunnel Client (Local Machine)
BRIDGE_URL=ws://your-bridge-server.com:8767
LOCAL_MCP_URL=http://127.0.0.1:8766
LOCAL_API_KEY=dev-key-local-only
USER_ID=<your-unique-id>
REMOTE_API_KEY=<your-remote-api-key>
ALLOWED_TOOLS=search,search_agentic,open,summarize,list
```

## Use Cases

**AI Tool Integration:**
- Use LocalBrain with ChatGPT, Claude, or other AI assistants
- Access your knowledge base from any AI tool that supports MCP
- Custom workflows and automations

**Mobile Access:**
- Search your LocalBrain from phone via AI apps
- Quick note capture from anywhere
- On-the-go knowledge retrieval

**Remote Work:**
- Access home LocalBrain from office
- Use from any device without VPN
- Seamless cross-device experience

## Technical Details

**Connection:**
- WebSocket tunnel with persistent connection
- Auto-reconnection on disconnection
- Keepalive pings every 30 seconds
- JSON message format for requests/responses

**Deployment:**
- **Self-Hosted**: Run your own bridge on VPS or cloud (recommended)
- **Local Testing**: Run bridge on localhost for development
- **Docker**: Coming soon
- **Hosted Service**: Coming soon (official LocalBrain relay servers)

**Technologies:**
- FastAPI (async web framework)
- websockets (WebSocket client/server)
- httpx (async HTTP client)
- Pydantic (data validation)

## Privacy & Control

**Data Privacy:**
- Zero data storage on bridge server (100% ephemeral)
- All processing happens locally on your machine
- Bridge only relays encrypted WebSocket messages
- No logging of query contents (only connection metadata)

**Access Control:**
- Stop tunnel client to disable remote access instantly
- Per-tool permissions (allow only search, block open, etc.)
- Rate limiting: 60 requests/minute per user
- Revoke access by changing REMOTE_API_KEY

**Monitoring:**
- Bridge server logs connection events
- Tunnel client logs all forwarded requests
- Admin endpoints to view active tunnels
- Track request counts and last activity per tunnel

**Offline First:**
- LocalBrain works fully without remote bridge
- Bridge is completely optional
- No degradation of local functionality
- All data stays local unless explicitly accessed via tunnel

## Future Enhancements

Planned improvements (see IMPLEMENTATION.md for full list):

**Performance:**
- [ ] Multiple concurrent requests per tunnel (async queue)
- [ ] Request/response compression
- [ ] Response caching (with opt-in)
- [ ] Load balancing across multiple bridges

**Features:**
- [ ] Docker deployment
- [ ] Official hosted bridge service
- [ ] Custom domain support
- [ ] Webhook notifications for tunnel events
- [ ] Web dashboard for tunnel management

**Security:**
- [ ] Two-factor authentication for tunnel setup
- [ ] IP whitelisting
- [ ] Request signing and verification
- [ ] Time-limited access tokens
- [ ] Per-path access restrictions

**Note:** This remote bridge is purely for convenience - LocalBrain is designed to work completely offline and locally without any cloud dependencies. The bridge is 100% optional.