# LocalBrain MCP Architecture

**Status**: ✅ Clean, Pure Proxy Implementation (October 2025)

---

## System Overview

```
Claude Desktop
    ↓ stdio protocol
stdio_server.py  
    ↓ HTTP (port 8766)
MCP FastAPI Server (PURE PROXY)
    ↓ HTTP (port 8765)
Daemon (REAL BACKEND - agentic search)
    ↓
Vault Files
```

---

## Core Principle

**MCP is a PURE PROXY** - it does ZERO business logic.

- ✅ Translates formats (MCP ↔ Daemon)
- ✅ Handles authentication & audit
- ❌ NO search logic
- ❌ NO parameter processing
- ❌ NO filtering

**All intelligence lives in the daemon.**

---

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| **search** | Natural language search | `query` (string) only |
| **open** | Read full file contents | `file_path`, `include_metadata` |
| **summarize** | Generate file summaries | `file_path` or `content`, `max_length`, `style` |
| **list** | Browse directory structure | `path`, `recursive`, `file_types` |

### Search Tool (Pure Proxy)

**MCP receives**:
```json
{"query": "conferences attended"}
```

**MCP forwards to daemon**:
```http
POST http://127.0.0.1:8765/protocol/search
{"q": "conferences attended"}
```

**Daemon does the work**:
1. Calls Claude Haiku with agentic tools
2. Claude generates grep patterns: `conference|attended|event`
3. Daemon executes grep_vault with regex
4. Returns contexts

**MCP returns**:
```json
{
  "success": true,
  "data": {
    "query": "conferences attended",
    "results": [...],
    "total": 15
  }
}
```

**NO top_k, NO min_similarity, NO filters in MCP!**

---

## Components

### 1. stdio_server.py
- **Purpose**: Claude Desktop integration
- **Location**: `src/core/mcp/stdio_server.py`
- **Protocol**: stdio (stdin/stdout)
- **Tool Definitions**: Defines what Claude sees

**Critical**: This file gets copied into the `.mcpb` package.  
**To update**: Run `cd extension && bash package.sh`

### 2. MCP FastAPI Server
- **Purpose**: HTTP API with auth/audit
- **Location**: `src/core/mcp/server.py`
- **Port**: 8766
- **Endpoints**:
  - `POST /mcp/search`
  - `POST /mcp/open`
  - `POST /mcp/summarize`
  - `POST /mcp/list`
  - `GET /mcp/tools` - list available tools
  - `GET /mcp/stats` - audit statistics

### 3. MCPTools (Proxy Layer)
- **Purpose**: Format translation
- **Location**: `src/core/mcp/tools.py`
- **Responsibilities**:
  - Forward requests to daemon
  - Map field names (e.g., `file` → `file_path`)
  - Convert response format

### 4. Daemon (Real Backend)
- **Purpose**: All business logic
- **Location**: `src/daemon.py`
- **Port**: 8765
- **Capabilities**:
  - Agentic search (Claude + tools)
  - File operations
  - Auto-sync (Gmail, etc.)

---

## Recent Fixes

### 1. Removed search_agentic (October 2025)
**Before**: Two search tools
- `search` - semantic search
- `search_agentic` - structured search with filters

**After**: ONE search tool
- `search` - forwards to daemon's agentic search
- Daemon handles all query decomposition

**Reason**: Duplicate functionality, confusing for users

### 2. Removed top_k Parameter (October 2025)
**Before**:
```json
{"query": "test", "top_k": 15}
```

**After**:
```json
{"query": "test"}
```

**Reason**: Daemon doesn't support it. All result limiting happens in daemon.

### 3. Fixed grep_vault Regex (October 2025)
**Bug**: Fallback grep treated patterns as literal strings
```python
# BEFORE (broken):
if pattern.lower() in line.lower():  # 'a|b' treated as literal

# AFTER (fixed):
regex = re.compile(pattern, re.IGNORECASE)
if regex.search(line):  # 'a|b' works as OR
```

