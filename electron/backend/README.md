# Backend Services

Background services that handle data processing, search, and external integrations for LocalBrain. Runs as a background process managed by the Electron main process.

## Overview

The backend processes commands via the `localbrain://` protocol and provides a Local MCP interface for external tools. It manages data ingestion, retrieval, and external connector integration.

## Protocol System

The backend processes custom deep link commands:

```
localbrain://search?q=internship+email
localbrain://open?filepath=finance/banking.md
localbrain://search_agentic?keywords=internship,nvidia&days=7
localbrain://ingest?text="Email from contact@henr.ee: fuck you"
```

**Protocol Handler Flow:**
1. System intercepts `localbrain://` URLs
2. Electron main process receives the request
3. Request parsed and routed to appropriate backend service
4. Response formatted and returned

## Local MCP / API

Provides tools for external integrations with configurable access permissions:

### Core Tools

**search**
- **Input**: Natural language search query, or list of queries
- **Output**: Most relevant chunks/quotes from the filesystem
- **Scope**: Defined by bridge settings (user-configurable file access)

**search_agentic**
- **Input**: Syntax/command-based search queries
- **Output**: Exact results matching specific criteria

**open**
- **Input**: Filepath
- **Output**: Full contents of the file

**summarize**
- **Input**: Filepath
- **Output**: Summary of the file content

**list**
- **Input**: Folder directory
- **Output**: File tree of the specified directory

### Future Tools (Optional)
- **Online MCP Proxy**: Turn local MCP into remote URL endpoint
- **Authentication**: External source validation
- **Rate Limiting**: Request throttling for security

## Ingestion Engine

Processes documents and data from multiple sources with intelligent extraction:

**Guardrails:**
- Never ingest sensitive data (passwords, SSNs, credit cards, etc.)
- Automatic filtering and sanitization

**Document Processing:**
- Chunk documents for embedding
- Generate standardized file structures
- Extract insights and observations
- Create metadata and source citations

**Markdown File Structure:**
- Auto-initialize with purpose summary paragraph
- Structure: insights/observations + sources
- Wikipedia-style observations and facts
- Claims linked to supporting evidence with metadata
- Source metadata: timestamp, platform, URL, direct quotations

## Retrieval Engine

Semantic search and query processing across all ingested content:

**Query Processing:**
- Natural language understanding
- Context-aware result ranking
- Multi-query support and aggregation

**Database Integration:**
- Vector embeddings for semantic similarity
- Chunk-based retrieval with metadata
- File modification triggers re-chunking and re-embedding

## Connector System

Standardized interface for external data sources. Each connector implements:

**Core Functions:**
- **Sync**: Check for new data and feed to ingestion agent
- **Propagate/Initialize** (optional): First-time sync of existing data

**Standardized Interface:**
- Common configuration schema
- Error handling and retry logic
- Rate limiting and API quota management
- Authentication and permission management

**Available Connectors:**
- Browser History
- Gmail (emails and attachments)
- Google Drive (documents and files)
- Calendar (events and scheduling)
- Discord (messages and channels)
- iMessage (conversations)
- Slack (messages and channels)
- LinkedIn (activity and connections)
- Instagram (messages and posts)
- TikTok (DMs and liked content)

## Security & Access Control

**Bridge Settings:**
- User-configurable file access permissions
- Granular connector permissions
- Queryable scope restrictions

**Data Protection:**
- Sensitive data filtering at ingestion
- Optional filesystem encryption
- Complete audit logging of all requests

**Configuration:**
- Settings stored in `.localbrain/app.json`
- Bridge access toggles and restrictions
- Connector authentication and permissions

## Development

The backend runs as a Node.js service managed by the Electron main process. Services communicate via:

- **IPC**: Inter-process communication with Electron main
- **HTTP/WebSocket**: Internal service communication
- **File System**: Persistent data storage and configuration
- **Protocol Handler**: Custom URL scheme processing

**Service Architecture:**
- **Ingestion Service**: Document processing and storage
- **Retrieval Service**: Search and query handling
- **MCP Service**: External API interface
- **Bridge Service**: Access control and audit logging
- **Connector Services**: External data integration