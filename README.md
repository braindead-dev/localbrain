# LocalBrain

> **The personalization layer for the next generation of AI apps**  
> The protocol to give AI apps your life's context.

Whether it's an agent like Poke or a chat app like Claude, next gen AI apps rely on accurate personal context. **This raises an issue** at both sides, for the AI app *and* the user.

For AI apps:
 - Engineering and maintaining a system to gather and use personal context eats up engineering time, ends up working okay at best in practice, and pulls focus away from shipping the core product.

For users:
 - Linking all of your connectors (email, slack, iMessage, etc) to every AI app you use is high-friction, a privacy risk, and leaves your own context fragmented and inaccessible.

This gap is only getting bigger as we move to an AI-adjusted world.

LocalBrain bridges this gap; it automatically organizes personal context from all your connectors into a **local, readable knowledge base** that any AI app can query to safely understand you.

<img width="1035" height="543" alt="high level architecture" src="https://github.com/user-attachments/assets/87795413-06c2-4da5-8f74-ece0c9fbb09f" />

## Architecture

### Data Flow

**Search Query:**
```
User types "conferences attended"
  ↓
Frontend POST /protocol/search {"q": "conferences attended"}
  ↓
Daemon receives query
  ↓
Agentic search: LLM generates grep pattern "conference|attended|event"
  ↓
Execute ripgrep on vault files
  ↓
Read relevant file sections
  ↓
Synthesize answer with citations
  ↓
Return JSON response with results + metadata
```

**Ingestion:**
```
Connector fetches new data (e.g., Gmail emails)
  ↓
Convert to ConnectorData format (title, content, timestamp, source_url)
  ↓
LLM analyzes: "Where does this belong in the vault?"
  ↓
Generate structured markdown with ## sections
  ↓
Fuzzy match existing files/sections (tolerance for typos)
  ↓
Apply changes to vault files
  ↓
Validate markdown structure (title, citations, sections)
  ↓
If errors: regenerate with feedback (max 3 retries)
  ↓
Save citation metadata to .json sidecar
```

LocalBrain is a three-layer system: **Electron frontend** (macOS app) → **FastAPI daemon** → **hybrid markdown vault**. Also an optional **MCP proxy server** enables AI apps to query the vault.

### Core Components

**1. FastAPI Daemon**
- Main service running as background process
- Handles agentic search, ingestion, and connector management
- Auto-syncs connected data sources every 10 minutes
- Stateless HTTP API with CORS for frontend access

**2. Agentic Search Engine**
- Uses Claude Haiku (claude-haiku-4-5-20251001) with tool calling
    - *we chose this model since its fast, cheap, and accurate, but it can be swapped out for any LLM*
- Tools: `grep_vault` (ripgrep-based regex search) and `read_file`
- LLM decides search strategy: decompose query → generate patterns → grep files → read relevant sections → synthesize answer
- No vector embeddings, no similarity scoring—pure regex + LLM reasoning
- 95% accuracy on LongMemEval benchmark (19/20 questions)
    - *this is a random sample of questions from the benchmark, not a full evaluation*
- We took inspiration from how SoTA coding agents retrieve the most relevant info while being blazingly fast

**3. Ingestion Pipeline**
- LLM analyzes raw data (emails, messages, docs) and updates the structured markdown filesystem to include the new info if its releavant to the user
- Fuzzy matching for section/file names using Levenshtein distance
- Validation feedback loop: attempts ingestion → checks markdown structure → retries if errors (max 3 attempts)
- Citations tracked in `.json` sidecars with source URLs, timestamps, and metadata

**4. Connector Plugin System**
- We made a standardized connector framework, so all connector plugins work nicely and are relatively easy to develop
- Source can either be external (over the web, like Gmail, Discord, etc) or pull from a local source (browser history, iMessage database, etc)
- Auto-discovery: drop `<name>_connector.py` in `connectors/<name>/` and it's loaded on startup
- Interface: `BaseConnector` with 4 methods (`get_metadata`, `has_updates`, `fetch_updates`, `get_status`)
- Generic REST routes (`/api/connectors/<id>/sync`, `/status`, etc.) work for all connectors

**5. MCP Proxy Server**
- This is how AI apps can safely query your local filesystem knowledge base
- **Pure format translator**—zero business logic
- Bridges Claude Desktop (stdio) ↔ Daemon (HTTP)
- Handles authentication (API keys) and audit logging
- Tools exposed to Claude: `search`, `open`, `summarize`, `list`
- Packaged as `.mcpb` extension for one-click Claude Desktop installation

**6. Electron Frontend**
- Next.js app wrapped in Electron for native desktop experience
- Real-time status indicators for daemon and MCP server health
- Resizable panels: file tree, editor, chat, connections, notes
- Dark mode with shadcn/ui components and Tailwind CSS

### Why This Architecture?