**Impact**: Patterns like `conference|event|workshop` now work correctly

### 4. Fixed Pydantic v2 Deprecations
- `.dict()` → `.model_dump()`
- `.schema()` → `.model_json_schema()`

---

## Development Workflow

### Making Changes

1. **Edit Python files** in `src/core/mcp/`
2. **Rebuild extension**:
   ```bash
   cd src/core/mcp/extension
   bash package.sh
   ```
3. **Restart Claude Desktop** (to reload extension)
4. **Restart backend**:
   ```bash
   cd electron
   npm run dev
   ```

### Testing

**Test daemon directly**:
```bash
curl -X POST http://127.0.0.1:8765/protocol/search \
  -H "Content-Type: application/json" \
  -d '{"q":"conference"}'
```

**Test MCP endpoint**:
```bash
curl -X POST http://127.0.0.1:8766/mcp/search \
  -H "X-API-Key: dev-key-local-only" \
  -H "Content-Type: application/json" \
  -d '{"query":"conference"}'
```

**Test with Claude**:
Ask: "search for conferences attended"

---

## Configuration

### Vault Path
Configured in: `~/.localbrain/config.json`
```json
{
  "vault_path": "/path/to/test-vault",
  "port": 8765
}
```

### MCP Settings
- **Port**: 8766 (hardcoded in `config.py`)
- **Auth**: API key in `~/.localbrain/mcp/clients.json`
- **Default key**: `dev-key-local-only` (dev only!)

---

## File Structure

```
electron/backend/src/core/mcp/
├── server.py              # FastAPI server (port 8766)
├── tools.py               # Proxy layer - forwards to daemon
├── models.py              # Pydantic models (SearchRequest, etc.)
├── stdio_server.py        # Claude Desktop bridge
├── auth.py                # API key authentication
├── audit.py               # Request logging
├── config.py              # Configuration management
├── protocol_handler.py    # localbrain:// URL handler (unused)
├── extension/
│   ├── manifest.json      # Extension metadata
│   ├── package.sh         # Build script
│   ├── server/
│   │   └── stdio_server.py  # Copied here by package.sh
│   └── localbrain.mcpb    # Built package
└── *.md                   # Documentation
```

---

## Debugging

### Search returns 0 results

**Check**:
1. Is ripgrep installed? `which rg`
2. Does daemon return results? Test with curl
3. Is vault path correct? Check `~/.localbrain/config.json`
4. Are there actually matching files? `grep -r "keyword" /path/to/vault`

### Claude can't see tools

**Fix**:
1. Rebuild extension: `cd extension && bash package.sh`
2. Remove cached extension:
   ```bash
   rm -rf ~/Library/Application\ Support/Claude/Claude\ Extensions/local.mcpb.localbrain.localbrain
   ```
3. Restart Claude Desktop
4. Reinstall extension (drag .mcpb file)

### MCP server won't start

**Check**:
1. Is port 8766 in use? `lsof -i:8766`
2. Is daemon running? `curl http://127.0.0.1:8765/health`
3. Check logs in terminal

---

## Performance

**Benchmark** (longmemeval test suite):
- **Retrieval Rate**: 95% (19/20 questions)
- **Average Response Time**: 2-4 seconds
- **Agentic Iterations**: 2-4 per query

**Why fast**:
- Regex grep is instant (<100ms)
- Claude Haiku is fast (~500ms per call)
- Parallel tool execution when possible

---

## Future Improvements

**NOT PLANNED** (keep it simple):
- ❌ Caching in MCP layer
- ❌ Query rewriting in MCP
- ❌ Result ranking in MCP

**MAYBE CONSIDER**:
- Install ripgrep automatically
- Better error messages
- Health check endpoint that tests full stack

---

## Summary

**MCP is a pure HTTP proxy**:
1. Receives requests from Claude (via stdio)
2. Forwards to daemon at port 8765
3. Returns response

**That's it. Nothing fancy. It works.** ✅
