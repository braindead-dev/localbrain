# LocalBrain MCP Server - Usage Guide

Complete guide for setting up and using the LocalBrain Model Context Protocol (MCP) server.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration](#configuration)
3. [Running the Server](#running-the-server)
4. [API Reference](#api-reference)
5. [Protocol Handler](#protocol-handler)
6. [Authentication](#authentication)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Install Dependencies

```bash
cd electron/backend
pip install fastapi uvicorn pydantic loguru chromadb sentence-transformers
```

### 2. Set Up Environment

```bash
# Copy example environment file
cp src/core/mcp/examples/.env.example .env

# Edit .env with your configuration
vim .env
```

Required environment variables:
- `VAULT_PATH`: Path to your LocalBrain vault
- `CHROMA_API_KEY`: Your ChromaDB Cloud API key

### 3. Set Up Authentication (Optional)

```bash
# Copy example client config
mkdir -p ~/.localbrain/mcp
cp src/core/mcp/examples/clients.json ~/.localbrain/mcp/clients.json

# Edit client config to add your API keys
vim ~/.localbrain/mcp/clients.json
```

### 4. Run the Server

```bash
# From electron/backend directory
python -m src.core.mcp.server
```

The server will start on `http://127.0.0.1:8765` by default.

---

## Configuration

### Environment Variables

All configuration can be done via environment variables. See `examples/.env.example` for the complete list.

**Key Configuration Options:**

```bash
# Server
MCP_HOST=127.0.0.1          # Server host
MCP_PORT=8765               # Server port
MCP_TIMEOUT=30              # Request timeout (seconds)

# Tools
MCP_SEARCH_TOP_K=10         # Default search results
MCP_CACHE_ENABLED=true      # Enable caching
MCP_CACHE_TTL=300           # Cache TTL (seconds)

# Security
MCP_RATE_LIMIT=100          # Requests per hour
MCP_AUDIT_ENABLED=true      # Enable audit logging
```

### Client Authentication

Client configurations are stored in JSON format. See `examples/clients.json` for examples.

**Client Configuration Structure:**

```json
{
  "client_id": "my_app",
  "api_key": "lb_your_api_key_here",
  "permissions": [
    {
      "tool": "search",
      "allowed": true,
      "scope_restrictions": {
        "max_results": 100
      }
    }
  ],
  "rate_limit": 1000,
  "enabled": true
}
```

**Generating API Keys:**

```python
from src.core.mcp.auth import MCPAuthManager

# Generate a secure API key
api_key = MCPAuthManager.generate_api_key("my_client")
print(api_key)  # lb_abc123...
```

---

## Running the Server

### Development Mode

```bash
# Using Python module
python -m src.core.mcp.server

# Or directly
python src/core/mcp/server.py
```

### Production Mode (with Gunicorn)

```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn src.core.mcp.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8765
```

### As a Background Service (macOS)

Create a launch agent at `~/Library/LaunchAgents/com.localbrain.mcp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.localbrain.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>-m</string>
        <string>src.core.mcp.server</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/localbrain/electron/backend</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/localbrain-mcp.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/localbrain-mcp.out</string>
</dict>
</plist>
```

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.localbrain.mcp.plist
```

---

## API Reference

### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-15T10:30:00Z",
  "version": "1.0.0"
}
```

### List Available Tools

**Endpoint:** `GET /mcp/tools`

**Response:**
```json
{
  "tools": [
    {
      "name": "search",
      "description": "Natural language search across knowledge base",
      "input_schema": { ... }
    },
    ...
  ]
}
```

### Search Tool

**Endpoint:** `POST /mcp/search`

**Headers:**
```
X-API-Key: your_api_key_here
```

**Request Body:**
```json
{
  "query": "where did I apply for internships",
  "top_k": 10,
  "min_similarity": 0.5,
  "filters": {
    "platform": "Gmail",
    "date_from": "2024-01-01"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "where did I apply for internships",
    "processed_query": "where apply internships",
    "results": [
      {
        "chunk_id": "abc123",
        "text": "Applied to NVIDIA for ML internship...",
        "snippet": "Applied to NVIDIA for ML internship...",
        "file_path": "career/job-search.md",
        "similarity_score": 0.89,
        "final_score": 0.87,
        "platform": "Gmail",
        "timestamp": "2024-03-01T10:00:00Z",
        "chunk_position": 0,
        "source": {
          "platform": "Gmail",
          "url": null,
          "quote": "Applied to NVIDIA..."
        }
      }
    ],
    "total": 5,
    "took_ms": 45.2
  },
  "error": null,
  "took_ms": 45.2,
  "request_id": null
}
```

### Search Agentic Tool

**Endpoint:** `POST /mcp/search_agentic`

**Headers:**
```
X-API-Key: your_api_key_here
```

**Request Body:**
```json
{
  "keywords": ["internship", "nvidia"],
  "days": 30,
  "platform": "Gmail",
  "top_k": 10
}
```

### Open Tool

**Endpoint:** `POST /mcp/open`

**Request Body:**
```json
{
  "file_path": "career/job-search.md",
  "include_metadata": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "file_path": "career/job-search.md",
    "content": "# Job Search\n\nMy job search journey...",
    "metadata": {
      "name": "job-search.md",
      "path": "career/job-search.md",
      "size": 1024,
      "created": "2024-01-01T00:00:00Z",
      "modified": "2024-03-15T10:00:00Z",
      "file_type": "md"
    }
  },
  "error": null,
  "took_ms": 2.5
}
```

### Summarize Tool

**Endpoint:** `POST /mcp/summarize`

**Request Body:**
```json
{
  "file_path": "career/job-search.md",
  "max_length": 100,
  "style": "concise"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": "Applied to multiple tech companies for ML internships. Received offers from Startup X and Company Y...",
    "word_count": 85,
    "source": "career/job-search.md",
    "style": "concise"
  },
  "error": null,
  "took_ms": 15.3
}
```

### List Tool

**Endpoint:** `POST /mcp/list`

**Request Body:**
```json
{
  "path": "career",
  "recursive": false,
  "include_metadata": true,
  "file_types": ["md"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "path": "career",
    "items": [
      {
        "name": "job-search.md",
        "path": "career/job-search.md",
        "is_directory": false,
        "size": 1024,
        "modified": "2024-03-15T10:00:00Z",
        "file_type": "md"
      }
    ],
    "total_items": 1,
    "total_size": 1024
  },
  "error": null,
  "took_ms": 3.1
}
```

### Statistics

**Endpoint:** `GET /mcp/stats`

**Headers:**
```
X-API-Key: your_api_key_here
```

**Response:**
```json
{
  "statistics": {
    "total_requests": 1000,
    "successful_requests": 950,
    "failed_requests": 50,
    "success_rate": 0.95,
    "by_tool": {
      "search": 500,
      "search_agentic": 200,
      "open": 150,
      "summarize": 100,
      "list": 50
    },
    "by_client": {
      "local_electron": 800,
      "external_app": 200
    }
  },
  "performance": {
    "count": 1000,
    "avg_ms": 45.2,
    "min_ms": 2.1,
    "max_ms": 500.3,
    "p50_ms": 40.0,
    "p95_ms": 100.5,
    "p99_ms": 250.0
  }
}
```

---

## Protocol Handler

The MCP server supports `localbrain://` protocol URLs for easy integration.

### Protocol URL Format

```
localbrain://<tool>?<parameters>
```

### Examples

**Search:**
```
localbrain://search?q=internship+applications&top_k=10
```

**Search Agentic:**
```
localbrain://search_agentic?keywords=internship,nvidia&days=7&platform=Gmail
```

**Open File:**
```
localbrain://open?filepath=career/job-search.md
```

**Summarize:**
```
localbrain://summarize?filepath=finance/taxes.md&style=bullets
```

**List Directory:**
```
localbrain://list?path=projects&recursive=true
```

### Using the Protocol Handler

```python
from src.core.mcp.protocol_handler import ProtocolHandler
from src.core.mcp.tools import MCPTools

# Initialize
tools = MCPTools(vault_path="~/vault", retrieval_engine=engine)
handler = ProtocolHandler(tools_client=tools)

# Handle URL
url = "localbrain://search?q=test&top_k=5"
result = await handler.handle_url(url)
print(result)
```

### Building Protocol URLs

```python
from src.core.mcp.protocol_handler import ProtocolHandler

# Build search URL
url = ProtocolHandler.build_url("search", q="test query", top_k=10)
# Returns: localbrain://search?q=test+query&top_k=10

# Build open URL
url = ProtocolHandler.build_url("open", filepath="readme.md")
# Returns: localbrain://open?filepath=readme.md
```

---

## Authentication

### API Key Authentication

All requests (except `/health` and `/mcp/tools`) require an API key in the `X-API-Key` header.

**Example:**
```bash
curl -X POST http://localhost:8765/mcp/search \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

### Permission System

Each client has granular permissions for each tool:

```json
{
  "tool": "open",
  "allowed": true,
  "scope_restrictions": {
    "allowed_directories": ["career/", "projects/"],
    "allowed_file_types": ["md", "txt"]
  }
}
```

**Scope Restrictions:**
- `allowed_directories`: List of directories the client can access
- `allowed_file_types`: List of file extensions allowed
- `max_results`: Maximum number of results for search tools

### Rate Limiting

Each client has a configurable rate limit (requests per hour).

```json
{
  "client_id": "my_app",
  "rate_limit": 100,  // 100 requests per hour
  "enabled": true
}
```

**Rate Limit Response:**
```json
{
  "detail": "Rate limit exceeded: 100 requests per hour"
}
```

---

## Examples

### Python Client Example

```python
import httpx
from typing import Dict, Any

class LocalBrainClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}

    def search(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/mcp/search",
            headers=self.headers,
            json={"query": query, "top_k": top_k}
        )
        response.raise_for_status()
        return response.json()

    def open_file(self, file_path: str) -> str:
        response = httpx.post(
            f"{self.base_url}/mcp/open",
            headers=self.headers,
            json={"file_path": file_path}
        )
        response.raise_for_status()
        return response.json()["data"]["content"]

# Usage
client = LocalBrainClient("http://localhost:8765", "your_api_key")
results = client.search("internship applications")
print(results)
```

### JavaScript/TypeScript Client Example

```typescript
class LocalBrainClient {
  constructor(
    private baseUrl: string,
    private apiKey: string
  ) {}

  async search(query: string, topK: number = 10): Promise<any> {
    const response = await fetch(`${this.baseUrl}/mcp/search`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query, top_k: topK })
    });

    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }

    return response.json();
  }

  async openFile(filePath: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/mcp/open`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ file_path: filePath })
    });

    if (!response.ok) {
      throw new Error(`Open failed: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data.content;
  }
}