**No vector database for search:**
- Ripgrep is instant (<100ms on 10K files)
- LLM generates optimal search patterns (better than embedding similarity)
- Zero indexing overhead, works on any markdown vault
- Transparent: see exactly what matched via grep results

**LLM-powered ingestion:**
- Handles ambiguity and context (e.g., "Q3 launch" → finds correct project section)
- Self-correcting via validation loops (95%+ success rate)
- Maintains human-readable markdown structure
- No brittle rules or templates—adapts to any content

**Plugin architecture:**
- Add new connectors without touching daemon code
- Generic API routes scale to infinite connectors
- Easy testing: each connector is isolated

**MCP as pure proxy:**
- All intelligence in daemon (single source of truth)
- MCP just translates formats (no duplicate logic)
- Easy to debug: test daemon directly, MCP is transparent layer

**Markdown as storage:**
- Human-readable and editable
- Git-friendly (version control, diffs, branches)
- Portable (works with any markdown editor)
- No vendor lock-in, no database corruption

### Performance Characteristics

- **Search latency:** 1-3s (ripgrep ~50ms + LLM calls ~200ms each)
- **Ingestion speed:** ~5s per item (LLM analysis + fuzzy matching + validation)
- **Memory footprint:** ~200MB (FastAPI + Anthropic SDK)
- **Disk usage:** Vault size + ~10% overhead for citation JSON files
- **Concurrent requests:** FastAPI handles 100+ RPS easily

### Tech Stack

**Backend:**
- FastAPI (async Python web framework)
- Anthropic SDK (Claude Haiku API client)
- ripgrep (Rust-based regex search, 100x faster than grep)
- Levenshtein (fuzzy string matching for section names)
- python-dotenv (environment configuration)

**Frontend:**
- Next.js 15 (React SSR framework)
- Electron 33 (native desktop wrapper)
- TailwindCSS (utility-first styling)
- shadcn/ui (component library)
- Motion/Framer Motion (animations)

**Integration:**
- Model Context Protocol (Claude Desktop stdio bridge)
- OAuth 2.0 (Gmail authentication)
- Discord.py (Discord API wrapper)

### Project Structure

```
localbrain/
├── electron/
│   ├── app/                        # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/page.tsx       # Main app layout
│   │   │   └── components/        # React components
│   │   └── package.json           # Frontend deps
│   │
│   └── backend/                    # Python backend
│       ├── src/
│       │   ├── daemon.py           # Main FastAPI service
│       │   ├── agentic_search.py   # Search engine (LLM + ripgrep)
│       │   ├── agentic_ingest.py   # Ingestion pipeline (LLM + fuzzy match)
│       │   ├── connectors/         # Plugin system
│       │   │   ├── base_connector.py
│       │   │   ├── connector_manager.py
│       │   │   ├── gmail/
│       │   │   ├── browser/
│       │   │   └── ...
│       │   ├── core/
│       │   │   ├── mcp/            # MCP proxy server
│       │   │   │   ├── server.py
│       │   │   │   ├── stdio_server.py
│       │   │   │   └── tools.py
│       │   │   └── ingestion/      # Ingestion utilities
│       │   └── utils/              # Shared utilities
│       └── requirements.txt
│
└── my-vault/                       # Markdown knowledge base
    ├── projects/
    ├── personal/
    └── ...
```

### Implementation Details

**Agentic Search Prompt Strategy:**
- Ultra-concise system prompt (OpenCode-inspired)
- Example-driven: shows LLM exactly how to use tools
- "Minimize output, answer directly" → reduces token usage
- Forces LLM to check line numbers before reading full files

**Fuzzy Matching Algorithm:**
- Levenshtein distance with configurable threshold (default: 0.7 similarity)
- Tries exact match first, falls back to fuzzy if no match
- Prevents duplicate sections from slight name variations

**Validation Loop:**
- After ingestion: parse markdown, check for required sections (# title, ## Related)
- Verify citation markers `[1]` match entries in `.json` file
- If errors found: pass to LLM with specific error messages
- Max 3 retries → fail gracefully with detailed error log

**Connector Auto-Discovery:**
- Scan `connectors/` directory for `*_connector.py` files
- Import and instantiate classes inheriting from `BaseConnector`
- Register REST routes dynamically using FastAPI's router system
- Maintain singleton `ConnectorManager` for lifecycle management

**MCP Extension Packaging:**
- `stdio_server.py` copied into `extension/server/` directory
- `manifest.json` declares tool schemas (JSON Schema format)
- `package.sh` creates `.mcpb` bundle (ZIP with manifest)
- Claude Desktop loads bundle, spawns stdio server subprocess

This architecture optimizes for **transparency** (see what's happening), **simplicity** (minimal abstractions), and **extensibility** (easy to add connectors/features). The markdown vault is the single source of truth, everything else is stateless logic.

---

Made with ❤️ by Henry Wang, Sid Songirkar, Taymur Faruqui, and Pranav Balaji
