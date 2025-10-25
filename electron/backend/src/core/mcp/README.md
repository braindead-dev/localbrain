# Local MCP Server

Provides a Model Context Protocol (MCP) interface for external tools and integrations. Acts as a thin proxy layer that forwards MCP requests to the LocalBrain daemon backend.

## Implementation Status

✅ **COMPLETE** - Full MCP server implementation with proxy architecture, authentication, and audit logging.

## Access Options

The local MCP server provides two ways to access your LocalBrain:

### 1. Local Access (This Server)
- **Use case**: Claude Desktop, local tools, same machine
- **Port**: 8766 (localhost only)
- **Security**: Local API key authentication
- **Setup**: See Quick Start below

### 2. Remote Access (Optional Bridge)
- **Use case**: External tools, mobile apps, remote access
- **Location**: `remote-mcp/` directory at project root
- **Security**: WebSocket tunnel + multi-layer auth
- **Features**: Zero data storage, rate limiting, revocable access
- **Setup**: See [Remote MCP Bridge README](../../../../../remote-mcp/README.md)

**Choose local access for Claude Desktop and local tools. Use remote bridge only if you need external/mobile access.**

## Architecture

The MCP server is a **thin proxy layer** that:
1. Receives MCP protocol requests (HTTP or stdio)
2. Forwards them to the LocalBrain daemon backend (`daemon.py`)
3. Returns responses in MCP format

```
External Tools → MCP Server (auth/audit) → LocalBrain Daemon (core logic)
```

**Why this architecture?**
- Single source of truth: All tool implementations live in `daemon.py`
- No duplication: MCP server doesn't re-implement search, ingestion, etc.
- Simpler maintenance: Changes to core logic only need to happen in one place

## Quick Start

### Option 1: Start Both Servers with One Command (Recommended)

```bash
# From project root
python electron/backend/src/core/mcp/extension/start_servers.py

# Or navigate to extension directory
cd electron/backend/src/core/mcp/extension
python start_servers.py
```

This will:
- Start the daemon on `http://127.0.0.1:8765`
- Start the MCP server on `http://127.0.0.1:8766`
- Monitor both processes
- Stop both cleanly when you press Ctrl+C

### Option 2: Start Servers Manually

**You must start the daemon first:**

```bash
cd electron/backend
python src/daemon.py
```

The daemon runs on `http://127.0.0.1:8765` by default.

**Then start the MCP server (in another terminal):**

```bash
cd electron/backend
python -m src.core.mcp.server
```

By default:
- **Daemon** runs on `http://127.0.0.1:8765`
- **MCP Server** runs on `http://127.0.0.1:8766` and proxies to daemon

You can customize ports with environment variables:
```bash
DAEMON_PORT=8765 MCP_PORT=8766 python -m src.core.mcp.server
```

### For Claude Desktop Integration

**Claude Desktop will automatically start all servers when launched!**

1. **Configure Claude Desktop**:
   - Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
   - Add this configuration (update paths to match your system):

```json
{
  "mcpServers": {
    "localbrain": {
      "command": "python",
      "args": [
        "/absolute/path/to/localbrain/electron/backend/src/core/mcp/extension/start_servers.py",
        "--stdio"
      ],
      "env": {
        "VAULT_PATH": "/absolute/path/to/your/vault"
      }
    }
  }
}
```

2. **Restart Claude Desktop** - Look for 🔨 hammer icon

When Claude Desktop launches, it will automatically:
- Start the daemon backend (port 8765)
- Start the MCP HTTP server (port 8766)
- Connect via stdio bridge
- Clean up all servers when Claude Desktop closes

**Note:** Replace `/absolute/path/to/localbrain/` with your actual project path, and set `VAULT_PATH` to your vault directory.