// Usage
const client = new LocalBrainClient('http://localhost:8765', 'your_api_key');
const results = await client.search('internship applications');
console.log(results);
```

### cURL Examples

```bash
# Search
curl -X POST http://localhost:8765/mcp/search \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"query": "internship applications", "top_k": 10}'

# Open file
curl -X POST http://localhost:8765/mcp/open \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "career/job-search.md"}'

# Summarize
curl -X POST http://localhost:8765/mcp/summarize \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "career/job-search.md", "style": "concise"}'

# List directory
curl -X POST http://localhost:8765/mcp/list \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"path": "career", "recursive": false}'
```

---

## Troubleshooting

### Server Won't Start

**Problem:** Server fails to start with connection error.

**Solution:**
1. Check that port is not already in use: `lsof -i :8765`
2. Verify environment variables are set correctly
3. Check ChromaDB credentials

### Authentication Errors

**Problem:** Getting 401 Unauthorized errors.

**Solution:**
1. Verify API key is correct
2. Check that API key is in `X-API-Key` header
3. Ensure client is enabled in `clients.json`

### Rate Limit Errors

**Problem:** Getting 429 Too Many Requests errors.

**Solution:**
1. Check client rate limit in `clients.json`
2. Wait for rate limit window to reset (1 hour)
3. Increase rate limit for your client

### Search Returns No Results

**Problem:** Search queries return empty results.

**Solution:**
1. Check that ChromaDB collection is populated
2. Verify vault path is correct
3. Lower `min_similarity` threshold
4. Try simpler query terms

### File Access Denied

**Problem:** Getting 403 Forbidden when opening files.

**Solution:**
1. Check that file path is within vault directory
2. Verify client has `open` permission
3. Check `allowed_directories` scope restriction
4. Ensure file exists in vault

### Logs

**Audit Logs Location:**
```
~/.localbrain/logs/mcp/mcp_audit_YYYY-MM-DD.jsonl
```

**View Recent Logs:**
```bash
tail -f ~/.localbrain/logs/mcp/mcp_audit_$(date +%Y-%m-%d).jsonl | jq
```

**Server Logs:**
Server logs are output to stdout/stderr. When running as a service, check:
```bash
# macOS LaunchAgent
cat /tmp/localbrain-mcp.out
cat /tmp/localbrain-mcp.err
```

---

## Claude Desktop Integration

The LocalBrain MCP server can be integrated with Claude Desktop to give Claude direct access to your knowledge base.

### Architecture

The system uses a **two-part architecture**:

1. **FastAPI Server** (`server.py`) - HTTP REST API for programmatic access
2. **Stdio Wrapper** (`stdio_server.py`) - MCP protocol adapter for Claude Desktop

The stdio wrapper forwards tool calls to the FastAPI server via HTTP.

### Setup Steps

#### 1. Install MCP SDK

```bash
cd electron/backend
pip install mcp>=1.0.0
```

#### 2. Start FastAPI Server

The FastAPI server must be running for Claude Desktop to work:

```bash
# Terminal 1: Start the FastAPI server
python -m src.core.mcp.server
```

Keep this running in the background or run it as a service (see "As a Background Service" section).

#### 3. Configure Claude Desktop

**macOS:**

1. Open Claude Desktop
2. Go to **Settings** → **Developer** → **Edit Config**
3. This opens `~/Library/Application Support/Claude/claude_desktop_config.json`

**Alternatively, edit directly:**

```bash
# macOS
vim ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Windows
notepad %APPDATA%\Claude\claude_desktop_config.json

