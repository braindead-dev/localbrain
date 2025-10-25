# LocalBrain

A personal knowledge workspace that intelligently organizes and retrieves information from your local files and external data sources through a desktop application.

## Product Vision

LocalBrain provides intelligent search, ingestion, and retrieval of personal knowledge across local files and external data sources. It combines the power of semantic search with a structured filesystem approach to create a personal knowledge base that understands context and relationships in your data.

**Key Features:**
- **Intelligent Search**: Natural language queries return relevant files, lines, or generated responses
- **Automated Ingestion**: Processes documents and extracts insights automatically
- **External Connectors**: Integrates with Gmail, Discord, Slack, Drive, and more
- **Local MCP Interface**: API access for external tools and integrations
- **Personal Insights**: Surface patterns and observations that traditional search can't find

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron Desktop App                     │
├─────────────────────────────────────────────────────────────┤
│  Next.js Frontend  │    Electron Main Process    │  Backend  │
│  - Search UI       │    - Window Management     │  Services │
│  - Filesystem View │    - Protocol Handler      │  - Ingestion│
│  - Bridge Settings │    - Service Supervision   │  - Retrieval│
│  - Audit Dashboard │    - IPC Communication     │  - MCP API  │
└─────────────────────────────────────────────────────────────┘
                                │
                    ┌─────────────┼─────────────┐
                    │             │             │
              .localbrain/   External Tools  Connectors
              Filesystem     (via MCP API)   - Gmail
                                             - Discord
                                             - Slack
                                             - Drive
                                             - Browser History
                                             - Calendar
```

## Team Breakdown

**Taymur**: Main app architecture, UI features, external app use cases
**Henry + Pranav**: Retrieval system, Node bridge service, Local MCP access, initial architecture setup
**Sid**: Ingestion system, filesystem management
**Everyone**: Architecture decisions, cross-team collaboration

## Core Components

### Frontend (Next.js)
- **Intelligent Search**: Send queries to retrieval agent, display relevant results
- **Quick Note**: Send note contents + metadata to ingestion agent
- **Bulk Ingest**: Upload and process large amounts of text data
- **Filesystem View**: Human-readable folder and file browser
- **Bridge Management**: Configure external access permissions and settings
- **Audit Dashboard**: Display retrieval and ingestion history

### Backend Services
- **Ingestion Engine**: Process documents, extract insights, manage embeddings
- **Retrieval Engine**: Semantic search, query processing, result ranking
- **Local MCP Server**: API endpoints for external tools (search, summarize, open, list)
- **Bridge Service**: External access management and audit logging
- **Connector System**: Standardized interface for external data sources

### Protocol System
Custom `localbrain://` deep links for external integration:
```
localbrain://search?q=internship+email
localbrain://open?filepath=finance/banking.md
localbrain://search_agentic?keywords=internship,nvidia&days=7
localbrain://ingest?text="Email content here"
```

## Filesystem Structure

LocalBrain uses a `.localbrain/` directory containing:
- **Markdown Files**: Structured notes with insights and observations
- **Standardized Format**: Each file starts with purpose summary
- **Source Citations**: Claims linked to supporting evidence with metadata
- **Auto-chunking**: Files automatically split and embedded for search
- **App Configuration**: `app.json` settings file for user preferences

## Unique Value Propositions

1. **Intelligent Insights**: Surface macro-level patterns (e.g., "applied to 200+ internships, no responses")
2. **Preprocessing Advantage**: Analyze all available data, not just query responses
3. **Community Plugin Ecosystem**: Like Obsidian, anyone can build and share custom connectors for any data source
4. **Vault-Based Architecture**: Choose any folder as your vault, sync via Dropbox/iCloud, switch between multiple vaults
5. **Local-First**: Full privacy with local processing and storage
6. **Semantic Understanding**: Context-aware search and retrieval

## Quick Start

### Prerequisites
- **Node.js 16+** - Frontend and Electron
- **Python 3.10+** - Backend services  
- **Conda** - Python environment management

### Setup & Run

```bash
# 1. Setup Python backend
cd backend
conda create -n localbrain python=3.10 -y
conda activate localbrain
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 2. Run Electron app (auto-starts daemon)
cd ../
npm install
npm run dev
```

**That's it!** The app will:
- ✅ Start Python daemon automatically
- ✅ Show tray icon in menu bar
- ✅ Register `localbrain://` protocol
- ✅ Keep daemon running when window closes

Test it: `open "localbrain://ingest?text=Hello&platform=Test"`

See `ELECTRON_INTEGRATION.md` for full details.

---

## Development Setup (Detailed)

### Getting Started (Advanced)
```bash
# Install dependencies
npm install

# Development mode (runs Next.js + Electron concurrently)
npm run dev

# Production build
npm run build
```

### Development Mode
- Next.js dev server: http://localhost:3000
- Electron app loads from dev server
- Hot reloading enabled
- Window starts maximized

### Production Mode
- Next.js builds to static files in `app/out/`
- Electron loads from file system
- Window starts maximized
- Optimized for distribution

## Security & Privacy

- **Local Processing**: All data stays on your machine
- **Sensitive Data Filtering**: Automatic removal of passwords, SSNs, etc.
- **Access Controls**: User-configurable permissions for external access
- **Audit Logging**: Complete history of all requests and responses
- **Optional Encryption**: Filesystem encryption available

## Ingestion Pipeline (OpenCode-Inspired)

Production-ready ingestion system with techniques from OpenCode:

### Key Features
- **Fuzzy Matching**: Levenshtein distance handles LLM naming variations
- **Validation Loops**: Self-correcting system fixes errors automatically  
- **Optimized Prompts**: Anthropic-style prompts reduce LLM errors by ~30%
- **Retry Mechanism**: Up to 3 attempts with error feedback (95% success rate)

### Quick Example
```bash
# Using test script (recommended)
python backend/scripts/ingest_from_file.py content.txt metadata.json

# Direct CLI
python backend/src/agentic_ingest.py ~/my-vault "Got offer from Meta, $150k"
```

**Documentation:**
- [Ingestion Guide](backend/INGESTION.md) - Comprehensive guide
- [OpenCode Comparison](../OPENCODE_COMPARISON.md) - Architecture comparison
- [Improvements Summary](../IMPROVEMENTS_SUMMARY.md) - What changed

## Future Roadmap

### Phase 1 (MVP)
- ✅ Production ingestion pipeline (fuzzy matching, validation, 95% success)
- Basic search and retrieval
- Core connectors (Gmail, Drive, Browser History)
- Local MCP interface

### Phase 2 (Enhanced)
- Natural language responses
- Advanced connectors (Discord, Slack, iMessage)
- External bridge functionality

### Phase 3 (Advanced)
- Online MCP proxy
- Plugin system for custom connectors
- Advanced analytics and insights

For detailed technical architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).