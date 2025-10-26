# LocalBrain Backend

FastAPI backend service with agentic search, connector system, and MCP integration.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure vault
echo '{"vault_path": "/path/to/vault", "port": 8765}' > ~/.localbrain/config.json

# Set API key
export ANTHROPIC_API_KEY="your-key"

# Start daemon
python src/daemon.py
```

Server runs on **http://localhost:8765**

---

## Key Components

### daemon.py
Main service - handles all requests

### agentic_search.py
Intelligent search using Claude + tools

### connectors/
Plugin system for external data sources
- Gmail
- Discord  
- Browser History
- Easy to add more!

### core/mcp/
Claude Desktop integration (MCP protocol)

---

## API Endpoints

### Search
```bash
POST /protocol/search
Body: {"q": "your query"}
```

### File Operations
```bash
GET /file/{filepath}
GET /list/{path}
```

### Connectors
```bash
GET /connectors
POST /connectors/{id}/sync
GET /connectors/{id}/status
```

See [API docs](../../docs/API.md) for complete reference.

---

## Testing

```bash
# Unit tests
pytest

# Test search
curl -X POST http://localhost:8765/protocol/search \
  -d '{"q": "test"}'
```

---

## Configuration

**Config file**: `~/.localbrain/config.json`
```json
{
  "vault_path": "/Users/you/vault",
  "port": 8765,
  "auto_start": false
}
```

**Environment**:
- `ANTHROPIC_API_KEY` - Required for search
- `MCP_API_KEY` - For MCP server (default: dev-key-local-only)

---

## Architecture

See [Architecture docs](../../docs/ARCHITECTURE.md) for detailed design.

**Key principles:**
- Agentic search (Claude + tools)
- Plugin-based connectors
- Pure proxy MCP layer
- Local-first storage
