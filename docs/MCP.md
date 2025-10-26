# Claude Desktop Integration (MCP)

**Use LocalBrain directly from Claude Desktop**

---

## Overview

LocalBrain provides a Model Context Protocol (MCP) extension for Claude Desktop. This allows Claude to search your vault, open files, and access your personal knowledge base during conversations.

---

## What is MCP?

Model Context Protocol is Anthropic's standard for connecting AI assistants to external tools and data sources. Think of it like plugins for Claude Desktop.

**With LocalBrain MCP, Claude can:**
- Search your vault using natural language
- Read specific files on request
- List directory contents
- Generate summaries of documents

---

## Installation

### 1. Build Extension

```bash
cd electron/backend/src/core/mcp/extension
bash package.sh
```

This creates `localbrain.mcpb`.

### 2. Install in Claude Desktop

1. Open Claude Desktop
2. Go to **Settings** → **Extensions**
3. Drag `localbrain.mcpb` into the window
4. Use default API key: `dev-key-local-only`
5. Enable the extension

### 3. Start Backend

```bash
cd electron
npm run dev
```

This starts:
- Daemon on port 8765
- MCP server on port 8766

---

## Using with Claude

### Search Your Vault

**You:** "Search my vault for information about internships"

**Claude:** Uses the `search` tool automatically
```
🔍 Searching vault...
Found 3 results:
- career/job-search.md: "Applied to NVIDIA for ML internship..."
- emails/recruiter-outreach.md: "Amazon internship opportunity..."
```

### Open Files

**You:** "Open my resume file"

**Claude:** Uses the `open` tool
```
📄 Opening career/resume.md...
[Shows file contents]
```

### List Files

**You:** "What files are in my projects directory?"

**Claude:** Uses the `list` tool
```
📂 projects/
  • localbrain.md
  • machine-learning-pipeline.md
  • weekend-project-ideas.md
```

---

## Available Tools

### search
Search vault using natural language.

**Example:**
```
Tool: search
Input: {"query": "machine learning projects"}
Output: [relevant contexts with citations]
```

### open
Read full contents of a file.

**Example:**
```
Tool: open
Input: {"file_path": "career/resume.md"}
Output: [complete file contents]
```

### list
Browse directory structure.

**Example:**
```
Tool: list
Input: {"path": "projects", "recursive": false}
Output: [list of files and directories]
```

### summarize
Generate summary of a document.

**Example:**
```
Tool: summarize
Input: {"file_path": "research/paper-notes.md", "style": "concise"}
Output: [brief summary]
```

---

## Architecture

```
Claude Desktop
    ↓ stdio protocol
stdio_server.py (Bridge)
    ↓ HTTP request
MCP Server (Port 8766)
    • Authentication
    • Audit logging
    • Format translation
    ↓ HTTP request
Daemon (Port 8765)
    • Agentic search
    • File operations
    • Business logic
    ↓
Your Vault
```

**MCP Server = Pure Proxy**
- No business logic
- Just auth, audit, routing
- All intelligence in daemon

---

## Configuration

### API Key

Default for development:
```
dev-key-local-only
```

For production, generate secure key:
```python
import secrets
api_key = secrets.token_urlsafe(32)
```

Store in `~/.localbrain/mcp/clients.json`.

### Vault Path

Set in `~/.localbrain/config.json`:
```json
{
  "vault_path": "/path/to/your/vault",
  "port": 8765
}
```

---

## Troubleshooting

### Claude Can't Find Extension

**Solution:**
1. Rebuild extension: `cd extension && bash package.sh`
2. Remove cache:
   ```bash
   rm -rf ~/Library/Application\ Support/Claude/Claude\ Extensions/local.mcpb.localbrain.localbrain
   ```
3. Restart Claude Desktop
4. Reinstall `.mcpb` file

### Search Returns Nothing

**Check:**
1. Is daemon running? `curl http://localhost:8765/health`
2. Is MCP server running? `curl http://localhost:8766/health`
3. Is vault path correct? Check `~/.localbrain/config.json`
4. Are there files in vault? `ls /path/to/vault`

### Connection Timeout

**Check:**
1. Firewall blocking localhost?
2. Ports 8765/8766 available? `lsof -i:8765`
3. Backend logs for errors

---

## Development

### Testing Extension

**Test search directly:**
```bash
curl -X POST http://localhost:8766/mcp/search \
  -H "X-API-Key: dev-key-local-only" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

**Test full stack:**
```bash
# Start backend
npm run dev

# Open Claude Desktop
# Ask: "Search my vault for test"
```

### Rebuilding

After code changes:
```bash
cd extension
bash package.sh
# Restart Claude Desktop
# Reinstall extension
```

---

## Security

### Authentication
- API key required for all requests
- Default key for development only
- Generate unique keys for production

### Data Privacy
- All data stays local
- No external transmission
- MCP server only accessible on localhost

### Audit Logging
- All requests logged
- Location: `~/.localbrain/logs/mcp/`
- Includes query, tool, timing, status

---

## Performance

**Typical Response Times:**
- Search: 2-4 seconds (agentic)
- Open: <50ms
- List: <50ms
- Summarize: 100-500ms

**Why Search is Slower:**
- Makes 2-4 Claude API calls
- Executes grep across vault
- Reads multiple files
- Worth it for accuracy!

---

## Limitations

### Current
- ❌ No write operations (read-only)
- ❌ No real-time updates
- ❌ Single vault per instance
- ❌ No collaborative features

### Planned
- ✅ File editing support
- ✅ Real-time sync
- ✅ Multiple vault support
- ✅ Sharing/collaboration

---

## Comparison to Other Extensions

### vs. File System Access
- **LocalBrain**: Semantic search, context-aware
- **File System**: Just file operations

### vs. Web Search
- **LocalBrain**: Personal knowledge, private
- **Web Search**: Public information

### vs. Code Interpreter
- **LocalBrain**: Knowledge retrieval
- **Code Interpreter**: Code execution

---

## Advanced Usage

### Custom Actions

Connectors can expose custom actions:

```python
# In your connector
def action_send_email(self, to: str, subject: str):
    # Custom logic
    pass
```

Call from Claude:
```
POST /connectors/gmail/action/send_email
{"to": "user@example.com", "subject": "Test"}
```

### Batch Operations

Search multiple queries:
```python
queries = ["internships", "job applications", "resume"]
for q in queries:
    search(q)
```

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) - System design
- [Search System](SEARCH.md) - How search works
- [API Reference](API.md) - REST endpoints
- [MCP Technical](../electron/backend/src/core/mcp/ARCHITECTURE.md) - Implementation details
