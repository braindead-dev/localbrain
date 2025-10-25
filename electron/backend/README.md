# LocalBrain Backend

Python backend for ingestion and search.

---

## Features

### 1. AI Ingestion
```bash
open "localbrain://ingest?text=Got offer from NVIDIA&platform=Email"
```

- Analyzes content with Claude
- Fuzzy matches to existing files
- Updates or creates files
- Adds citations automatically
- 95% success rate

### 2. Natural Language Search
```bash
open "localbrain://search?q=What was my NVIDIA offer?"
```

- No embeddings, just ripgrep + LLM
- ~3-4 seconds per query
- Includes citations
- OpenCode-inspired

---

## Setup

```bash
conda create -n localbrain python=3.10 -y
conda activate localbrain
pip install fastapi uvicorn anthropic python-dotenv
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

## Running

```bash
# Via Electron (auto-starts)
cd ..
npm run dev

# Or standalone
python src/daemon.py
```

---

## Technical Details

### Model
- **claude-haiku-4-5-20251001** for both ingestion and search
- Fast (~1-2s response)
- Cost-effective (~$0.01 per operation)

### Ingestion Pipeline
- Fuzzy matching (handles typos)
- Validation loops (self-correcting)
- Retry mechanism (3 attempts max)
- 95% success rate

### Search Strategy
- OpenCode-inspired (no embeddings)
- Ripgrep + LLM with tools
- grep_vault and read_file tools
- ~3-4 seconds per query

---

## Documentation

- `INGESTION.md` - Ingestion system guide
- `CITATION_SYSTEM.md` - Citation format
- `SETUP.md` - Setup instructions