# Linux
vim ~/.config/Claude/claude_desktop_config.json
```

**Add the LocalBrain configuration:**

```json
{
  "mcpServers": {
    "localbrain": {
      "command": "python",
      "args": [
        "/Users/YOUR_USERNAME/Projects/localbrain/electron/backend/src/core/mcp/stdio_server.py"
      ],
      "env": {
        "VAULT_PATH": "/Users/YOUR_USERNAME/Projects/localbrain/my-vault",
        "MCP_API_KEY": "dev-key-local-only",
        "MCP_BASE_URL": "http://127.0.0.1:8765"
      }
    }
  }
}
```

**IMPORTANT:**
- Replace `/Users/YOUR_USERNAME/...` with your **absolute paths**
- Use the same API key configured in `~/.localbrain/mcp/clients.json`
- Ensure `VAULT_PATH` points to your vault directory

**Example configuration file:** See `examples/claude_desktop_config.json`

#### 4. Restart Claude Desktop

Close and reopen Claude Desktop completely (not just the window).

#### 5. Verify Connection

Look for the **🔨 hammer icon** in the bottom-right corner of Claude Desktop. This indicates MCP servers are connected.

### Testing the Integration

In Claude Desktop, try these prompts:

**Search your knowledge base:**
```
Search my vault for "internship applications"
```

**List directory contents:**
```
List the files in my career/ folder
```

**Open a specific file:**
```
Open career/job-search.md
```

**Get a summary:**
```
Summarize my personal/goals.md file
```

**Structured search:**
```
Search for emails about "nvidia" from the last 30 days
```

### Available Tools in Claude Desktop

When connected, Claude has access to these tools:

1. **search** - Natural language semantic search
2. **search_agentic** - Structured search with filters
3. **open** - Read full file contents
4. **summarize** - Generate file summaries
5. **list** - Browse directory structure

### Troubleshooting Claude Desktop

**Issue: No hammer icon appears**

Solution:
1. Check Claude Desktop config file syntax (must be valid JSON)
2. Ensure paths are absolute, not relative
3. Restart Claude Desktop completely
4. Check Claude Desktop logs (Settings → Developer → View Logs)

**Issue: "Cannot connect to FastAPI server"**

Solution:
1. Verify FastAPI server is running: `curl http://localhost:8765/health`
2. Check server logs for errors
3. Ensure port 8765 is not blocked by firewall

