# LocalBrain Architecture

## Product Overview

LocalBrain is a personal knowledge workspace that intelligently organizes and retrieves information from your local files and external data sources through a desktop application. It combines semantic search, automated ingestion, and a structured filesystem approach to create a personal knowledge base that understands context and relationships in your data.

**Key Value Propositions:**
- **Intelligent Insights**: Surface macro-level patterns (e.g., "applied to 200+ internships, no responses")
- **Preprocessing Advantage**: Analyze all available data, not just query responses
- **Open Source Connectors**: Community can build integrations for any data source
- **Local-First**: Full privacy with local processing and storage
- **Semantic Understanding**: Context-aware search and retrieval

## Team Breakdown

**Taymur**: Main app architecture, UI features, external app use cases
**Henry + Pranav**: Retrieval system, Node bridge service, Local MCP access, initial architecture setup
**Sid**: Ingestion system, filesystem management
**Everyone**: Architecture decisions, cross-team collaboration

## System Architecture

### Electron Desktop Application
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
              Filesystem     (via MCP API)   - Gmail, Discord
                                             - Slack, Drive
                                             - Browser History
```

## Frontend (Next.js)

The Next.js frontend provides the user interface wrapped in Electron, built with React, TypeScript, and Tailwind CSS.

### Core Features
- **Intelligent Search**: Send queries to retrieval agent, display relevant files/lines
- **Quick Note**: Send note contents + metadata to ingestion agent
- **Bulk Ingest**: Upload and process large amounts of text data
- **Filesystem View**: Human-readable folder and file browser
- **Bridge Management**: Configure external access permissions and settings
- **Audit Dashboard**: Display retrieval and ingestion history

### Protocol Integration
All UI actions use `localbrain://` deep links:
```
localbrain://search?q=internship+email
localbrain://open?filepath=finance/banking.md
localbrain://ingest?text="Meeting notes here"
localbrain://summarize?filepath=projects/startup.md
```

## Backend Services

Background services that handle data processing, search, and external integrations.

### Protocol System
Custom deep link commands processed by backend:
```
localbrain://search?q=internship+email
localbrain://search_agentic?keywords=internship,nvidia&days=7
localbrain://ingest?text="Email from contact@henr.ee: fuck you"
localbrain://open?filepath=finance/banking.md
```

### Local MCP / API
Provides tools for external integrations:
- **search**: Natural language search across knowledge base
- **search_agentic**: Structured search with filters
- **open**: Retrieve full file contents
- **summarize**: Generate file summaries
- **list**: Browse directory structure

### Ingestion Engine
- **Document Processing**: Parse various file formats
- **Content Chunking**: Split documents for search optimization
- **Embedding Generation**: Create semantic vector representations
- **Guardrails**: Filter sensitive data (passwords, SSNs, credit cards)
- **Standardized Files**: Auto-initialize markdown with purpose summaries

### Retrieval Engine
- **Semantic Search**: Vector similarity matching across content
- **Query Processing**: Natural language understanding and parsing
- **Result Ranking**: Context-aware ordering by relevance and recency
- **Multi-Format Results**: Files, text snippets, or generated responses

### Connector System
Standardized interface for external data sources:
- **Sync**: Incremental data fetching and processing
- **Propagate**: Initial full data import
- **Authentication**: Secure credential management
- **Rate Limiting**: API quota compliance

**Available Connectors:**
- Communication: Gmail, Discord, Slack, iMessage, LinkedIn
- Productivity: Google Drive, Calendar, Browser History
- Social Media: Instagram, TikTok

## Filesystem Structure

**`.localbrain/` Directory:**
```
.localbrain/
├── app.json              # Application configuration
├── notes/                # User markdown files
│   ├── projects/         # Project-related notes
│   ├── research/         # Research and learning
│   ├── personal/         # Personal notes
│   └── archive/          # Archived content
├── attachments/          # Connector file attachments
├── config/               # System configuration
├── data/                 # Database and embeddings
└── logs/                 # Application logs
```

