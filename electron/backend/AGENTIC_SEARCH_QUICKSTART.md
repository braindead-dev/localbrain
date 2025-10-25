# Agentic Search - Quick Start

OpenCode-inspired retrieval. NO embeddings. Just ripgrep + LLM.

---

## What You Got

✅ **`localbrain://agentic_search`** - Protocol support  
✅ **Tool-based retrieval** - LLM decides what to search/read  
✅ **Ripgrep integration** - Blazingly fast file search  
✅ **Recent = relevant** - Sort by modification time  
✅ **No setup** - Works immediately, no indexing  

---

## Quick Test

### 1. Start Daemon

```bash
# From Electron (auto-starts daemon)
cd electron && npm run dev

# OR manually
cd backend
conda activate localbrain
python src/daemon.py
```

### 2. Test Via Protocol

```bash
open "localbrain://agentic_search?query=What%20was%20my%20Meta%20offer?"
```

### 3. Test Via API

```bash
curl -X POST http://localhost:8765/protocol/agentic_search \
  -H "Content-Type: application/json" \
  -d '{"query": "What was my Meta offer?"}'
```

### 4. Test Via Script

```bash
cd backend
python scripts/test_agentic_search.py "What was my Meta offer?"
```

---

## How It Works

```
You: "What was my Meta offer?"
  ↓
LLM: "Let me search for 'Meta offer'"
  ↓
Tool: grep_vault("Meta.*offer") → ["offers/meta.md"]
  ↓
LLM: "Let me read that file"
  ↓
Tool: read_file("offers/meta.md") → {content: "..."}
  ↓
LLM: "Based on the file, here's the answer..."
  ↓
Answer: "Meta offered $160k base, $40k sign-on..."
```

**The LLM orchestrates everything. You just ask questions.**

---

## Example Queries

```bash
# Simple lookup
open "localbrain://agentic_search?query=What%20courses%20did%20I%20take?"

# Multi-file synthesis  
open "localbrain://agentic_search?query=Compare%20all%20my%20job%20offers"

# Exploration
open "localbrain://agentic_search?query=What%20projects%20did%20I%20work%20on?"

# Time-based
open "localbrain://agentic_search?query=What%20did%20I%20do%20last%20week?"
```

---

## Why No Embeddings?

### OpenCode Proved It

OpenCode searches **massive codebases** (100k+ files) without embeddings:
- Uses ripgrep (~100ms for entire codebase)
- LLM decides what to read
- Sorts by modification time (recent = relevant)
- **Faster than embeddings** (no indexing overhead)

### For LocalBrain

Your vault is **tiny** compared to codebases OpenCode handles:
- 1000 markdown files = ~10-50MB
- Ripgrep searches in **50-100ms**
- No indexing delay
- No stale indexes
- No vector database

**Just grep + LLM is enough. Simpler and faster.**

---

## Speed Comparison

### With Embeddings
```
Initial setup: 5-10 minutes (indexing)
Query time: ~600ms
  - Generate query embedding: ~200ms
  - Vector search: ~100ms
  - LLM synthesis: ~300ms
Freshness: Stale (reindex on changes)
Storage: GBs of vectors
```

### With Agentic Search
```
Initial setup: 0 seconds
Query time: ~1-2 seconds
  - Grep: 50-100ms
  - LLM + tools: ~1-2s (includes synthesis)
Freshness: Always fresh
Storage: 0 extra
```

**Slightly slower per query, but:**
- ✅ No setup time
- ✅ No reindexing
- ✅ Always fresh
- ✅ Much simpler

---

## Tools Available

### 1. grep_vault(pattern, limit=20)

```python
# LLM calls
grep_vault(pattern="Meta.*offer", limit=10)

# Returns
{
  "matches": [
    {
      "file": "offers/meta.md",
      "preview": "Meta offered $160k base salary..."
    }
  ],
  "count": 1
}
```

**Features:**
- Regex support (uses ripgrep)
- Sorted by modification time
- Includes preview snippets
- Fast (~50-100ms for 1000 files)

### 2. read_file(filepath)

```python
# LLM calls
read_file(filepath="offers/meta.md")

# Returns
{
  "filepath": "offers/meta.md",
  "content": "# Meta Offer\n\nBase: $160k...",
  "citations": {...},
  "length": 1234
}
```

**Features:**
- Reads full file
- Includes citations from .json
- Safe (can't access files outside vault)

---

## Logs

All searches logged:

```bash
tail -f /tmp/localbrain-daemon.log
```

Example output:
```
2024-10-25 04:00:00 - INFO - 🔍 Agentic search: What was my Meta offer?
2024-10-25 04:00:00 - INFO -   🔧 Tool call: grep_vault({'pattern': 'Meta.*offer'})
2024-10-25 04:00:01 - INFO -   🔧 Tool call: read_file({'filepath': 'offers/meta.md'})
2024-10-25 04:00:02 - INFO - ✅ Search complete (2 iterations)
```

---

## Configuration

### Vault Path

Edit `backend/src/daemon.py`:
```python
VAULT_PATH = Path.home() / "your" / "vault"
```

### Install Ripgrep (Optional)

```bash
# macOS
brew install ripgrep

# Ubuntu
apt install ripgrep

# Falls back to Python search if not installed
```

---

## Troubleshooting

### "No results found"

LLM will try different search patterns automatically:

```python
# First attempt
grep_vault("Meta offer")  # Maybe no results

# LLM tries variations
grep_vault("Meta")
grep_vault("offer")
grep_vault("job.*Meta")
```

### "Search taking too long"

Check logs:
```bash
tail -f /tmp/localbrain-daemon.log
```

Look for:
- Ripgrep taking > 1 second (install ripgrep)
- LLM API timeout (check network)
- Too many tool iterations (max 10)

### "ModuleNotFoundError: fastapi"

Install dependencies:
```bash
conda activate localbrain
pip install fastapi uvicorn anthropic python-dotenv
```

---

## Integration Examples

### From Electron

Already integrated! Protocol URLs automatically forwarded to daemon.

### From Alfred

Create workflow:
```bash
open "localbrain://agentic_search?query={query}"
```

### From Raycast

```bash
#!/bin/bash
# LocalBrain Search
encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$1'))")
open "localbrain://agentic_search?query=$encoded"
```

### From Python

```python
from agentic_search import AgenticSearch

searcher = AgenticSearch(vault_path)
result = searcher.search("What was my Meta offer?")
print(result['answer'])
```

---

## Next Steps

1. **Test it:** Try some queries on your vault
2. **Install ripgrep:** `brew install ripgrep` for speed
3. **Add to Alfred/Raycast:** Quick access from anywhere
4. **Build UI:** Show search results in Electron app

---

## Summary

✅ **Implemented:** Agentic search with tool-based retrieval  
✅ **Protocol:** `localbrain://agentic_search?query=...`  
✅ **No embeddings:** Just ripgrep + LLM  
✅ **Fast:** ~1-2 seconds per query  
✅ **Simple:** 300 lines of code  
✅ **OpenCode-proven:** Works for massive codebases  

**Ready to use!** Just restart the daemon and try:
```bash
open "localbrain://agentic_search?query=Tell%20me%20about%20my%20projects"
```

🚀
