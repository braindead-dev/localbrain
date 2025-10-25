# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Localbrain is a local-first model context management system that empowers AI applications with relevant context from files, exports, and live connectors. It stores ingested information semantically using embeddings and exposes a secure local API for LLM queries. The system is designed for modularity, extensibility, and high performance with a focus on Python backend and an Electron desktop frontend.

## Architecture

### 1. Electron Desktop Application (Frontend)

**Purpose:**  
User interface for interacting with GEMINI, including note-taking, search, settings, and ingestion management.

**Technology:**  
- Electron (Node.js + Chromium)  
- React + TypeScript for UI components  
- IPC (Inter-Process Communication) to communicate with MCP daemon

**Implementation Instructions:**  
- Scaffold Electron app with React and TypeScript  
- Implement UI modules:  
  - Notes and quick search interface  
  - Ingestion pipeline control panel (e.g., enable/disable connectors)  
  - Settings and user preferences  
- Use Electron IPC to call MCP daemon endpoints over local HTTP or direct IPC bridge  
- Package the Electron app with `electron-builder` for cross-platform distribution

**Module Structure:**  
- `/src/electron/` — Electron main process  
- `/src/ui/` — React components and pages  
- `/src/ipc/` — IPC handlers and client wrappers

### 2. MCP Daemon (Python Backend API Server)

**Purpose:**  
Core backend service exposing local API endpoints for LLM queries, ingestion control, ACL enforcement, and audit logging.

**Technology:**  
- FastAPI for high-performance async API  
- Uvicorn as ASGI server  
- Pydantic for data validation and ACL models  
- Loguru for structured logging

**Implementation Instructions:**  
- Create FastAPI app with routes for:  
  - Semantic search & retrieval  
  - Ingestion job management (start/stop connectors)  
  - LLM query proxying and orchestration  
  - Audit log retrieval and ACL enforcement  
- Implement ACL middleware using Pydantic models and dependency injection  
- Integrate logging with Loguru, capturing request and audit events  
- Package as a standalone Python service with dependency management (Poetry or pipenv)

**Module Structure:**  
- `/mcp/api.py` — FastAPI app and route definitions  
- `/mcp/auth.py` — ACL and authentication models  
- `/mcp/logging.py` — Audit and structured logging setup  
- `/mcp/llm_client.py` — Wrappers for GPT, Claude, local LLMs  
- `/mcp/config.py` — Configuration and environment management

### 3. Ingestion Layer

**Purpose:**  
Connectors and pipelines to ingest data from multiple sources, generate embeddings, and store data in vector DB.

**Technology:**  
- Python connectors for Gmail, Google Drive, Slack, iMessage, Notion, etc.  
- Sentence-Transformers for embedding generation  
- Chroma as the primary vector database (Python SDK)  
- Asyncio for concurrent ingestion tasks

**Implementation Instructions:**  
- Build modular connector classes for each data source with unified ingestion interface  
- Implement embedding generation pipeline using sentence-transformers  
- Store embeddings and metadata in Chroma vector DB  
- Design ingestion scheduler and job manager to run ingestion tasks periodically or on-demand  
- Provide error handling, retry logic, and ingestion status reporting

**Module Structure:**  
- `/ingestion/connectors/` — Source-specific connector modules  
- `/ingestion/embedding.py` — Embedding generation utilities  
- `/ingestion/storage.py` — Chroma vector DB interface  
- `/ingestion/scheduler.py` — Task scheduling and job management

### 4. Retrieval Layer

**Purpose:**  
Query vector DB and optionally graph DB to retrieve relevant context for LLM queries.

**Technology:**  
- Chroma for vector search  
- Optional lightweight graph storage with networkx (in-memory prototype)  
- Python wrappers to integrate retrieval results with LLM clients

**Implementation Instructions:**  
- Implement retrieval API to query Chroma with semantic similarity search  
- Aggregate results with metadata for context construction  
- If graph DB is enabled, augment retrieval with graph traversal results  
- Integrate retrieval layer with MCP daemon query endpoints  
- Optimize retrieval latency and caching for common queries

**Module Structure:**  
- `/retrieval/vector_search.py` — Chroma query interface  
- `/retrieval/graph_search.py` — Networkx graph utilities (optional)  
- `/retrieval/context_builder.py` — Context aggregation and formatting

## Package Choices Summary