**Markdown File Format:**
```markdown
---
title: "File Purpose Summary"
created: "2024-01-15T10:30:00Z"
source: "manual"
tags: ["project", "research"]
---

# Main Content

## Observations
- Key insight with source citation
- Supporting evidence and context

## Sources
**Source:** [Platform] - [Timestamp]
[Direct quotation or evidence]
[URL if applicable]
```

## Database Architecture

**Three-Layer Storage:**
1. **Embeddings Layer**: Vector representations for semantic search
2. **Chunks Layer**: Document segments with metadata
3. **Metadata Layer**: File, source, and system information

**Data Relationships:**
- Files contain multiple Chunks
- Chunks have Embeddings for search
- Metadata provides context and attribution
- Auto-reprocessing on file changes

## Security & Access Control

### Bridge Settings
User-configurable external access permissions stored in `.localbrain/app.json`:
```json
{
  "bridge": {
    "enabled": true,
    "allowedDirectories": ["projects", "notes"],
    "blockedDirectories": ["private", "sensitive"],
    "allowedTools": ["search", "list"],
    "maxRequestsPerHour": 1000
  }
}
```

### Data Protection
- **Sensitive Data Filtering**: Automatic removal of passwords, SSNs, etc.
- **Access Logging**: Complete audit trail of all requests
- **Permission Validation**: Multi-layer access control enforcement
- **Optional Encryption**: Filesystem encryption for sensitive content

## Development Workflow

### Getting Started
```bash
# Install dependencies
npm install

# Development mode (Next.js + Electron concurrently)
npm run dev

# Production build
npm run build
```

### Project Structure Benefits
- **Separation of Concerns**: Clear boundaries between UI, backend, and electron
- **Modular Design**: Easy to add new connectors or features
- **Type Safety**: Shared types ensure consistency
- **Scalability**: Background services can be extended independently

### Protocol Handler Development
- Test URLs: `localbrain://search?q=test`
- Debug with Electron dev tools
- Mock backend responses during development
- Validate URL generation and parsing

## Future Roadmap

### Phase 1 (MVP)
- Basic search and ingestion functionality
- Core connectors (Gmail, Drive, Browser History)
- Local MCP interface
- Filesystem browser and file management

### Phase 2 (Enhanced Features)
- Natural language response generation
- Advanced connectors (Discord, Slack, iMessage)
- External bridge with authentication
- Bulk ingestion and processing
- Audit dashboard and analytics

### Phase 3 (Advanced Features)
- Online MCP proxy functionality
- Plugin system for custom connectors
- Advanced analytics and insights
- Filesystem encryption
- Multi-user collaboration features

## Unique Selling Points

1. **Intelligent Insights**: Surface macro-level patterns that traditional search can't find
2. **Preprocessing Power**: Analyze all available data rather than just responding to queries
3. **Open Source Ecosystem**: Anyone can build connectors for any data source
4. **Privacy-First**: All processing happens locally with no cloud dependency
5. **Semantic Understanding**: Context-aware search that understands relationships
6. **Desktop Integration**: Native macOS experience with system integration

## Development Guidelines

### Code Organization
- **Feature-Based**: Components organized by feature areas
- **Shared Components**: Reusable UI components in shared locations
- **Type Safety**: Comprehensive TypeScript coverage
- **Testing Ready**: Structure prepared for unit and integration tests

### Integration Patterns
- **Protocol-First**: Use `localbrain://` URLs for all backend communication
- **Event-Driven**: Respond to file changes and system events
- **Background Processing**: Non-blocking operations for better UX
- **Error Recovery**: Graceful failure handling and retry logic

### Performance Considerations
- **Incremental Processing**: Only process changed content
- **Efficient Storage**: Optimized data structures and indexing
- **Caching**: Intelligent caching of frequent operations
- **Resource Management**: Monitor and manage system resources

This architecture provides a solid foundation for the LocalBrain system while remaining flexible for future enhancements and maintaining clear separation between different system components.
