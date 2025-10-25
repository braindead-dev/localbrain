# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LocalBrain is a desktop application built with Electron and Next.js. The project consists of three main components:

1. **Electron Desktop App** (`electron/`) - Wraps the Next.js frontend in an Electron shell for desktop deployment
2. **Next.js Frontend** (`electron/app/`) - The user interface, configured for static export
3. **Remote MCP Proxy** (`remote-mcp/`) - A planned proxy service to enable local MCP access via public URLs

## Architecture

### Electron + Next.js Integration

The desktop app uses a hybrid development/production architecture:

- **Development mode**: Electron loads Next.js dev server at `http://localhost:3000`
- **Production mode**: Electron loads statically exported Next.js files from `electron/app/out/` using `file://` protocol

The Electron main process (`electron/main.js`) creates a BrowserWindow that:
- Starts maximized with minimum dimensions of 800x600
- Displays "LocalBrain" in the macOS dock (not "Electron")
- Uses security best practices (no nodeIntegration, contextIsolation enabled)
- Includes platform-specific menu templates for macOS

### Next.js Configuration

The Next.js app is configured for static export in `electron/app/next.config.ts`:
- `output: 'export'` - Generates static HTML/CSS/JS files
- `trailingSlash: true` - Ensures file:// protocol compatibility
- `images: { unoptimized: true }` - Disables image optimization for static export
- `assetPrefix: './'` - Uses relative paths for assets

This configuration is critical for Electron compatibility. Do not change these settings without understanding the implications for the desktop app.

### Backend (Planned)

The `electron/backend/` directory is reserved for a background service that will run independently, controlled via macOS menu bar icon. Planned features:
- Connection fetching
- Ingestion agent
- Retrieval agent
- Local MCP bridge

## Development Commands

### Initial Setup

```bash
# From electron/ directory
npm install
# This automatically runs postinstall to install Next.js dependencies in app/
```

### Development Workflow

```bash
# From electron/ directory - Start both Next.js and Electron in dev mode
npm run dev

# Run only Next.js dev server
npm run dev:next

# Run only Electron (assumes Next.js is running separately)
npm run dev:electron
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
