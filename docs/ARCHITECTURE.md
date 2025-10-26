# LocalBrain Architecture

**System design and component overview**

---

## System Overview

LocalBrain is a three-tier architecture:

1. **Frontend** - Next.js web app & Electron desktop
2. **Daemon** - FastAPI backend with agentic search
3. **MCP Server** - Claude Desktop integration layer

```
┌────────────────────────────────────────────┐
│           Frontend (Port 3000)              │
│  • Next.js web interface                   │
│  • Search UI, vault browser                │
│  • Connector management                    │
└────────────┬───────────────────────────────┘
             │ HTTP
┌────────────▼───────────────────────────────┐
│       Daemon Backend (Port 8765)           │
│  • Agentic Search Engine                  │
│  • Connector Manager (plugins)             │
│  • Ingestion Pipeline                      │
│  • File Operations                         │
└────────────┬───────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼──────┐   ┌──────▼────────┐
│  Vault   │   │  Connectors   │
│ (Markdown)│  │ (Gmail, etc.) │
└──────────┘   └───────────────┘
```

Separate MCP server (port 8766) acts as a pure proxy for Claude Desktop integration.

---

## Core Components

### 1. Daemon (`daemon.py`)

**Main backend service** that runs continuously.

**Responsibilities:**
- Handle search requests
- Manage connectors
- Coordinate ingestion
- Serve REST API

**Key Endpoints:**
- `POST /protocol/search` - Agentic search
- `GET /file/{filepath}` - File operations
- `GET /list/{path}` - Directory listing
- `GET /connectors` - Connector management

### 2. Agentic Search (`agentic_search.py`)

**Intelligent search engine** powered by Claude.

**How it works:**
1. User submits natural language query
2. Claude generates grep patterns
3. Execute searches across vault
4. Claude reads relevant files
5. Synthesize answer with citations

**Tools available to Claude:**
- `grep_vault(pattern)` - Search markdown files
- `read_file(filepath)` - Read full files
- Extract and return relevant contexts

**Performance:**
- 2-4 second response time
- 95% retrieval accuracy
- 2-4 Claude API calls per query

### 3. Connector System (`connectors/`)

**Plugin architecture** for external data sources.

**Base Interface:**
```python
class BaseConnector(ABC):
    def get_metadata() -> ConnectorMetadata
    def has_updates(since) -> bool
    def fetch_updates(since, limit) -> List[ConnectorData]
    def get_status() -> ConnectorStatus
```

**Auto-Discovery:**
- Drop connector in `connectors/<name>/`
- Manager discovers on startup
- Generic API routes auto-generated

**Available Connectors:**
- Gmail (OAuth 2.0)
- Discord (Bot token)
- Browser History
- Calendar
- More coming soon!

### 4. Ingestion Pipeline (`agentic_ingest.py`)

**Multi-stage processing** for incoming content.

**Stages:**
1. **Chunking** - Split into digestible pieces
2. **Summarization** - Extract key information
3. **Metadata** - Extract dates, entities, etc.
4. **Citations** - Track source references
5. **Storage** - Save to vault

**Output:** Markdown files with frontmatter metadata.

### 5. MCP Server (`core/mcp/`)

**Claude Desktop integration** via Model Context Protocol.

**Architecture:**
```
Claude Desktop
    ↓ stdio
stdio_server.py
    ↓ HTTP (8766)
MCP FastAPI Server (auth, audit)
    ↓ HTTP (8765)
Daemon Backend (real logic)
```

**Pure Proxy Design:**
- No business logic in MCP layer
- Just auth, audit, format translation
- All intelligence in daemon

**Tools Exposed:**
- `search` - Natural language search
- `open` - Read files
- `summarize` - Generate summaries
- `list` - Browse directories

---

## Data Flow

### Search Query

```
1. User: "Find emails about internships"
   ↓
2. Daemon receives query
   ↓
3. Claude generates grep patterns
   "internship|application|job|position"
   ↓
4. Execute grep_vault tool
   Returns: ['career/job-search.md', 'emails/nvidia.md']
   ↓
5. Claude reads relevant files
   ↓
6. Claude synthesizes answer
   "You applied to NVIDIA for ML internship..."
   ↓
7. Return contexts + citations
```

