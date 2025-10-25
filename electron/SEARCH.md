# Natural Language Search

Ask questions in plain English, get answers with citations.

```bash
open "localbrain://search?q=What was my NVIDIA offer?"
```

---

## How It Works

```
Question → LLM generates grep patterns → Ripgrep searches (~50-100ms) 
→ LLM reads relevant files → Answer with citations
```

**No embeddings, no vector search.** Just ripgrep + LLM (OpenCode-inspired).

**Speed:** ~3-4 seconds per query

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
# Via API
curl -X POST http://localhost:8765/protocol/search \
  -H "Content-Type: application/json" \
  -d '{"q": "What was my NVIDIA offer?"}'

# Check logs
tail -f /tmp/localbrain-daemon.log
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
