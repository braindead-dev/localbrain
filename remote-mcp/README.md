# Remote MCP Bridge

An optional relay service that enables external access to your LocalBrain from anywhere by connecting your local MCP server to a publicly accessible bridge.

## Overview

The Remote MCP Bridge is a **proxy/relay service** that forwards requests between external tools and your local MCP server via encrypted WebSocket tunnels.

**How It Works:**
```
External Tool → Bridge Server → WebSocket Tunnel → Local MCP Server → Daemon → LocalBrain
   (Internet)    (Public VPS)      (Encrypted)      (Port 8766)    (Port 8765)
```

**Key Features:**
- ✅ Zero data storage (100% ephemeral relay)
- ✅ Multi-layer authentication
- ✅ Rate limiting (60 req/min per user)
- ✅ Auto-reconnection & keepalive
- ✅ Tool-level permissions
- ✅ Self-hosted or use existing bridge

## Quick Start

### Connect to an Existing Bridge

**If someone is already running a bridge server** (e.g., `localbrain.henr.ee`), you can connect directly:

#### 1. Install Dependencies

```bash
cd remote-mcp
pip install -r requirements.txt
```

#### 2. Configure Tunnel Client

**Copy the environment template:**

```bash
cp .env.example .env
```

**Generate your unique credentials:**

```bash
# Generate USER_ID (your unique identifier)
python3 -c "import uuid; print(str(uuid.uuid4()))"
# Example output: 3f079754-88ea-40d7-a486-d41944c0bfd4

# Generate REMOTE_API_KEY (your secret access key)
python3 -c "import secrets; print('lb_' + secrets.token_urlsafe(32))"
# Example output: lb_Tj1oK5B-S0jTSw0vUU63txbal0S1ugcFrjB7pgsf3PI
```

**Edit your `.env` file:**

```bash
nano .env
```

**Update these values:**

```env
# Bridge server URL (replace with the bridge you're connecting to)
BRIDGE_URL=wss://localbrain.henr.ee/tunnel/connect

# Your generated credentials
USER_ID=3f079754-88ea-40d7-a486-d41944c0bfd4
REMOTE_API_KEY=lb_Tj1oK5B-S0jTSw0vUU63txbal0S1ugcFrjB7pgsf3PI

# These defaults should work as-is
LOCAL_MCP_URL=http://127.0.0.1:8766
LOCAL_API_KEY=dev-key-local-only
ALLOWED_TOOLS=search,search_agentic,open,summarize,list
KEEPALIVE_INTERVAL=30
SSL_VERIFY=true
```

**Security Notes:**
- ⚠️ **Keep your `USER_ID` and `REMOTE_API_KEY` secret!**
- ✅ **Each user must generate their own unique credentials** - never share
- 🔒 **Never commit `.env` to git** - it's in `.gitignore` for safety

#### 3. Start Local MCP Server

```bash
# From project root
python electron/backend/src/core/mcp/extension/start_servers.py

# You should see:
# ✅ Daemon running on http://127.0.0.1:8765
# ✅ MCP Server running on http://127.0.0.1:8766
```

Keep this terminal open.

#### 4. Start Tunnel

**In a new terminal:**

```bash
cd remote-mcp
./start_tunnel.sh
```

**You should see:**

```
✅ SSL certificate verification enabled.
✅ Tunnel established successfully!
  Remote URL: https://localbrain.henr.ee/u/YOUR_USER_ID

External tools can now access your vault using:
  URL: https://localbrain.henr.ee/u/YOUR_USER_ID/{tool}
  API Key: YOUR_REMOTE_API_KEY
```

#### 5. Test Your Connection

```bash
curl -X POST https://localbrain.henr.ee/u/YOUR_USER_ID/search \
  -H "X-API-Key: YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "test search", "top_k": 3}'
```

---

### Run Your Own Bridge Server

**To self-host your own bridge:**

1. **Deploy bridge to VPS** - See [DEPLOY_DIGITALOCEAN.md](./DEPLOY_DIGITALOCEAN.md) for complete setup guide
2. **Configure tunnel client** - Same as above, but set `BRIDGE_URL` to your server
3. **Start tunnel** - Follow steps 3-5 above

**For local testing:**

```bash
./start_bridge.sh
# Bridge runs on http://localhost:8767
```

---

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for technical details.

**Components:**

1. **Bridge Server** (`bridge_server.py`)
   - FastAPI application deployed on public VPS
   - WebSocket endpoint: `/tunnel/connect`
   - Public MCP endpoints: `/u/{user_id}/{tool}`
   - In-memory tunnel registry (no persistent storage)
   - Rate limiting: 60 requests/minute per user

2. **Tunnel Client** (`tunnel_client.py`)
   - Runs on your local machine
   - Persistent WebSocket connection to bridge
   - Forwards requests to local MCP server
   - Auto-reconnection with keepalive pings

3. **Local MCP Server** (existing)
   - Port 8766 (localhost only)
   - Receives forwarded requests from tunnel
   - Proxies to daemon on port 8765

**Request Flow:**

