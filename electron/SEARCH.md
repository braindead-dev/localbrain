# Natural Language Search

**Simple:** `localbrain://search?q=your question here`

Input: Natural language  
Output: Answer + relevant context  
Model: claude-haiku-4-5-20251022 (same as ingestion)

---

## Quick Start

### Via Protocol URL

```bash
open "localbrain://search?q=What was my Meta offer?"
```

### Via API

```bash
curl -X POST http://localhost:8765/protocol/search \
  -H "Content-Type: application/json" \
  -d '{"q": "What was my Meta offer?"}'
```

### Via Python

```python
from agentic_search import Search

searcher = Search(vault_path)
result = searcher.search("What was my Meta offer?")
print(result['answer'])
```

---

## How It Works

**Input:** Natural language query  
**Backend:** Figures out best retrieval method (currently: agentic grep)  
**Output:** Answer with citations

```
You: "What was my Meta offer?"
  ↓
LLM generates grep patterns
  ↓
Ripgrep searches vault (50-100ms)
  ↓
LLM reads relevant files
  ↓
LLM synthesizes answer
  ↓
"Meta offered $160k base, $40k sign-on [offers/meta.md]"
```

**No embeddings. No vector search. Just ripgrep + LLM.**

---

## Examples

```bash
# Simple lookup
open "localbrain://search?q=What courses did I take?"

# Multi-file synthesis
open "localbrain://search?q=Compare all my job offers"

# Exploration
open "localbrain://search?q=What projects did I work on?"

# Time-based
open "localbrain://search?q=What did I do last week?"
```

---

## Testing

### Shell Script

```bash
cd backend
./scripts/test_search.sh "What was my Meta offer?"
```

### Python Script

```bash
cd backend
python scripts/test_search.py "What was my Meta offer?"
```

### Check Logs

```bash
tail -f /tmp/localbrain-daemon.log
```

Expected output:
```
2024-10-25 04:30:00 - INFO - 🔍 Search: What was my Meta offer?
2024-10-25 04:30:00 - INFO -   🔧 Tool call: grep_vault({'pattern': 'Meta.*offer'})
2024-10-25 04:30:01 - INFO -   🔧 Tool call: read_file({'filepath': 'offers/meta.md'})
2024-10-25 04:30:02 - INFO - ✅ Search complete (2 iterations)
```

---

## Configuration

### Vault Path

Edit `backend/src/daemon.py`:
```python
VAULT_PATH = Path.home() / "your" / "vault"
```

### Model

Default: `claude-haiku-4-5-20251022` (same as ingestion)

To change, edit `backend/src/agentic_search.py`:
```python
class Search:
    def __init__(self, vault_path: Path, model: str = "your-model"):
        ...
```

---

## Integration

### Alfred Workflow

```bash
open "localbrain://search?q={query}"
```

### Raycast Script

```bash
#!/bin/bash
encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$1'))")
open "localbrain://search?q=$encoded"
```

### Electron (already integrated!)

Protocol URLs automatically handled.

---

## Why This Approach?

### 1. Flexible Backend
Today: Agentic grep  
Tomorrow: Could add hybrid search, reranking, etc.  
User doesn't care - same simple interface

### 2. Natural Input
No need to understand "semantic search" vs "keyword search"  
Just ask your question

### 3. Simple Protocol
One endpoint: `localbrain://search?q=...`  
No complex parameters

---

## Speed

**Typical query (1000 files):**
- Grep: 50-100ms
- LLM tool calls: ~1-2s
- **Total: ~1-2 seconds**

**Fast enough.** No need for complex optimization.

---

## What's Under the Hood

**Current implementation:** Agentic retrieval
- LLM gets `grep_vault` and `read_file` tools
- LLM decides what to search and read
- LLM synthesizes answer
- Inspired by OpenCode's approach

**Why no embeddings?**
- Vault is small (1000 files = ~50MB)
- Ripgrep is fast enough (50-100ms)
- No indexing overhead
- Always fresh

**Could we add embeddings later?**  
Yes! Backend can decide:
- Use grep for keyword queries
- Use embeddings for semantic queries
- Hybrid for best of both

User doesn't need to know - same `?q=` interface.

---

## Logs & Debugging

Full tool trace in logs:
```bash
tail -f /tmp/localbrain-daemon.log
```

See:
- What patterns LLM searched
- Which files were read
- How many iterations
- Final answer

---

## Summary

✅ **Simple interface:** `localbrain://search?q=...`  
✅ **Natural language input:** Ask questions normally  
✅ **Flexible backend:** Can swap retrieval methods  
✅ **Fast:** ~1-2 seconds per query  
✅ **No setup:** No indexing, no embeddings  
✅ **Same model as ingestion:** claude-haiku-4-5-20251022  

**Test it:**
```bash
npm run dev  # From electron/
open "localbrain://search?q=Tell me about my projects"
```

🚀