See [USAGE.md - Claude Desktop Integration](./USAGE.md#claude-desktop-integration) for detailed setup.

## Features

- ✅ **Proxy Architecture** - Thin layer that forwards to daemon backend
- ✅ **REST API Server** - HTTP endpoints for programmatic access
- ✅ **Claude Desktop Integration** - Stdio wrapper for MCP protocol
- ✅ **4 MCP Tools** - search, open, summarize, list
- ✅ **Authentication & Authorization** - API key-based with granular permissions
- ✅ **Audit Logging** - Complete request/response tracking
- ✅ **Rate Limiting** - Per-client request throttling

See [USAGE.md](./USAGE.md) for complete documentation.

## Core Responsibilities

- **Protocol Translation**: Convert MCP requests to daemon API calls
- **Authentication**: Validate external tool permissions with API keys
- **Rate Limiting**: Prevent abuse and ensure performance
- **Audit Logging**: Complete request/response tracking
- **Response Formatting**: Structure daemon responses according to MCP specification

## MCP Tools → Daemon Mapping

All tool implementations live in `daemon.py`. The MCP server simply proxies requests:

**search**
- **MCP Endpoint**: `/mcp/search`
- **Daemon Endpoint**: `/protocol/search`
- **Purpose**: Natural language search across personal knowledge base
- **Use Case**: AI assistants, external search interfaces


**open**
- **MCP Endpoint**: `/mcp/open`
- **Daemon Endpoint**: `/file/{filepath}`
- **Purpose**: Retrieve full contents of specific files
- **Use Case**: External editors, backup systems

**summarize**
- **MCP Endpoint**: `/mcp/summarize`
- **Implementation**: Fetches file from daemon + simple extractive summary
- **Purpose**: Generate summaries of files or search results
- **Use Case**: Quick overview, content preview
- **Note**: Daemon doesn't have a summarize endpoint yet

**list**
- **MCP Endpoint**: `/mcp/list`
- **Daemon Endpoint**: `/list/{path}`
- **Purpose**: Browse directory structure and available files
- **Use Case**: File management, navigation

## Protocol Integration

**localbrain:// Command Processing:**
- Intercept and parse protocol URLs from external sources
- Route commands to appropriate MCP tools
- Format responses for protocol return values
- Handle authentication and permissions

**Deep Link Examples:**
```
localbrain://search?q=internship+applications
localbrain://open?filepath=career/job-search.md
localbrain://summarize?filepath=finance/taxes.md
localbrain://list?path=projects
```

## Security & Access Control

**Permission System:**
- **Bridge Settings**: User-configurable file access restrictions
- **Tool Permissions**: Granular control over which tools are available
- **Scope Limitations**: Restrict queries to specific directories or file types
- **Authentication**: Validate external tool credentials

**Audit Logging:**
- Complete record of all MCP requests and responses
- Timestamp, source, query, and result logging
- Performance metrics and error tracking
- Privacy-compliant logging (no sensitive data)

## Configuration

**Server Settings:**
- **Port Configuration**: HTTP/WebSocket server ports
- **CORS Policies**: Cross-origin request handling
- **Rate Limits**: Request throttling per endpoint
- **Timeout Settings**: Maximum processing time per request

**Tool Configuration:**
- **Search Parameters**: Default ranking and filtering options
- **File Access**: Allowed directories and file types
- **Response Limits**: Maximum results returned
- **Caching**: Response caching strategies

## Remote Access

**Remote MCP Bridge** ✅ **IMPLEMENTED**

For external access to your LocalBrain from anywhere (ChatGPT, mobile apps, remote devices):

- **Location**: `remote-mcp/` directory at project root
- **Architecture**: WebSocket tunnel + public bridge server
- **Security**: Multi-layer auth, rate limiting, zero data storage
- **Features**:
  - Access LocalBrain from any device/network
  - No port forwarding or VPN required
  - Complete control and privacy
  - Self-hosted or official hosted service (coming soon)

**Quick Start:**
```bash
cd remote-mcp
./start_bridge.sh    # Terminal 1: Start bridge
./start_tunnel.sh    # Terminal 2: Connect tunnel
```

**Documentation:**
- [Remote MCP README](../../../../../remote-mcp/README.md) - Overview
- [Remote MCP Quick Start](../../../../../remote-mcp/QUICKSTART.md) - 5-minute setup
- [Remote MCP Implementation](../../../../../remote-mcp/IMPLEMENTATION.md) - Complete guide
- [Remote MCP Architecture](../../../../../remote-mcp/ARCHITECTURE.md) - Technical details

**Important**: The remote bridge is completely optional. Local MCP works fully without it.

## Future Enhancements

**Advanced Tools:**
- **batch_search**: Multiple queries in single request
- **similarity**: Find related content and connections
- **timeline**: Search within date ranges
- **export**: Export content in various formats

**Remote Bridge Improvements** (see remote-mcp/ for full roadmap):
- Docker deployment
- Official hosted bridge service
- Custom domain support
- Advanced rate limiting and monitoring

## Integration Points

- **Frontend**: Route UI search requests through MCP interface
- **Claude Desktop**: Direct integration via stdio wrapper (see Extension.md)
- **Protocol Handler**: Process localbrain:// URLs via MCP tools
- **Remote Bridge**: Enable external access via WebSocket tunnels (see remote-mcp/)
- **External Tools**: Provide API access for third-party applications
- **Connectors**: Use MCP tools for data validation and processing

## Architecture

### File Structure

```
electron/backend/src/core/mcp/
├── __init__.py              # Package initialization
├── server.py                # FastAPI server implementation
├── tools.py                 # MCP tool implementations
├── models.py                # Pydantic models for requests/responses
├── auth.py                  # Authentication and authorization
├── audit.py                 # Audit logging system
├── config.py                # Configuration management
├── protocol_handler.py      # localbrain:// URL handler
├── README.md                # This file
├── USAGE.md                 # Complete usage documentation
└── examples/
    ├── .env.example         # Example environment configuration
    └── clients.json         # Example client authentication config
```

### Key Components

**Server (`server.py`):**
- FastAPI application with async support
- HTTP/WebSocket endpoints for all tools
- Middleware for CORS, authentication, rate limiting
- Global exception handling
- Startup/shutdown lifecycle management
- Proxies all tool requests to daemon backend

**Tools (`tools.py`):**
- **Proxy layer only** - no direct tool implementation
- Forwards requests to daemon backend via HTTP:
  - `search` → `/protocol/search`
  - `open` → `/file/{filepath}`
  - `summarize` → fetches file + simple summary
  - `list` → `/list/{path}`
- Translates MCP request/response formats to/from daemon API

**Authentication (`auth.py`):**
- API key-based authentication
- Per-tool permission system
- Scope restrictions (directories, file types, result limits)
- Rate limiting per client
- Client management (add, remove, update)

**Audit Logging (`audit.py`):**
- Complete request/response logging
- Performance metrics tracking
- Privacy-compliant (sanitized queries)
- Daily log rotation with configurable retention
- Queryable log history (by client, tool, date)

**Configuration (`config.py`):**
- Pydantic-based configuration models
- Environment variable support
- JSON config file support
- Validation and defaults
- Daemon URL configuration

**Protocol Handler (`protocol_handler.py`):**
- Parse `localbrain://` URLs
- Convert to MCP requests
- Build protocol URLs programmatically

## Development

**MCP Specification Compliance:**
- Standard MCP protocol implementation
- Tool discovery and capability advertising
- Error handling and status reporting
- Proxy architecture for simplified tool additions

**Testing:**
```bash
# 1. Start daemon first (port 8765)
cd electron/backend
python src/daemon.py

# 2. In another terminal, run MCP server (port 8766)
cd electron/backend
python -m src.core.mcp.server

# 3. Test with curl (use MCP server port 8766)
curl -X POST http://localhost:8766/mcp/search \
  -H "X-API-Key: dev-key-local-only" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

**Adding New Tools:**

The MCP server is a thin proxy, so most changes happen in `daemon.py`:

1. **Add endpoint to `daemon.py`** - Implement the actual tool logic there
2. **Add proxy method to `tools.py`** - Forward MCP request to daemon endpoint
3. **Add request/response models to `models.py`** (if needed)
4. **Add endpoint to `server.py`** - Wire up the FastAPI route
5. **Update authentication in `auth.py`** - Add permission config
6. **Update README.md** - Document the new tool

**Example: Adding a new "tags" tool**

1. In `daemon.py`, add `/tags/{filepath}` endpoint
2. In `tools.py`, add `async def tags(request)` that calls daemon
3. In `server.py`, add `/mcp/tags` FastAPI endpoint
4. Document in README

**Security Considerations:**
- Always use HTTPS in production
- Rotate API keys regularly
- Set appropriate rate limits
- Review audit logs for suspicious activity
- Limit scope restrictions to minimum required access
- Keep dependencies updated
- Ensure daemon is not exposed publicly (localhost only)
