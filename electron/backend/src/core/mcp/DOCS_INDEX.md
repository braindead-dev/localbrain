# LocalBrain MCP Documentation Index

**Last Updated**: October 25, 2025  
**Status**: ✅ Clean, up-to-date, pure proxy architecture

---

## Documentation Files

### 📚 Current & Up-to-Date

| File | Purpose | Status |
|------|---------|--------|
| **ARCHITECTURE.md** | System design, components, debugging | ✅ Current |
| **USAGE.md** | API reference, examples, troubleshooting | ✅ Current |
| **README.md** | Project overview, quick start | ✅ Current |
| **Extension.md** | Claude Desktop extension guide | ✅ Current |
| **MCP_FIX_COMPLETE.md** | Recent bug fixes (Oct 2025) | ✅ Current |
| **INSTALL.md** | Extension installation steps | ✅ Current |

### 🗄️ Archived (Old)

| File | Status | Note |
|------|--------|------|
| **USAGE_OLD.md** | ⚠️ Archived | Had outdated search_agentic references |

---

## Quick Navigation

### Getting Started
1. Read **README.md** - Overview
2. Read **ARCHITECTURE.md** - Understand the system
3. Read **USAGE.md** - Learn the API
4. Read **Extension.md** - Set up Claude Desktop

### Development
- **ARCHITECTURE.md** → System design
- **tools.py** → Proxy implementation
- **models.py** → Data structures

### Troubleshooting
- **USAGE.md** → Common issues
- **ARCHITECTURE.md** → Debugging guide

---

## What Changed (October 2025)

### Removed
- ❌ `search_agentic` tool (was duplicate)
- ❌ `top_k` parameter (backend doesn't support it)
- ❌ `min_similarity` parameter (not used)
- ❌ All MCP-layer filtering (daemon does it all)

### Fixed
- ✅ grep_vault regex matching
- ✅ Pydantic v2 deprecations
- ✅ Search returning 0 results

### Architecture
- ✅ Pure proxy - NO business logic in MCP
- ✅ All intelligence in daemon
- ✅ Single search tool with agentic backend

---

## Core Principles

1. **MCP is a pure proxy** - zero business logic
2. **Daemon has all the intelligence** - agentic search, file ops
3. **One search tool** - forwards to daemon's agentic search
4. **Simple is better** - minimal parameters, maximum clarity

---

## File Locations

```
electron/backend/
├── src/core/mcp/           # MCP server code
│   ├── *.md               # Documentation (THIS)
│   ├── server.py          # FastAPI server
│   ├── tools.py           # Proxy layer
│   ├── models.py          # Data models
│   ├── stdio_server.py    # Claude Desktop bridge
│   └── extension/         # Packaging
│       ├── package.sh     # Build script
│       └── localbrain.mcpb  # Built package
├── src/daemon.py          # REAL backend (port 8765)
├── src/agentic_search.py  # Search implementation
└── MCP_FIX_COMPLETE.md    # Bug fix summary
```

---

## When to Read Each Doc

### I want to...

**Understand the architecture**  
→ Read **ARCHITECTURE.md**

**Use the API programmatically**  
→ Read **USAGE.md** → API examples

**Install the Claude Desktop extension**  
→ Read **Extension.md** or **INSTALL.md**

**Debug search issues**  
→ Read **ARCHITECTURE.md** → Debugging section

**Add a new tool**  
→ Read **ARCHITECTURE.md** → Development section

**See what was fixed recently**  
→ Read **MCP_FIX_COMPLETE.md**

---

## Documentation Style

All docs follow these principles:
- ✅ Clear, concise examples
- ✅ Current code only (no legacy references)
- ✅ Accurate curl commands that work
- ✅ Real file paths and structure
- ❌ No outdated parameter references
- ❌ No removed tools/features

---

## Maintenance

When making changes:

1. **Update code** → Make your changes
2. **Update ARCHITECTURE.md** → If system design changed
3. **Update USAGE.md** → If API changed
4. **Update this file** → Document what changed

**Don't update** README.md unless major features added/removed.

---

## Questions?

- System design? → **ARCHITECTURE.md**
- API usage? → **USAGE.md**  
- Installation? → **Extension.md**
- Everything else? → **README.md**
