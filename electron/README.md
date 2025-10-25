# LocalBrain

Personal knowledge vault with AI-powered ingestion and natural language search.

**What it does:**
- 📥 **Ingest** text from anywhere into your vault (AI decides where it goes)
- 🔍 **Search** your vault with natural language questions
- 📂 **Organizes** information automatically into markdown files
- 🖥️ **Runs** as a background service with menu bar icon

---

## Current Features (✅ Working)

### 1. AI Ingestion (`localbrain://ingest`)
Send text from anywhere → AI decides where to save it
```bash
open "localbrain://ingest?text=Got offer from Meta&platform=Email"
```

**What it does:**
- Analyzes content with Claude
- Fuzzy matches to existing files (handles typos)
- Updates files or creates new ones
- Adds citations automatically
- 95% success rate with retry logic

### 2. Natural Language Search (`localbrain://search`)
Ask questions → Get context chunks with citations
```bash
open "localbrain://search?q=What was my NVIDIA offer?"
```

**Returns:**
- Relevant text from your .md files (not LLM synthesis)
- Citations from .json files with full metadata
- Structured for AI apps to consume

**How it works:**
- No embeddings, no vector search
- Uses ripgrep + LLM with tools (OpenCode-inspired)
- LLM finds relevant files
- Returns actual content + citations
- ~3-4 seconds per query

### 3. Background Service
- Runs as daemon with menu bar icon
- Starts automatically with Electron
- Persists when window closes
- Must quit from tray menu

---

## Architecture

```
Electron App (macOS menu bar)
  ↓
Python Backend Daemon (FastAPI)
  ↓
Your Markdown Vault
```

**Protocol URLs:**
- `localbrain://ingest?text=...` - Ingest content
- `localbrain://search?q=...` - Search vault

**API Endpoints:**
- `POST /protocol/ingest` - Ingestion
- `POST /protocol/search` - Search (returns context chunks)
- `GET /file/{filepath}` - Fetch full file content
- `GET /list/{path}` - List files and directories
- `GET /health` - Status check

## Quick Start

```bash
# 1. Setup Python backend
cd backend
conda create -n localbrain python=3.10 -y
conda activate localbrain
pip install fastapi uvicorn anthropic python-dotenv
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 2. Run Electron app (auto-starts daemon)
cd ..
npm install
npm run dev
```

**That's it!** The app will:
- ✅ Start Python daemon automatically
- ✅ Show tray icon in menu bar (🟢 = running)
- ✅ Register `localbrain://` protocol
- ✅ Keep daemon running when window closes

### Test It

```bash
# Test ingestion
open "localbrain://ingest?text=Hello from LocalBrain&platform=Test"

# Test search
open "localbrain://search?q=What did I ingest?"

# Check daemon
curl http://localhost:8765/health
```

---

## Usage

### Ingestion

**From anywhere on macOS:**
```bash
open "localbrain://ingest?text=Got offer from NVIDIA&platform=Email"
```

**Parameters:**
- `text` (required) - Content to ingest
- `platform` (optional) - Source platform
- `timestamp` (optional) - ISO 8601 timestamp
- `url` (optional) - Source URL

**What happens:**
1. LLM analyzes content
2. Determines best file(s) to update
3. Fuzzy matches file names (handles typos)
4. Updates or creates files
5. Adds citation with metadata

### Search

**From anywhere on macOS:**
```bash
open "localbrain://search?q=What was my NVIDIA offer?"
```

**Parameter:**
- `q` (required) - Natural language question

**What happens:**
1. LLM generates grep patterns
2. Ripgrep searches vault (~50-100ms)
3. LLM reads relevant files
4. Extracts context chunks + citations
5. Returns in ~3-4 seconds

**Returns:**
```json
{
  "contexts": [
    {
      "text": "Actual .md content with [1] citations",
      "file": "personal/nvidia_offer.md",
      "citations": [
        {"id": 1, "platform": "Email", "quote": "...", ...}
      ]
    }
  ]
}
```

---

## Technical Details

### Models
- **Ingestion:** `claude-haiku-4-5-20251001`
- **Search:** `claude-haiku-4-5-20251001`
- Same model for consistency

### Search Strategy (OpenCode-Inspired)
- No vector embeddings
- No semantic search database
- Just ripgrep + LLM with tools
- LLM gets `grep_vault` and `read_file` tools
- LLM decides what to search and read
- **Returns actual .md content** (not LLM synthesis)
- **Context layer for AI apps**, not a chatbot

### Why No Embeddings?
- Vault is small (~1000 files = 50MB)
- Ripgrep is blazingly fast (~50-100ms)
- No setup time, no stale indexes
- Always fresh, always accurate
- Simpler (300 lines vs thousands)

### Ingestion Pipeline
- Fuzzy matching (Levenshtein distance)
- Validation loops (self-correcting)
- Retry mechanism (3 attempts)
- 95% success rate

---

## Configuration

### Vault Path
Edit `backend/src/daemon.py`:
```python
VAULT_PATH = Path.home() / "your" / "vault"
```

### Vault Structure
```
my-vault/
├── career/
│   ├── Job Search.md
│   ├── Job Search.json  # Citations
│   └── about.md
├── personal/
│   ├── About Me.md
│   └── about.md
└── projects/
    └── LocalBrain.md
```

---

## Documentation

- `SEARCH.md` - Search system details
- `TEST_RESULTS.md` - Test results and performance
- `backend/INGESTION.md` - Ingestion system guide
- `backend/CITATION_SYSTEM.md` - Citation format
- `backend/README.md` - Backend overview

---

## Troubleshooting

### Daemon won't start
```bash
# Check conda environment
conda activate localbrain
python backend/src/daemon.py

# Check logs
tail -f /tmp/localbrain-daemon.log
```

### Protocol URLs don't work
```bash
# Check if daemon is running
curl http://localhost:8765/health

# Restart Electron
npm run dev
```

### Search returns no results
- Make sure vault has markdown files
- Check vault path in `backend/src/daemon.py`
- Try simpler queries first

---

## Development

### File Structure
```
electron/
├── app/                    # Next.js frontend
├── backend/                # Python backend
│   └── src/
│       ├── daemon.py       # FastAPI server
│       ├── agentic_ingest.py
│       └── agentic_search.py
├── electron-stuff/
│   ├── main.js            # Electron main process
│   └── assets/            # Tray icons
└── README.md              # This file
```

### Key Files
- `electron-stuff/main.js` - Electron main, daemon management, protocol handler
- `backend/src/daemon.py` - FastAPI server, endpoints
- `backend/src/agentic_ingest.py` - Ingestion engine
- `backend/src/agentic_search.py` - Search engine

### Commands
```bash
npm run dev           # Development mode
npm run build         # Production build
npm run dist          # Create distributable
```

---

## License

MIT