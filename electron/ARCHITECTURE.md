# LocalBrain Architecture Plan

## Overview

LocalBrain is a desktop application that provides intelligent search, ingestion, and retrieval of personal knowledge across local files and external data sources. The system consists of an Electron frontend with Next.js UI and a background backend service that manages data processing and provides a local MCP interface.

## Core Architecture

```
electron/
├── app/                          # Next.js Frontend UI
├── backend/                      # Background Services & Core Logic
├── electron-stuff/              # Electron Main Process & Assets
└── shared/                      # Shared Types & Utilities
```

## Component Breakdown

### Frontend (app/)

The Next.js UI provides the user interface for interacting with the LocalBrain system.

```
app/
├── src/
│   ├── app/                     # Next.js App Router Pages
│   │   ├── api/                # API Routes (if needed)
│   │   ├── bridge/             # Bridge Management UI
│   │   ├── search/             # Search Interface
│   │   ├── settings/           # Settings & Configuration
│   │   └── vault/              # Filesystem View
│   ├── components/             # Reusable React Components
│   │   ├── ui/                 # Basic UI Components
│   │   ├── search/             # Search-related Components
│   │   ├── file-tree/         # File Tree Components
│   │   └── bridge/             # Bridge Components
│   ├── hooks/                  # Custom React Hooks
│   ├── lib/                    # Utilities & Helpers
│   ├── types/                  # TypeScript Types
│   └── styles/                 # Global Styles
├── public/                     # Static Assets
└── global.d.ts                # Global Type Declarations
```

**Key Frontend Features:**
- **Intelligent Search UI**: Send queries to retrieval agent, display results
- **Quick Note Interface**: Send note contents + metadata to ingestion
- **Bulk Ingest UI**: Upload and process large amounts of text data
- **Filesystem View**: Human-readable folder and file browser
- **Bridge Management**: Toggle external access, configure permissions
- **Settings Panel**: Configure folders, bridge access, audit logs
- **Audit Dashboard**: Display retrieval and ingestion history

### Backend (backend/)

The background service handles data processing, MCP interface, and external integrations.

```
backend/
├── src/
│   ├── core/                   # Core Services
│   │   ├── ingestion/         # Document Ingestion Engine
│   │   ├── retrieval/         # Search & Retrieval Engine
│   │   ├── mcp/               # Local MCP Server
│   │   └── bridge/            # External Bridge Service
│   ├── connectors/            # External Data Connectors
│   │   ├── browser-history/   # Browser History Connector
│   │   ├── gmail/             # Gmail Connector
│   │   ├── drive/             # Google Drive Connector
│   │   ├── calendar/          # Calendar Connector
│   │   ├── discord/           # Discord Messages
│   │   ├── imessage/          # iMessage Connector
│   │   ├── slack/             # Slack Connector
│   │   └── linkedin/          # LinkedIn Connector
│   ├── database/              # Data Storage Layer
│   │   ├── embeddings/        # Vector Embeddings
│   │   ├── chunks/            # Document Chunks
│   │   └── metadata/          # File & Source Metadata
│   ├── filesystem/            # Local File Management
│   ├── protocol/              # LocalBrain Protocol Handler
│   └── types/                 # Backend TypeScript Types
├── config/                    # Configuration Files
├── logs/                      # Application Logs
└── data/                      # Persistent Data Storage
```

**Backend Components:**

1. **Ingestion Engine**:
   - Process documents and extract insights
   - Chunk documents for embedding
   - Generate standardized file structures
   - Apply guardrails for sensitive data

2. **Retrieval Engine**:
   - Semantic search across all ingested content
   - Query processing and result ranking
   - Context-aware response generation

3. **Local MCP Server**:
   - Provide API endpoints for external tools
   - Handle protocol registration (localbrain://)
   - Manage permissions and access control

4. **Bridge Service**:
   - External API proxy functionality
   - Authentication and authorization
   - Request routing and logging

5. **Connector System**:
   - Standardized interface for external data sources
   - Sync and propagation functionality
   - Configurable permissions and filters

### Electron Main Process (electron-stuff/)

```
electron-stuff/
├── main.js                    # Main Electron Process
├── preload.js                 # Preload Script
├── menu.js                    # Application Menu
├── assets/                    # Icons & Images
├── protocols/                 # Custom Protocol Handlers
└── ipc-handlers/              # Inter-Process Communication
```

**Main Process Responsibilities:**
- Window management and lifecycle
- Background service supervision
- Protocol handling (localbrain://)
- System tray integration
- IPC bridge between frontend and backend

### Shared Components (shared/)

```
shared/
├── types/                     # Shared TypeScript Types
├── schemas/                   # Data Validation Schemas
├── constants/                 # Application Constants
└── utils/                     # Shared Utilities
```

## Data Flow Architecture

### Frontend → Backend Communication

1. **User initiates action in UI** (search, note creation, etc.)
2. **Frontend sends request via IPC** to Electron main process
3. **Main process routes request** to appropriate backend service
4. **Backend processes request** and returns results
5. **Results flow back** through the same chain to update UI

### Backend Data Processing Pipeline

1. **Data Ingestion**: Connectors fetch external data → Ingestion engine processes → Filesystem storage
2. **Document Processing**: Files chunked → Embeddings generated → Database storage
3. **Query Processing**: User query → Semantic search → Results ranked → Response formatted
4. **MCP Requests**: External tools query → Permission checks → Data retrieval → Formatted response

## Protocol System

LocalBrain uses a custom protocol system for deep linking and external integration:

```
localbrain://search?q=internship+email
localbrain://open?filepath=finance/banking.md
localbrain://search_agentic?keywords=internship,nvidia&days=7
localbrain://ingest?text="Email content here"
```

**Protocol Handler Flow:**
1. System intercepts localbrain:// URLs
2. Electron main process receives the request
3. Request parsed and validated
4. Routed to appropriate backend service
5. Response formatted and returned

## Security & Permissions

### Access Control
- **Bridge Settings**: User-configurable file access permissions
- **Connector Permissions**: Granular control over external data sources
- **Audit Logging**: Complete history of all requests and responses

### Data Protection
- **Sensitive Data Guardrails**: Automatic filtering of passwords, SSNs, etc.
- **Optional Encryption**: Filesystem encryption for sensitive content
- **Permission Validation**: All requests validated against user settings

## Development Workflow

### Getting Started
1. **Install dependencies**: `npm install` in root directory
2. **Development mode**: `npm run dev` (runs both frontend and electron)
3. **Backend development**: Services run as background processes
4. **Testing**: Use development tools in Electron for debugging

### Project Structure Benefits
- **Separation of Concerns**: Clear boundaries between UI, backend, and electron
- **Modular Design**: Easy to add new connectors or features
- **Type Safety**: Shared types ensure consistency across components
- **Scalability**: Background services can be extended independently

## Future Enhancements

### Phase 1 (MVP)
- Basic search and ingestion functionality
- Simple filesystem browser
- 2-3 core connectors (Gmail, Drive, Browser History)
- Local MCP interface

### Phase 2 (Enhanced Features)
- Advanced search with natural language responses
- Bulk ingestion capabilities
- External bridge with authentication
- Audit dashboard

### Phase 3 (Advanced Features)
- Online MCP proxy functionality
- Advanced connectors (Discord, Slack, iMessage)
- Filesystem encryption
- Plugin system for custom connectors

This architecture provides a solid foundation for the LocalBrain system while remaining flexible for future enhancements and maintaining clear separation between different system components.
