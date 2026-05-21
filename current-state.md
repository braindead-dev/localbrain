# LocalBrain — Current State

## Project Overview

LocalBrain is a macOS desktop app (Electron + Next.js frontend, FastAPI Python backend) that acts as a "personalization layer" for AI apps. It ingests personal data from connectors (Gmail, Google Calendar, iMessage, GitHub, Notion, Reddit, Twitter, browser history, Outlook) into a local markdown vault, then exposes it via a natural-language search API and an MCP server so AI apps (like Claude Desktop) can query the user's context.

### Architecture
- **Electron shell** (`electron/electron-stuff/main.js`) — spawns the Python daemon and the Next.js-built UI
- **Next.js 16 frontend** (`electron/app/`) — React + Tailwind + shadcn/ui, statically exported to `app/out/`
- **FastAPI daemon** (`electron/backend/src/daemon.py`) — port 8765, handles search, ingestion, connectors
- **MCP HTTP server** (`electron/backend/src/core/mcp/server.py`) — port 8766, bridges Claude Desktop
- **Markdown vault** (`my-vault/`) — human-readable knowledge base with `.json` citation sidecars

### Tech Stack
- Python 3.13 / FastAPI 0.115 / Anthropic SDK 0.71 / uvicorn / slowapi
- Next.js 16.0 / React 19 / TypeScript 5 / Tailwind v4 / Electron 25
- Claude Haiku (`claude-haiku-4-5-20251001`) for search + ingestion
- ripgrep for vault search (must be on `$PATH`)

---

## Build & Run Instructions

### Prerequisites
1. **Node.js** (v18+) and **npm**
2. **Conda** with a `localbrain` environment (or a Python 3.11+ venv)
3. **ripgrep** (`brew install ripgrep`)
4. An Anthropic API key

### Python environment setup
```bash
conda create -n localbrain python=3.11
conda activate localbrain
pip install -r electron/backend/requirements.txt
```

### Environment configuration
```bash
cp electron/backend/.env electron/backend/.env.local   # do NOT commit real keys
# Edit .env and set:
# ANTHROPIC_API_KEY=<your-key>
# VAULT_PATH=~/path/to/your/vault
```

### Frontend (Next.js)
```bash
cd electron/app
npm install
npm run build        # produces electron/app/out/
```

### Run in development
```bash
cd electron
npm install
npm run dev          # starts Next.js dev server + Electron concurrently
```

### Run production build (DMG)
```bash
cd electron
npm run build        # builds Next.js static export then runs electron-builder
```

### Run backend only (for testing)
```bash
cd electron/backend
conda activate localbrain
python src/daemon.py
# Daemon runs on http://localhost:8765
```

### Run tests
```bash
cd electron/app
npm test             # 33 vitest tests, all passing
```

---

## Issues Table