```
1. External tool → Bridge: POST https://bridge.com/u/USER_ID/search
   Authentication: X-API-Key: REMOTE_API_KEY

2. Bridge → Tunnel: WebSocket message
   {tool: "search", params: {...}}

3. Tunnel → MCP: POST http://127.0.0.1:8766/mcp/search
   Authentication: X-API-Key: LOCAL_API_KEY

4. MCP → Daemon: POST http://127.0.0.1:8765/protocol/search

5. Response flows back through same chain
```

**Security:**

- **Multi-layer authentication**: Remote API key + local API key
- **Zero data storage**: All data is ephemeral, nothing persists on bridge
- **Tool permissions**: Per-user allowlist (search, open, list, etc.)
- **Rate limiting**: 60 requests/minute default
- **SSL/TLS**: Encrypted WebSocket connections (WSS)
- **Revocable access**: Stop tunnel or change API key anytime

**What the Bridge Does:**
- Accept requests at public URL
- Authenticate API keys
- Forward requests via WebSocket tunnel
- Return responses to requester

**What the Bridge Does NOT Do:**
- Store queries, responses, or any user data
- Process or analyze content
- Cache responses
- Access your files directly

---

## Files

- `bridge_server.py` - Bridge server (deploy to VPS/cloud)
- `tunnel_client.py` - Tunnel client (run locally)
- `requirements.txt` - Python dependencies
- `.env.example` - Environment configuration template
- `Caddyfile.example` - Reverse proxy configuration for HTTPS
- `start_bridge.sh` - Start bridge server script
- `start_tunnel.sh` - Start tunnel client script
- `test_bridge.py` - Integration tests
- `README.md` - This file
- `ARCHITECTURE.md` - Technical architecture details
- `DEPLOY_DIGITALOCEAN.md` - Production deployment guide

---

## Configuration

See `.env.example` for all options.

**Tunnel Client Configuration:**

```env
BRIDGE_URL=wss://your-bridge.com/tunnel/connect  # Bridge WebSocket URL
LOCAL_MCP_URL=http://127.0.0.1:8766              # Local MCP server
LOCAL_API_KEY=dev-key-local-only                 # Local MCP auth
USER_ID=<your-unique-uuid>                       # Your unique ID
REMOTE_API_KEY=<your-remote-api-key>             # Your remote auth key
ALLOWED_TOOLS=search,search_agentic,open,summarize,list
KEEPALIVE_INTERVAL=30                            # Seconds
SSL_VERIFY=true                                  # Verify SSL certificates
```

**Bridge Server Configuration:**

```env
BRIDGE_HOST=0.0.0.0                              # Bind address
BRIDGE_PORT=8767                                 # Server port
BRIDGE_SECRET=<admin-secret>                     # Admin API secret
MAX_TUNNEL_IDLE_SECONDS=300                      # Auto-disconnect idle tunnels
```

---

## Use Cases

**AI Tool Integration:**
- Use LocalBrain with ChatGPT, Claude, or other AI assistants
- Access your knowledge base from any AI tool
- Custom workflows and automations

**Mobile Access:**
- Search your LocalBrain from phone via AI apps
- Quick note capture from anywhere
- On-the-go knowledge retrieval

**Remote Work:**
- Access home LocalBrain from office
- Use from any device without VPN
- Seamless cross-device experience

---

## Privacy & Control

**Data Privacy:**
- ✅ Zero data storage on bridge server (100% ephemeral)
- ✅ All processing happens locally on your machine
- ✅ Bridge only relays encrypted messages
- ✅ No logging of query contents (only connection metadata)

**Access Control:**
- Stop tunnel client to disable remote access instantly
- Per-tool permissions (allow only search, block open, etc.)
- Rate limiting prevents abuse
- Revoke access by changing REMOTE_API_KEY

**Offline First:**
- LocalBrain works fully without remote bridge
- Bridge is completely optional
- No degradation of local functionality
- All data stays local unless explicitly accessed via tunnel

---

## Technologies

- **FastAPI** - Async web framework
- **websockets** - WebSocket client/server
- **httpx** - Async HTTP client
- **Pydantic** - Data validation
- **Caddy** - Reverse proxy with automatic HTTPS

---

## Troubleshooting

**Tunnel won't connect:**
- Check bridge server is running and accessible
- Verify `BRIDGE_URL` is correct in `.env`
- Check firewall allows WebSocket connections

**Requests timeout:**
- Ensure local MCP server is running (port 8766)
- Verify daemon is running (port 8765)
- Check tunnel client logs for forwarding errors

**SSL certificate errors:**
- For valid certificates: Set `SSL_VERIFY=true`
- For self-signed/testing: Set `SSL_VERIFY=false`

**"No active tunnel" error:**
- Ensure tunnel client is running and connected
- Check USER_ID matches in both client and requests
- Restart tunnel client if connection dropped

---

## Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Technical architecture and design
- **[DEPLOY_DIGITALOCEAN.md](./DEPLOY_DIGITALOCEAN.md)** - Production deployment guide
- **[Caddyfile.example](./Caddyfile.example)** - HTTPS reverse proxy configuration

---

**Note:** The remote bridge is purely for convenience - LocalBrain is designed to work completely offline and locally without any cloud dependencies. The bridge is 100% optional.
