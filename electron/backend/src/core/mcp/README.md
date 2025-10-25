# Local MCP Server

Provides a Model Context Protocol (MCP) interface for external tools and integrations. Acts as a thin proxy layer that forwards MCP requests to the LocalBrain daemon backend.

## Implementation Status

✅ **COMPLETE** - Full MCP server implementation with proxy architecture, authentication, and audit logging.

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

### Prerequisites

**You must start the daemon first:**

```bash
cd electron/backend
python src/daemon.py
```

The daemon runs on `http://127.0.0.1:8765` by default.

### For REST API Access

```bash
# 1. Install dependencies
pip install fastapi uvicorn pydantic loguru httpx

# 2. Run MCP server
python -m src.core.mcp.server
```

MCP server will start on `http://127.0.0.1:8766` and proxy requests to daemon on port 8765.

### For Claude Desktop Integration

1. **Start the daemon** (see Prerequisites above)
2. **Start MCP server** (as above)
3. **Configure Claude Desktop**:
   - Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
   - Add LocalBrain server config (see `examples/claude_desktop_config.json`)
4. **Restart Claude Desktop** - Look for 🔨 hammer icon

See [USAGE.md - Claude Desktop Integration](./USAGE.md#claude-desktop-integration) for detailed setup.

## Features

- ✅ **Proxy Architecture** - Thin layer that forwards to daemon backend
- ✅ **REST API Server** - HTTP endpoints for programmatic access
- ✅ **Claude Desktop Integration** - Stdio wrapper for MCP protocol
- ✅ **5 MCP Tools** - search, search_agentic, open, summarize, list
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

**search_agentic**
- **MCP Endpoint**: `/mcp/search_agentic`
- **Daemon Endpoint**: `/protocol/search` (with structured params)
- **Purpose**: Structured search with specific parameters
- **Use Case**: Automated tools, batch processing

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
localbrain://search_agentic?keywords=internship,nvidia&days=7
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

## Future Enhancements

**Online MCP Proxy (Optional):**
- Remote URL endpoint for local MCP access
- Authentication and API key management
- Request forwarding to local MCP server
- Usage analytics and monitoring

**Advanced Tools:**
- **batch_search**: Multiple queries in single request
- **similarity**: Find related content and connections
- **timeline**: Search within date ranges
- **export**: Export content in various formats

## Integration Points

- **Frontend**: Route UI search requests through MCP interface
- **Protocol Handler**: Process localbrain:// URLs via MCP tools
- **Bridge Service**: Enforce access permissions and logging
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
  - `search_agentic` → `/protocol/search` with filters
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
# 1. Start daemon first
python src/daemon.py

# 2. In another terminal, run MCP server
python -m src.core.mcp.server

# 3. Test with curl
curl -X POST http://localhost:8766/mcp/search \
  -H "X-API-Key: dev-key-local-only" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
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