**Issue: "Authentication failed"**

Solution:
1. Verify `MCP_API_KEY` in config matches `~/.localbrain/mcp/clients.json`
2. Check that client is `enabled: true` in clients.json
3. Ensure API key has proper permissions for all tools

**Issue: "VAULT_PATH does not exist"**

Solution:
1. Use absolute path (e.g., `/Users/username/vault`, not `~/vault`)
2. Ensure the directory exists
3. Check directory permissions (readable by current user)

### Configuration Examples

**Multiple Vaults:**

```json
{
  "mcpServers": {
    "localbrain-personal": {
      "command": "python",
      "args": ["/path/to/stdio_server.py"],
      "env": {
        "VAULT_PATH": "/Users/me/personal-vault",
        "MCP_API_KEY": "key1"
      }
    },
    "localbrain-work": {
      "command": "python",
      "args": ["/path/to/stdio_server.py"],
      "env": {
        "VAULT_PATH": "/Users/me/work-vault",
        "MCP_API_KEY": "key2",
        "MCP_BASE_URL": "http://127.0.0.1:8766"
      }
    }
  }
}
```

**With Python Virtual Environment:**

```json
{
  "mcpServers": {
    "localbrain": {
      "command": "/Users/me/Projects/localbrain/.venv/bin/python",
      "args": ["/Users/me/Projects/localbrain/electron/backend/src/core/mcp/stdio_server.py"],
      "env": {
        "VAULT_PATH": "/Users/me/my-vault",
        "MCP_API_KEY": "dev-key-local-only"
      }
    }
  }
}
```

### Debugging

**Enable verbose logging in stdio_server:**

Edit `stdio_server.py` and add at the top of `main()`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check FastAPI server health:**

```bash
curl http://localhost:8765/health
```

**Test stdio server directly:**

```bash
python src/core/mcp/stdio_server.py
# Then type: {"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}
# Press Ctrl+D
```

### Performance Tips

1. **Keep FastAPI server running** - Start it as a background service
2. **Use search filters** - Narrow results with platform/date filters
3. **Cache results** - Enable caching in MCP config (`MCP_CACHE_ENABLED=true`)
4. **Optimize queries** - Use specific keywords instead of long questions

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)

For issues and feature requests, please file an issue in the LocalBrain repository.
