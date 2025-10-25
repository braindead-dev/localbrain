# LocalBrain API Reference

Complete API for personal context layer.

---

## Endpoints

### 1. POST /protocol/ingest
Ingest content into vault (AI decides where to save).

**Request:**
```bash
curl -X POST http://localhost:8765/protocol/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Got offer from NVIDIA for $155k",
    "platform": "Email",
    "timestamp": "2024-10-25T10:00:00Z",
    "url": "https://mail.google.com/..."
  }'
```

**Response:**
```json
{
  "success": true,
  "files_updated": ["career/Job Search.md"],
  "message": "Content ingested successfully"
}
```

---

### 2. POST /protocol/search
Search vault with natural language query.

**Request:**
```bash
curl -X POST http://localhost:8765/protocol/search \
  -H "Content-Type: application/json" \
  -d '{"q": "What was my NVIDIA offer?"}'
```

**Response:**
```json
{
  "success": true,
  "query": "What was my NVIDIA offer?",
  "contexts": [
    {
      "text": "NVIDIA extends a full-time Software Engineer position... [1]",
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
- `text` = Actual .md content (not LLM synthesis)
- `citations` = Full citation metadata from .json
- Consumer apps (GPT, Claude) do the synthesis

---

### 3. GET /file/{filepath}
Fetch full file content for deep dives.

**Request:**
```bash
curl http://localhost:8765/file/personal/nvidia_offer.md
```

**Response:**
```json
{
  "path": "personal/nvidia_offer.md",
  "content": "Full markdown content...",
  "citations": {
    "1": {
      "platform": "Email",
      "timestamp": "2024-10-01T10:00:00Z",
      "quote": "...",
      "note": "..."
    }
  },
  "size": 1234,
  "last_modified": 1761410603.33
}
```

**Use case:** After getting context chunk, fetch full file for more details

---

### 4. GET /list/{path}
List files and directories in vault.

**Requests:**
```bash
curl http://localhost:8765/list              # Root
curl http://localhost:8765/list/career       # Specific folder
curl http://localhost:8765/list/personal     # Another folder
```

**Response:**
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
      "name": "Resume.md",
      "type": "file",
      "size": 1221,
      "last_modified": 1761410603.330
    },
    {
      "name": "offers",
      "type": "directory",
      "item_count": 3,
      "last_modified": 1761410603.331
    }
  ],
  "total": 3
}
```

**Use cases:**
- Discover what files exist
- Browse folder structure
- Find all files in a category

---

### 5. GET /health
Health check.

**Request:**
```bash
curl http://localhost:8765/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "localbrain-daemon"
}
```

---

## Complete AI App Flow

### Scenario: GPT helping with career decisions

```
1. User → GPT: "Help me decide between job offers"

2. GPT → LocalBrain: POST /protocol/search
   Body: {q: "job offers"}
   
3. LocalBrain → GPT: 
   {
     contexts: [
       {text: "...", file: "career/Job Search.md", citations: [...]}
     ]
   }

4. GPT → LocalBrain: GET /list/career
   (Discover all files)
   
5. LocalBrain → GPT:
   {
     items: [
       {name: "Job Search.md", type: "file"},
       {name: "Resume.md", type: "file"}
     ]
   }

6. GPT → LocalBrain: GET /file/career/Job%20Search.md
   (Get full details)
   
7. LocalBrain → GPT:
   {
     content: "Full markdown with all offers...",
     citations: {...}
   }

8. GPT → User:
   "Based on your notes:
    - NVIDIA: $155k base + $25k sign-on [career/Job Search.md]
    - Meta: $160k base + $40k sign-on [career/Job Search.md]
    
    I'd recommend Meta because..."
```

---

## Protocol URLs

For macOS deep links:

```bash
# Ingest
open "localbrain://ingest?text=Hello&platform=Test"

# Search
open "localbrain://search?q=What was my NVIDIA offer?"
```

---

## Security

- All endpoints scoped to vault directory
- Path traversal protection
- No authentication (local-only)
- Only serves .md and .json files
- Skips hidden files

---

## Performance

- **Search:** ~3-4 seconds (agentic retrieval)
- **File fetch:** ~50-100ms
- **List:** ~10-50ms
- **Ingest:** ~2-4 seconds (with retry logic)

---

## Error Responses

All endpoints return errors in format:
```json
{
  "error": "Error message here"
}
```

HTTP status codes:
- `200` - Success
- `400` - Bad request (missing params, invalid path)
- `403` - Access denied (path outside vault)
- `404` - Not found
- `500` - Server error
