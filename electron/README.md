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
3. **Open Source Connectors**: Community can build integrations for any data source
4. **Local-First**: Full privacy with local processing and storage
5. **Semantic Understanding**: Context-aware search and retrieval

## Development Setup

### Prerequisites
- Node.js 16+
- npm or yarn
- For macOS builds: Xcode command line tools (`xcode-select --install`)

### Getting Started
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

## Future Roadmap

### Phase 1 (MVP)
- Basic search and ingestion
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