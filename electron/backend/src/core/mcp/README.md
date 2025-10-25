# Local MCP Server

Provides a local API interface for external tools and integrations. Implements the Model Context Protocol to enable external applications to access LocalBrain functionality.

## Core Responsibilities

- **API Endpoint Management**: HTTP/WebSocket servers for external access
- **Tool Implementation**: MCP-compliant tools (search, summarize, open, list)
- **Request Processing**: Parse and validate incoming requests
- **Response Formatting**: Structure responses according to MCP specification
- **Authentication**: Validate external tool permissions
- **Rate Limiting**: Prevent abuse and ensure performance

## MCP Tools

**search**
- **Purpose**: Natural language search across personal knowledge base
- **Input**: Query string or array of queries
- **Output**: Relevant chunks, quotes, and file references
- **Use Case**: AI assistants, external search interfaces

**search_agentic**
- **Purpose**: Structured search with specific parameters
- **Input**: Command-based syntax with filters (keywords, dates, etc.)
- **Output**: Exact matches and filtered results
- **Use Case**: Automated tools, batch processing

**open**
- **Purpose**: Retrieve full contents of specific files
- **Input**: File path within `.localbrain/` directory
- **Output**: Complete file content with metadata
- **Use Case**: External editors, backup systems

**summarize**
- **Purpose**: Generate summaries of files or search results
- **Input**: File path or content to summarize
- **Output**: Concise summary with key points
- **Use Case**: Quick overview, content preview

**list**
- **Purpose**: Browse directory structure and available files
- **Input**: Directory path (optional, defaults to root)
- **Output**: File tree with metadata (size, dates, types)
- **Use Case**: File management, navigation

## Protocol Integration

**localbrain:// Command Processing:**
- Intercept and parse protocol URLs from external sources
- Route commands to appropriate MCP tools
- Format responses for protocol return values
- Handle authentication and permissions

**Deep Link Examples:**
```
localbrain://search?q=internship+applications
localbrain://open?filepath=career/job-search.md
localbrain://search_agentic?keywords=internship,nvidia&days=7
localbrain://summarize?filepath=finance/taxes.md
localbrain://list?path=projects
```

## Security & Access Control

**Permission System:**
- **Bridge Settings**: User-configurable file access restrictions
- **Tool Permissions**: Granular control over which tools are available
- **Scope Limitations**: Restrict queries to specific directories or file types
- **Authentication**: Validate external tool credentials

**Audit Logging:**
- Complete record of all MCP requests and responses
- Timestamp, source, query, and result logging
- Performance metrics and error tracking
- Privacy-compliant logging (no sensitive data)

## Configuration

**Server Settings:**
- **Port Configuration**: HTTP/WebSocket server ports
- **CORS Policies**: Cross-origin request handling
- **Rate Limits**: Request throttling per endpoint
- **Timeout Settings**: Maximum processing time per request

**Tool Configuration:**
- **Search Parameters**: Default ranking and filtering options
- **File Access**: Allowed directories and file types
- **Response Limits**: Maximum results returned
- **Caching**: Response caching strategies

## Future Enhancements

**Online MCP Proxy (Optional):**
- Remote URL endpoint for local MCP access
- Authentication and API key management
- Request forwarding to local MCP server
- Usage analytics and monitoring

**Advanced Tools:**
- **batch_search**: Multiple queries in single request
- **similarity**: Find related content and connections
- **timeline**: Search within date ranges
- **export**: Export content in various formats

## Integration Points

- **Frontend**: Route UI search requests through MCP interface
- **Protocol Handler**: Process localbrain:// URLs via MCP tools
- **Bridge Service**: Enforce access permissions and logging
- **External Tools**: Provide API access for third-party applications
- **Connectors**: Use MCP tools for data validation and processing

## Development

**MCP Specification Compliance:**
- Standard MCP protocol implementation
- Tool discovery and capability advertising
- Error handling and status reporting
- Extensible tool framework for future additions
