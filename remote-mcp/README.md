# Remote MCP Bridge

An optional online bridge that relays your local MCP server to a remote URL, enabling external access to LocalBrain from anywhere.

## Overview

The Remote MCP is **just a proxy/relay service** between the local MCP on your machine and a publicly accessible URL. It doesn't process any data itself - it simply forwards requests and responses.

**How It Works:**
```
External Tool → Remote URL → Relay/Proxy → Local MCP Server → LocalBrain
                (Public)     (Bridge)       (Your Computer)
```

This allows your local MCP to be used anywhere a remote MCP URL is accepted (ChatGPT, Claude, custom tools, etc.).

## Purpose

Enable external access to your LocalBrain instance without:
- Port forwarding or network configuration
- Exposing your home IP address
- Complex VPN setup
- Cloud hosting requirements

## Architecture

**Simple Relay Model:**
1. **Remote URL**: Public endpoint (e.g., `https://mcp.localbrain.app/u/[user-id]`)
2. **Secure Tunnel**: WebSocket or HTTP connection to your local machine
3. **Request Forwarding**: Bridge relays requests to local MCP
4. **Response Return**: Bridge sends local MCP responses back to external tool

**What the Bridge Does:**
- Accept requests at public URL
- Authenticate API keys
- Forward requests to local MCP via tunnel
- Return responses to requester
- Rate limiting and abuse prevention

**What the Bridge Does NOT Do:**
- Store your data or queries
- Process or analyze content
- Cache responses
- Access your files directly

## Security

**Authentication:**
- API key required for all remote requests
- Unique user-specific URLs
- Per-tool access tokens (optional)
- Revokable at any time

**Encryption:**
- TLS/SSL for all connections
- Encrypted WebSocket tunnel to local machine
- No plaintext data transmission
- End-to-end request/response security

**Privacy:**
- No data stored on remote server
- All processing happens locally on your machine
- Full audit logging of remote access
- Disable anytime with one click

## Setup

1. **Enable Remote Bridge** in LocalBrain settings
2. **Generate API Key** for authentication
3. **Start Tunnel** to establish connection
4. **Get Remote URL** to use in external tools
5. **Configure Access** (which tools are available remotely)

**Example Configuration:**
```json
{
  "remoteBridge": {
    "enabled": true,
    "apiKey": "lb_xxxxxxxxxxxxx",
    "remoteUrl": "https://mcp.localbrain.app/u/abc123",
    "allowedTools": ["search", "summarize", "list"]
  }
}
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

**Connection Types:**
- WebSocket (preferred): Real-time bidirectional tunnel
- HTTP Long-Polling (fallback): For restrictive networks
- Server-Sent Events: For streaming responses

**Deployment Options:**
- **Hosted Service**: Official LocalBrain relay servers
- **Self-Hosted**: Run your own bridge on VPS or cloud
- **Docker**: Containerized deployment
- **Open Source**: Full bridge code available

## Privacy & Control

**Complete Transparency:**
- View all remote requests in audit dashboard
- See which tools are accessing your data
- Monitor request frequency and patterns
- Export access logs

**Full Control:**
- Enable/disable with one click
- Revoke API keys instantly
- Whitelist specific tools or IP addresses
- Set rate limits per tool

**Offline First:**
- LocalBrain works fully without remote bridge
- Bridge is completely optional
- No degradation of local functionality
- All data stays local unless explicitly accessed

## Future Enhancements

**Advanced Relay Features:**
- Multiple device sync through bridge
- Load balancing for high availability
- Custom domain support
- Geographic routing options
- Advanced caching strategies (with user consent)

**Security Improvements:**
- Two-factor authentication for setup
- IP whitelisting
- Request signing and verification
- Time-limited access tokens
- Custom encryption keys

This remote bridge is purely for convenience - LocalBrain is designed to work completely offline and locally without any cloud dependencies.