| ID | Priority | Component | Issue | Status |
|----|----------|-----------|-------|--------|
| 1 | **P0** | Security | Real `ANTHROPIC_API_KEY` and `CHROMA_API_KEY` committed in `electron/backend/.env` git history; also present in root `.env` locally | **Cannot auto-fix** — must rotate keys and clean git history |
| 2 | **P0** | Electron | `findPythonCmd()` in `main.js` only checked `~/miniconda3`, `~/anaconda3`, `~/miniforge3`, `~/mambaforge` paths — misses Homebrew-installed Anaconda at `/opt/homebrew/anaconda3` (the actual install location on this machine), causing daemon to silently fail with system python3 which has no dependencies | **Fixed** — added `/opt/homebrew/anaconda3`, `/opt/homebrew/miniconda3`, `/opt/anaconda3`, `/usr/local` variants |
| 3 | **P1** | TypeScript | `global.d.ts` declared `window.electronAPI` but preload.js exposes the bridge as `window.electron`. The type declaration was dead/wrong. Runtime code in `HomeView.tsx` correctly uses `window.electron` but TypeScript offered no type safety for it | **Fixed** — updated `global.d.ts` to declare `window.electron` with correct shape |
| 4 | **P1** | TypeScript tests | All three test files (`ChatView.test.tsx`, `ConnectionsView.test.tsx`, `SearchView.test.tsx`) used direct `as` casts for mock API objects, producing TS2352 type errors (`tsc --noEmit` failed) | **Fixed** — added `as unknown as` double-cast pattern |
| 5 | **P1** | Editor | `EditorView.tsx` save button shows but saving is not implemented (toast says "not yet implemented"). The backend has no `PUT /file/{path}` endpoint. File edits in the UI are view-only | **Skipped** — requires new backend endpoint and file-write logic |
| 6 | **P1** | Browser connector | `browser_history` connector in `ConnectionsView` shows a "Select File" dialog that is a placeholder with no actual file-picker logic (comment: "this is a placeholder"). iMessage connector has the same stub | **Skipped** — UI placeholder, requires Electron `dialog.showOpenDialog` wiring |
| 7 | **P2** | Backend | `slowapi` listed in `requirements.txt` but was not installed in the `localbrain` conda environment, causing `ModuleNotFoundError` on daemon startup | **Fixed** — installed `slowapi` in the conda env |
| 8 | **P2** | FastAPI | `@app.on_event("startup")` is deprecated since FastAPI 0.93 and will be removed in a future version; should use `lifespan` context manager instead | Annotated with `# type: ignore` and comment; full refactor deferred |
| 9 | **P2** | Electron build | Production icon file `electron/electron-stuff/assets/icon.icns` is missing; only `icon.png` exists. `main.js` references `.icns` in production mode, which will cause a broken/blank icon in packaged builds | **Skipped** — requires creating/converting icon file |
| 10 | **P2** | Electron | `enableRemoteModule: false` in `BrowserWindow` webPreferences — this option was removed in Electron 14 and is a no-op in Electron 25. Harmless but dead config noise | Minor — no functional impact |
| 11 | **P2** | Frontend | `SearchView` component exists (`src/components/SearchView.tsx`) and has tests but is never rendered in `page.tsx`. The "search" tab in the nav actually renders `EditorView`. The `SearchView` is dead code | **Skipped** — removing it would break tests; likely intentional feature left dormant |
| 12 | **P2** | Backend | `conversation_history` is a module-level list — shared across all concurrent requests. Multi-user or parallel requests will corrupt each other's conversation history | Minor in single-user desktop context; noted |
| 13 | **P3** | Next.js build | Multiple warnings about `baseline-browser-mapping` module being over 2 months old and workspace root detection warnings (multiple lockfiles) | Non-breaking warnings |
| 14 | **P3** | Python | `agentic_ingest.py` calls `pipeline.ingest()` with `context=` kwarg in some callers but `pipeline.ingest(text, metadata)` positionally in others — inconsistent but not broken because the method signature accepts both | Minor |
| 15 | **P3** | Security | `MCP_API_KEY=dev-key-local-only` hardcoded in `.env` — acceptable for local dev but should be documented as insecure for any network-exposed deployment | Documented |
| 16 | **P3** | Electron | `app.on('window-all-closed')` handler is a no-op (just logs). On Windows/Linux this keeps the app running invisibly with no tray icon in the taskbar when all windows close | Minor UX issue |
| 17 | **P3** | Misc | `Sid Songirkar Resume.tex` and `status.md` committed at repo root — not gitignored, unrelated to the project | Minor housekeeping |

---

## Build Results

### Next.js (`electron/app`)
```
✓ Compiled successfully in 3.1s
✓ Generating static pages (4/4)
Build: PASSES
```

### TypeScript (`npx tsc --noEmit`)
```
Before fixes: 3 errors (TS2352 in test files)
After fixes:  0 errors — PASSES
```

### Vitest tests (`npm test`)
```
Test Files: 3 passed (3)
Tests:      33 passed (33)
All tests PASS
```

### Electron build (`npm run build`)
Not run — requires `electron-builder` and the full Next.js `out/` directory to be present. Next.js build succeeds, so Electron build should work assuming the Python backend is bundled. Missing `icon.icns` will cause a broken icon in the DMG but will not block the build.

### Python backend
Daemon imports successfully with the `localbrain` conda environment. Requires `slowapi` (now installed). Daemon starts cleanly at `http://127.0.0.1:8765`.
