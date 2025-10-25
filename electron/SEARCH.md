# Natural Language Search

Ask questions in plain English, get context chunks with citations.

```bash
open "localbrain://search?q=What was my NVIDIA offer?"
```

**Returns:** Actual .md content + citations (not LLM synthesis)

---

## How It Works

```
Question → LLM generates grep patterns → Ripgrep searches (~50-100ms) 
→ LLM reads relevant files → Extract context + citations
```

**No embeddings, no vector search.** Just ripgrep + LLM (OpenCode-inspired).

**Speed:** ~3-4 seconds per query

---

## Return Format

```json
{
  "query": "What was my NVIDIA offer?",
  "contexts": [
    {
      "text": "Actual content from .md file with [1] citation markers",
      "file": "personal/nvidia_offer.md",
      "citations": [
        {
          "id": 1,
          "platform": "Email",
          "timestamp": "2024-10-01T10:00:00Z",
          "quote": "We are pleased to offer you...",
          "note": "NVIDIA offer letter"
        }
      ]
    }
  ],
  "total_results": 1
}
```

**Key:**
- `text` = Actual .md content (minimal inference)
- `citations` = Full citation metadata from .json
- **No LLM synthesis** - consuming apps do that

---

## Examples

```bash
# Simple
open "localbrain://search?q=What courses did I take?"

# Multi-file
open "localbrain://search?q=Compare all my job offers"

# Exploration
open "localbrain://search?q=What projects did I work on?"
```

---

## Testing

```bash
# Search for context
curl -X POST http://localhost:8765/protocol/search \
  -H "Content-Type: application/json" \
  -d '{"q": "What was my NVIDIA offer?"}'

# List files in root
curl http://localhost:8765/list

# List files in specific folder
curl http://localhost:8765/list/career

# Fetch full file (for deep dive)
curl http://localhost:8765/file/personal/nvidia_offer.md

# Check logs
tail -f /tmp/localbrain-daemon.log
```

---

## File Endpoint

After getting context chunks, AI apps can fetch full files:

```bash
GET /file/{filepath}
```

**Returns:**
```json
{
  "path": "personal/nvidia_offer.md",
  "content": "Full markdown content...",
  "citations": {"1": {...}, "2": {...}},
  "size": 1234,
  "last_modified": 1234567890
}
```

**Use case:** Context chunk mentions file → AI app fetches full content

---

## List Files Endpoint

Browse vault structure and discover available files:

```bash
GET /list              # Root directory
GET /list/career       # Specific folder
GET /list/personal     # Another folder
```

**Returns:**
```json
{
  "path": "career",
  "items": [
    {
      "name": "Job Search.md",
      "type": "file",
      "size": 1278,
      "last_modified": 1761410603.329
    },
    {
      "name": "offers",
      "type": "directory",
      "item_count": 3,
      "last_modified": 1761410603.330
    }
  ],
  "total": 2
}
```

**Use cases:**
- AI app discovers what files exist
- Browse folder structure
- Find all files in a category
- Check what context is available

**Example flow:**
```
GPT: "Show me all your job offers"
→ Search finds career/ folder mentioned
→ GET /list/career to see all files
→ GET /file/career/Job%20Search.md for details
```

---

## Why No Embeddings?

- Vault is small (~1000 files = 50MB)
- Ripgrep is fast enough (50-100ms)
- No setup, always fresh
- Simpler implementation

**Could add embeddings later** - user interface stays the same (`?q=...`)

---

## Performance

**Tested:**
- Query 1 (NVIDIA offer): 4 iterations, ~4s, perfect accuracy
- Query 2 (AI research): 3 iterations, ~3s, excellent synthesis

See `TEST_RESULTS.md` for full results.
