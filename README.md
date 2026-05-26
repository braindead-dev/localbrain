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

---

## Installation

### From a pre-built release

1. Download the latest `.dmg` (macOS) from the [Releases](https://github.com/braindead-dev/localbrain/releases) page
   - **Apple Silicon (M1/M2/M3/M4):** `LocalBrain-x.x.x-arm64.dmg`
   - **Intel Mac:** `LocalBrain-x.x.x.dmg`
2. Open the DMG and drag **LocalBrain** to your Applications folder
3. On first launch, macOS will warn about an unsigned app — right-click the app and select **Open**, then click **Open** in the dialog
4. LocalBrain will prompt you to:
   - Choose a vault folder (where your knowledge base lives)
   - Enter your Anthropic API key (powers search and ingestion)
   - Connect your apps (Gmail, GitHub, Notion, etc.)

### Prerequisites

LocalBrain requires:
- **Python 3.10+** with the `localbrain` conda environment (for the backend daemon)
- **Anthropic API key** (for Claude-powered search and ingestion)
- **ripgrep** installed (`brew install ripgrep`)

---

## Development Setup

### 1. Clone and install

```bash
git clone https://github.com/braindead-dev/localbrain.git
cd localbrain/electron

# Install Electron and build dependencies
npm install

# Install frontend dependencies
cd app && npm install && cd ..

# Create Python environment
conda create -n localbrain python=3.11
conda activate localbrain
cd backend && pip install -r requirements.txt && cd ..
```

### 2. Configure credentials

```bash
# Create the bundled OAuth credentials file
cp backend/src/bundled_credentials.json.example backend/src/bundled_credentials.json
# Edit and fill in your OAuth app credentials (see docs/connector-setup-guide.md)
```

### 3. Run in development

```bash
# From electron/ directory:
npm run dev
```

This starts the Next.js frontend (localhost:3000) and Electron in dev mode. The backend daemon starts automatically via Electron's main process.

To run the backend independently:

```bash
conda activate localbrain
cd backend
python -m src.daemon
```

### 4. Build for distribution

```bash
# From electron/ directory:
npm run build

# Output in electron/dist/:
#   LocalBrain-1.0.0-arm64.dmg    (Apple Silicon)
#   LocalBrain-1.0.0.dmg          (Intel)
#   LocalBrain-1.0.0-arm64-mac.zip
#   LocalBrain-1.0.0-mac.zip
```

---

## Connecting to Claude Desktop / Claude Code

LocalBrain exposes an MCP server so Claude can search, read, and ingest into your vault.

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "localbrain": {
      "command": "/opt/homebrew/anaconda3/envs/localbrain/bin/python",
      "args": ["-m", "src.core.mcp.extension.start_servers", "--stdio"],
      "cwd": "/absolute/path/to/localbrain/electron/backend"
    }
  }
}
```

For Claude Code, add the same to `.claude/settings.json`.

**MCP Tools exposed:** `search`, `open`, `ingest`, `list`

---

## Connectors

| Connector | Auth | Notes |
|-----------|------|-------|
| Gmail | OAuth (bundled) | "Sign in with Google" — reads emails |
| Google Calendar | OAuth (bundled) | Shares Gmail credentials — reads events |
| GitHub | OAuth (bundled) | "Sign in with GitHub" — reads activity |
| Notion | OAuth (bundled) | "Sign in with Notion" — reads pages |
| iMessage | Local DB | macOS-only; requires Full Disk Access |
| Browser | Chrome Extension | Ingests browsing history |

All OAuth connectors use bundled credentials — users just click "Sign in" and authenticate in their browser. No client IDs or secrets to configure.

To register your own OAuth apps (for forking/self-hosting), see [`docs/connector-setup-guide.md`](docs/connector-setup-guide.md).

---

## Architecture

LocalBrain is a three-layer system: **Electron frontend** (macOS app) -> **FastAPI daemon** -> **hybrid markdown vault**. An optional **MCP proxy server** enables AI apps to query the vault.

### Data Flow

**Search Query:**
```
User types "conferences attended"
  -> Frontend POST /protocol/search {"q": "conferences attended"}
  -> Daemon receives query
  -> Agentic search: LLM generates grep pattern "conference|attended|event"
  -> Execute ripgrep on vault files
  -> Read relevant file sections
  -> Synthesize answer with citations
  -> Return JSON response with results + metadata