### Connector Sync

```
1. Auto-sync timer triggers (every 10 min)
   ↓
2. ConnectorManager.sync_all()
   ↓
3. For each connected connector:
   - Check has_updates()
   - Fetch new data
   - Convert to ConnectorData format
   - Save to vault as markdown
   ↓
4. Log results
```

### File Ingestion

```
1. New file added to vault
   ↓
2. Ingestion pipeline processes:
   - Extract metadata
   - Chunk content
   - Generate summaries
   - Extract citations
   ↓
3. Enhanced markdown saved
```

---

## Technology Stack

### Backend
- **FastAPI** - REST API framework
- **Python 3.10+** - Core language
- **Claude Haiku** - Agentic search LLM
- **asyncio** - Async operations

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **TailwindCSS** - Styling
- **Electron** - Desktop app

### Storage
- **Markdown Files** - Vault content
- **JSON** - Configuration
- **SQLite** - (Optional) ChromaDB

### External Services
- **Anthropic API** - Claude access
- **Gmail API** - Email sync
- **Discord API** - Message sync

---

## Security Model

### Authentication
- API keys for daemon access
- OAuth 2.0 for Gmail
- Bot tokens for Discord
- Stored in `~/.localbrain/`

### Data Privacy
- All data stored locally
- No cloud storage (except external APIs)
- User controls what gets synced
- Credentials encrypted at rest

### Network
- CORS-enabled for localhost
- No external access by default
- API keys required for daemon
- MCP auth for Claude Desktop

---

## Performance Characteristics

### Search
- **Cold start**: 2-4 seconds
- **Cached**: <1 second (if implemented)
- **Scalability**: Linear with vault size
- **Bottleneck**: Claude API calls

### Connectors
- **Sync frequency**: 10 minutes
- **Sync time**: 1-10 seconds per connector
- **Rate limits**: Respects API limits
- **Incremental**: Only fetches new data

### Storage
- **Vault size**: Unlimited (filesystem)
- **File format**: Markdown (human-readable)
- **Metadata**: YAML frontmatter
- **No database required**

---

## Deployment Models

### Local Development
```bash
# Start backend
python src/daemon.py

# Start frontend (separate terminal)
npm run dev
```

### Desktop App
```bash
# Build Electron app
npm run build
npm run package
```

### Server Deployment
```bash
# Run as systemd service
systemctl start localbrain-daemon

# Nginx reverse proxy for frontend
# Expose on local network only
```

---

## Extensibility

### Adding Connectors
1. Implement `BaseConnector` interface
2. Drop in `connectors/<name>/`
3. Auto-discovered on startup

### Adding Search Tools
1. Add function to `agentic_search.py`
2. Register in tools list
3. Claude can now use it

### Custom Ingestion
1. Extend `AgenticIngestionPipeline`
2. Add custom processing stages
3. Configure in daemon startup

---

## Future Architecture

### Planned Improvements
- **Caching layer** - Redis for search results
- **Vector database** - Optional for semantic search
- **Multi-user** - Support for shared vaults
- **Real-time sync** - WebSocket for live updates
- **Mobile app** - iOS/Android clients

### Scaling Considerations
- Horizontal: Multiple daemon instances
- Vertical: Faster grep (ripgrep)
- Caching: Aggressive result caching
- Async: More concurrent operations

---

## Design Principles

1. **Local-first** - Your data stays on your machine
2. **Markdown-native** - Human-readable storage
3. **Plugin architecture** - Easy to extend
4. **Pure proxy** - Separation of concerns
5. **Production-ready** - Clean, maintainable code

---

## Related Documentation

- [Search System](SEARCH.md) - Agentic search details
- [Connectors](CONNECTORS.md) - Plugin system
- [MCP Integration](MCP.md) - Claude Desktop
- [API Reference](API.md) - REST endpoints
