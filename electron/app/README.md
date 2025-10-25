# Frontend (Next.js)

The Next.js frontend provides the user interface for LocalBrain, wrapped in an Electron desktop application. Built with React, TypeScript, and Tailwind CSS for a modern, responsive experience.

## Product Features

### Intelligent Search
- **Natural Language Queries**: Send queries to the retrieval agent
- **Multi-Format Results**: Display relevant files, text snippets, or generated responses
- **Context-Aware Ranking**: Results ordered by relevance and recency
- **Real-Time Search**: Progressive result delivery with highlighting

### Quick Note
- **Instant Ingestion**: Send note contents and metadata to ingestion agent
- **Rich Text Support**: Formatted text with basic markdown support
- **Auto-Categorization**: Automatic tagging and organization
- **Metadata Capture**: Timestamp, location, and context information

### Bulk Ingest
- **File Upload**: Support for multiple file formats (PDF, DOC, TXT, MD)
- **Drag & Drop**: Intuitive file selection interface
- **Progress Tracking**: Real-time upload and processing status
- **Batch Processing**: Handle large document collections efficiently

### Filesystem View (Vault Management)
- **Vault Selection**: Choose any directory as your LocalBrain vault (like Obsidian)
- **Multiple Vaults**: Switch between work, personal, research vaults
- **File Browser**: Human-readable directory structure navigation
- **File Management**: Create, edit, and organize markdown files
- **Preview System**: Quick content preview without opening files
- **Search Integration**: Find files directly from filesystem view
- **Cloud Sync**: Vaults can live in Dropbox, iCloud, etc. for cross-device sync

### Bridge Management
- **External Access Control**: Configure which files external tools can access
- **Permission Settings**: Granular access control by directory or file type
- **Security Dashboard**: Monitor and manage external connections
- **Access Logs**: View history of external tool interactions

### Audit Dashboard
- **Search History**: Complete log of all search queries and results
- **Ingestion Tracking**: Monitor document processing and storage
- **Performance Metrics**: System performance and usage analytics
- **Security Events**: Track access attempts and permission changes

## Protocol Integration

All app "actions" (retrieval, quick notes/ingestion, etc.) are sent to the persistent backend via `localbrain://` commands:

**Search Examples:**
```
localbrain://search?query=nvidia+internship+application
localbrain://search_agentic?keywords=internship,nvidia&days=7
```

**File Operations:**
```
localbrain://open?filepath=career/job-search.md
localbrain://list?path=projects
localbrain://summarize?filepath=finance/taxes.md
```

**Ingestion:**
```
localbrain://ingest?text="Email from contact@henr.ee: Great meeting today"
localbrain://ingest_bulk?files=document1.pdf,notes.md
```

**Protocol Handler Flow:**
1. UI generates protocol URL based on user action
2. Electron main process intercepts the URL
3. Request routed to appropriate backend service
4. Response processed and UI updated with results

## Technical Architecture

### Next.js Configuration
- **Static Export**: Optimized for Electron's file:// protocol
- **App Router**: Modern React routing with layouts and loading states
- **TypeScript**: Full type safety throughout the application
- **Tailwind CSS**: Utility-first styling with dark mode support

### Component Structure

```
src/
├── app/                    # Next.js App Router Pages
│   ├── search/            # Search interface and results
│   ├── bridge/            # Bridge management UI
│   ├── settings/          # Configuration and preferences
│   ├── vault/             # Filesystem browser
│   └── api/               # API routes (if needed)
├── components/            # Reusable React Components
│   ├── ui/                # Basic UI components (buttons, inputs)
│   ├── search/            # Search-specific components
│   ├── file-tree/         # File browser components
│   └── bridge/            # Bridge management components
├── hooks/                 # Custom React hooks
├── lib/                   # Utilities and helpers
├── types/                 # TypeScript type definitions
└── global.d.ts           # Global type declarations
```

## Development

### Setup
```bash
# From electron/ directory
npm install          # Installs Next.js dependencies automatically
npm run dev          # Runs Next.js dev server + Electron
```

### Protocol Handler Development
- Test protocol URLs in browser: `localbrain://search?q=test`
- Use Electron dev tools to debug IPC communication
- Mock backend responses during frontend development
- Test deep linking and URL generation

### State Management
- **React State**: Component-level state management
- **Context API**: Global state for user preferences
- **Local Storage**: Persist settings and recent searches
- **Real-time Updates**: Live updates from backend services

## UI Organization

**Page Structure:**
- `/` - Initial vault selection or dashboard
- `/search` - Search interface with filters and results
- `/vault` - File browser and vault management
- `/bridge` - Bridge settings and external access control
- `/settings` - App configuration and preferences
- `/audit` - Activity logs and analytics dashboard

**Component Hierarchy:**
- Shared UI components (buttons, inputs, modals)
- Feature-specific components (search bar, file tree, result cards)
- Layout components (sidebar, header, content area)
- Context providers for global state

## Integration Points

### Python Backend Communication
The frontend communicates with the Python backend services through the Electron main process:

**Communication Flow:**
1. UI action → Generate `localbrain://` URL
2. Electron main process intercepts protocol URL
3. Routes to Python backend service (ingestion, retrieval, etc.)
4. Python processes request and returns JSON response
5. Response flows back through Electron to UI
6. UI updates with results

**Protocol Interface:**
- All backend actions use protocol URLs for consistency
- Supports both sync and async operations
- Error handling and retry logic built-in
- Progress updates for long-running operations

### Electron Integration
- **Window Management**: Desktop-optimized UI behavior
- **Menu Integration**: Native application menus and shortcuts
- **File System Access**: Vault selection and file operations
- **System Events**: Respond to system-level events
- **IPC Bridge**: Direct communication channel with main process

## User Experience

### Desktop Optimization
- **Native Feel**: macOS-style interface and interactions
- **Keyboard Shortcuts**: Full keyboard navigation support
- **Responsive Design**: Adapts to window resizing
- **Performance**: Optimized for desktop hardware

### Search Interface
- **Query Builder**: Advanced search options and filters
- **Result Preview**: Quick content preview without opening
- **Action Buttons**: Direct actions (open, summarize, etc.)
- **History**: Recent searches and suggestions

## Security Considerations

### Content Security
- **Input Sanitization**: Validate and clean all user inputs
- **XSS Protection**: Prevent script injection attacks
- **CSP Compliance**: Content Security Policy headers
- **Secure Defaults**: Privacy-focused default settings

### External Access
- **Permission Prompts**: Clear user consent for external access
- **Scope Limitations**: Restrict external tool capabilities
- **Audit Display**: Show users what external tools are accessing
- **Revoke Access**: Easy disable of external permissions