```

**Ingestion:**
```
Connector fetches new data (e.g., Gmail emails)
  -> Convert to ConnectorData format (title, content, timestamp, source_url)
  -> LLM analyzes: "Where does this belong in the vault?"
  -> Generate structured markdown with ## sections
  -> Fuzzy match existing files/sections (tolerance for typos)
  -> Apply changes to vault files
  -> Validate markdown structure (title, citations, sections)
  -> If errors: regenerate with feedback (max 3 retries)
  -> Save citation metadata to .json sidecar
```

### Core Components

**1. FastAPI Daemon** — Main service handling search, ingestion, connector management. Auto-syncs every 10 minutes with per-connector toggle.

**2. Agentic Search Engine** — Claude Haiku with tool calling (`grep_vault` + `read_file`). No vector DB — pure ripgrep + LLM reasoning. 95% accuracy on LongMemEval benchmark.

**3. Ingestion Pipeline** — LLM-powered content analysis, fuzzy matching for existing sections, self-correcting validation loop (max 3 retries).

**4. Connector Plugin System** — Drop `<name>_connector.py` in `connectors/<name>/` and it auto-loads. Generic REST routes for all connectors.

**5. MCP Proxy Server** — Pure format translator bridging Claude Desktop (stdio) <-> Daemon (HTTP). Handles auth and audit logging.

**6. Electron Frontend** — Next.js + Electron with real-time status, resizable panels, dark mode, shadcn/ui.

### Why This Architecture?

- **No vector database:** ripgrep is instant (<100ms on 10K files), LLM generates optimal patterns, zero indexing overhead
- **LLM-powered ingestion:** handles ambiguity, self-corrects, maintains readable markdown
- **Plugin architecture:** add connectors without touching daemon code
- **MCP as pure proxy:** all intelligence in daemon, easy to debug
- **Markdown as storage:** human-readable, git-friendly, portable, no lock-in

### Performance

- **Search latency:** 1-3s (ripgrep ~50ms + LLM calls ~200ms each)
- **Ingestion speed:** ~5s per item
- **Memory footprint:** ~200MB
- **Disk usage:** Vault size + ~10% for citation JSON sidecars

---

## Project Structure

```
localbrain/
├── electron/
│   ├── app/                        # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/page.tsx       # Main app layout
│   │   │   └── components/        # React components
│   │   └── package.json
│   │
│   ├── electron-stuff/             # Electron main process
│   │   ├── main.js
│   │   ├── preload.js
│   │   └── assets/icon.icns
│   │
│   ├── backend/                    # Python backend
│   │   ├── src/
│   │   │   ├── daemon.py           # Main FastAPI service
│   │   │   ├── agentic_search.py   # Search engine
│   │   │   ├── agentic_ingest.py   # Ingestion pipeline
│   │   │   ├── config.py           # Config management
│   │   │   ├── connectors/         # Plugin system
│   │   │   │   ├── base_connector.py
│   │   │   │   ├── connector_manager.py
│   │   │   │   ├── connector_api.py
│   │   │   │   ├── gmail/
│   │   │   │   ├── calendar/
│   │   │   │   ├── github/
│   │   │   │   ├── notion/
│   │   │   │   └── imessage/
│   │   │   ├── core/mcp/           # MCP proxy server
│   │   │   │   ├── server.py
│   │   │   │   ├── stdio_server.py
│   │   │   │   └── tools.py
│   │   │   └── bundled_credentials.json  # OAuth creds (gitignored)
│   │   └── requirements.txt
│   │
│   ├── package.json                # Electron + electron-builder config
│   └── dist/                       # Build output (DMG/ZIP)
│
├── docs/
│   └── connector-setup-guide.md    # OAuth app registration guide
│
└── status.md                       # Project status tracker
```

---

## Tech Stack

**Backend:** FastAPI, Anthropic SDK (Claude Haiku), ripgrep, Levenshtein, loguru  
**Frontend:** Next.js 15, Electron, TailwindCSS, shadcn/ui, Motion  
**Integration:** Model Context Protocol (MCP), OAuth 2.0, PKCE

---

## Security

- All data stays local — vault is a folder on your machine
- OAuth tokens stored with `0600` permissions (owner-only)
- Bundled credentials are gitignored and never committed
- CORS restricted to localhost origins only
- OAuth callbacks validate CSRF state parameters
- Electron: `nodeIntegration: false`, `contextIsolation: true`
- Daemon binds to `127.0.0.1` only (not exposed to network)

---

Made with love by Henry Wang, Sid Songirkar, Taymur Faruqui, and Pranav Balaji