| Subsystem      | Packages / Libraries                                   |
|----------------|------------------------------------------------------|
| Frontend       | Electron, React, TypeScript, electron-builder        |
| Backend API    | FastAPI, Uvicorn, Pydantic, Loguru                    |
| Embedding      | sentence-transformers                                 |
| Vector DB      | Chroma Python SDK                                    |
| Graph DB       | networkx (prototype), py2neo / neo4j-driver (future) |
| Connectors     | google-api-python-client, slack-sdk, imessage-reader, notion-client, PyPDF2, Pillow, OpenCV |
| Utilities      | asyncio, watchdog (filesystem monitoring)             |

## Development Commands

### Initial Setup

```bash
# From electron/ directory
npm install
# This automatically runs postinstall to install Next.js dependencies in app/
```

### Development Workflow

**Frontend (Electron + Next.js):**

```bash
# From electron/ directory - Start both Next.js and Electron in dev mode
npm run dev

# Run only Next.js dev server
npm run dev:next

# Run only Electron (assumes Next.js is running separately)
npm run dev:electron
```

**Backend (Daemon + MCP Server):**

```bash
# From project root - Start both servers with one command
python electron/backend/src/core/mcp/extension/start_servers.py

# Or from extension directory
cd electron/backend/src/core/mcp/extension
python start_servers.py

# This will:
# - Start daemon on http://127.0.0.1:8765
# - Start MCP server on http://127.0.0.1:8766
# - Stop both cleanly with Ctrl+C
```

Alternatively, start servers manually in separate terminals:

```bash
# Terminal 1: Start daemon
cd electron/backend
python src/daemon.py

# Terminal 2: Start MCP server
cd electron/backend
python -m src.core.mcp.server
```

### Building

```bash
# From electron/ directory

# Build Next.js for static export
npm run build:next

# Build complete desktop app (includes Next.js build)
npm run build

# Alias for build
npm run dist
```

Build output:
- Next.js static files: `electron/app/out/`
- Electron distributables: `electron/dist/`
  - `LocalBrain-1.0.0.dmg` - macOS installer
  - `LocalBrain-1.0.0.zip` - macOS portable app

### Next.js Commands

```bash
# From electron/app/ directory

# Development server
npm run dev

# Build for static export
npm run build

# Alias for build
npm run export

# Run Next.js production server (not used in Electron)
npm run start

# Run ESLint
npm run lint
```

## Key Files and Directories

- `electron/main.js` - Electron main process, handles window creation and app lifecycle
- `electron/app/` - Next.js frontend application
- `electron/app/src/app/` - Next.js App Router pages and layouts
- `electron/app/next.config.ts` - Critical Next.js configuration for Electron compatibility
- `electron/package.json` - Electron app config with electron-builder settings
- `electron/assets/` - Application icons (icon.png for dev, icon.icns for production)
- `electron/backend/` - Placeholder for future background service

## Important Notes

### Next.js Export Requirements

When modifying the Next.js app:
- Do not use Next.js features that require a server (API routes, ISR, SSR)
- All pages must be statically exportable
- Use `next/image` sparingly or with `unoptimized: true`
- Test static export builds with `npm run build:next` before committing

### Electron Window Behavior

The window configuration in `electron/main.js` includes:
- `nodeIntegration: false` and `contextIsolation: true` for security
- Window starts maximized by default
- Custom menu templates for File, Edit, View, and Window menus
- Platform-specific menu handling for macOS

### Icon Requirements

- Development: Uses `assets/icon.png`
- Production: Requires `assets/icon.icns` (macOS)
- DMG installer: Uses `assets/dmg-background.png` (if present)

To regenerate icons, use the provided script: `electron/create-icon.sh`

## Technology Stack

- **Electron**: v25.0.0 - Desktop application framework
- **Next.js**: v16.0.0 - React framework with App Router
- **React**: v19.2.0 - UI library
- **TypeScript**: v5+ - Type safety
- **Tailwind CSS**: v4 - Styling (configured with PostCSS)
- **electron-builder**: v24.0.0 - Packaging and distribution

## Multi-Platform Builds

The electron-builder configuration supports:
- **macOS**: DMG and ZIP for both Intel (x64) and Apple Silicon (arm64)
- **Windows**: NSIS installer (configured but may need testing)
- **Linux**: AppImage (configured but may need testing)

Current development focus is macOS.
