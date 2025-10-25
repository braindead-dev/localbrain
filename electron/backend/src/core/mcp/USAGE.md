# LocalBrain MCP Usage Guide

**Quick Start**: See [ARCHITECTURE.md](./ARCHITECTURE.md) for system design.

---

## Available Tools

| Tool | Purpose | Example |
|------|---------|---------|
| **search** | Natural language search | "Find conference information" |
| **open** | Read file contents | Open specific files |
| **summarize** | Generate summaries | Summarize documents |
| **list** | Browse vault structure | List directory contents |

---

## Search Tool

**Pure proxy to daemon's agentic search** - just pass the query!

### Request

```bash
curl -X POST http://localhost:8766/mcp/search \
  -H "X-API-Key: dev-key-local-only" \
  -H "Content-Type: application/json" \
  -d '{"query": "conferences attended"}'
```

### Response

```json
{
  "success": true,
  "data": {
    "query": "conferences attended",
    "results": [
      {
        "file_path": "Personal/Travel/airline_and_ride_sharing.md",
        "text": "Las Vegas conference trip (March 15-18, 2023)...",
        "snippet": "Las Vegas conference trip..."
      }
    ],
    "total": 1
  }
}
```

**No additional parameters** - daemon handles everything!

---

## Open Tool

### Request

```bash
curl -X POST http://localhost:8766/mcp/open \
  -H "X-API-Key: dev-key-local-only" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "career/job-search.md",
    "include_metadata": true
  }'
```

### Response

```json
{
  "success": true,
  "data": {
    "file_path": "career/job-search.md",
    "content": "# Job Search\n\nMy notes...",
    "metadata": {
      "name": "job-search.md",
      "size": 1234,
      "modified": "2024-03-15T10:00:00Z"
    }
  }
}
```

---

## List Tool

### Request

```bash
curl -X POST http://localhost:8766/mcp/list \
  -H "X-API-Key: dev-key-local-only" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "",
    "recursive": false
  }'
```

### Response

```json
{
  "success": true,
  "data": {
    "path": "/",
    "items": [
      {"name": "Personal", "is_directory": true},
      {"name": "Work and Career", "is_directory": true}
    ],
    "total_items": 2
  }
}
```

---

## Summarize Tool

### Request

```bash
curl -X POST http://localhost:8766/mcp/summarize \
  -H "X-API-Key: dev-key-local-only" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "career/goals.md",
    "max_length": 200,
    "style": "concise"
  }'
```

### Response

```json
{
  "success": true,
  "data": {
    "summary": "Focus on ML engineering roles...",
    "word_count": 150,
    "source": "career/goals.md",
    "style": "concise"
  }
}
```

---

## Claude Desktop Integration

### 1. Build Extension

```bash
cd electron/backend/src/core/mcp/extension
bash package.sh
```

This creates `localbrain.mcpb`.

### 2. Install in Claude Desktop

1. Open Claude Desktop
2. Go to Settings → Extensions
3. Drag `localbrain.mcpb` into the window
4. Use default API key: `dev-key-local-only`
5. Enable the extension

### 3. Start Backend

```bash
cd electron
npm run dev
```

This starts both daemon (port 8765) and MCP server (port 8766).

### 4. Test

Ask Claude: "search for conferences attended"

---

## Authentication

### Default Dev Key

For local development, use:
```
X-API-Key: dev-key-local-only
```

### Production Keys

Create `~/.localbrain/mcp/clients.json`:

```json
{
  "clients": [
    {
      "client_id": "my-app",
      "api_key": "generated-secure-key",
      "permissions": [
        {"tool": "search", "allowed": true},
        {"tool": "open", "allowed": true},
        {"tool": "list", "allowed": true}
      ],
      "rate_limit": 100,
      "enabled": true
    }
  ]
}
```

Generate keys:
```python
import secrets
api_key = secrets.token_urlsafe(32)
```

---

## Troubleshooting

### Search returns 0 results

1. **Test daemon directly**:
   ```bash
   curl -X POST http://127.0.0.1:8765/protocol/search \
     -H "Content-Type: application/json" \
     -d '{"q":"test"}'
   ```

2. **Check vault path**:
   ```bash
   cat ~/.localbrain/config.json
   ```

3. **Verify files exist**:
   ```bash
   ls -la /path/to/vault
   ```

### Claude can't see extension

1. **Rebuild**:
   ```bash
   cd extension && bash package.sh
   ```

2. **Clear cache**:
   ```bash
   rm -rf ~/Library/Application\ Support/Claude/Claude\ Extensions/local.mcpb.localbrain.localbrain
   ```

3. **Restart Claude Desktop**

4. **Reinstall extension**

### Port already in use

```bash
# Kill existing processes
lsof -ti:8765 | xargs kill -9  # daemon
lsof -ti:8766 | xargs kill -9  # MCP
```

---

## Python Client Example

```python
import httpx

class LocalBrainClient:
    def __init__(self, api_key="dev-key-local-only"):
        self.base_url = "http://127.0.0.1:8766"
        self.headers = {"X-API-Key": api_key}
    
    def search(self, query: str):
        response = httpx.post(
            f"{self.base_url}/mcp/search",
            headers=self.headers,
            json={"query": query}
        )
        response.raise_for_status()
        return response.json()
    
    def open_file(self, file_path: str):
        response = httpx.post(
            f"{self.base_url}/mcp/open",
            headers=self.headers,
            json={"file_path": file_path, "include_metadata": True}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = LocalBrainClient()
results = client.search("conferences attended")
print(f"Found {results['data']['total']} results")
```

---

## Development

### File Structure

```
src/core/mcp/
├── server.py          # FastAPI server (port 8766)
├── tools.py           # Proxy to daemon
├── models.py          # Pydantic models
├── stdio_server.py    # Claude Desktop bridge
├── auth.py            # Authentication
├── audit.py           # Logging
├── config.py          # Configuration
└── extension/         # Package for distribution
    ├── package.sh     # Build script
    └── localbrain.mcpb  # Built package
```

### Making Changes

1. Edit Python files
2. Rebuild extension: `cd extension && bash package.sh`
3. Restart Claude Desktop
4. Restart backend: `npm run dev`

### Testing

**Full stack**:
```bash
# Ask Claude: "search for test"
```

**MCP only**:
```bash
curl -X POST http://127.0.0.1:8766/mcp/search \
  -H "X-API-Key: dev-key-local-only" \
  -d '{"query":"test"}'
```

**Daemon only**:
```bash
curl -X POST http://127.0.0.1:8765/protocol/search \
  -d '{"q":"test"}'
```

---

## Performance

**Typical response times**:
- Search: 2-4 seconds (includes Claude Haiku calls)
- Open: <50ms
- List: <50ms
- Summarize: 100-500ms

**Why search takes longer**:
- Agentic search calls Claude 2-4 times
- Each call: ~500ms-1s
- Grep execution: <100ms
- Worth it for 95% retrieval accuracy!

---

## See Also

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [README.md](./README.md) - Project overview
- [Extension.md](./Extension.md) - Extension packaging
- [MCP_FIX_COMPLETE.md](../../MCP_FIX_COMPLETE.md) - Recent fixes
