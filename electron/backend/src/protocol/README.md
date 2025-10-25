# Protocol Handler

Manages custom `localbrain://` protocol communications and routing. Handles deep link commands from external sources and routes them to appropriate backend services.

## Core Responsibilities

- **URL Parsing**: Parse and validate `localbrain://` URLs
- **Command Routing**: Direct commands to appropriate backend services
- **Response Formatting**: Structure responses for protocol return values
- **Authentication**: Validate request sources and permissions
- **Error Handling**: Manage protocol-specific errors and responses
- **Integration**: Bridge between external requests and internal services

## Protocol URL Format

**Base Format:**
```
localbrain://[command]?[parameters]
```

**Supported Commands:**

**Search Operations:**
```
localbrain://search?q=natural+language+query
localbrain://search_agentic?keywords=term1,term2&days=7
localbrain://search?query=internship+email&limit=10
```

**File Operations:**
```
localbrain://open?filepath=path/to/file.md
localbrain://summarize?filepath=projects/startup-ideas.md
localbrain://list?path=research
localbrain://list?path=&recursive=true
```

**Ingestion Operations:**
```
localbrain://ingest?text="Meeting notes: discussed project timeline"
localbrain://ingest_bulk?files=document1.pdf,note.txt
localbrain://ingest?text="Email content"&source=gmail&thread=123
```

**System Operations:**
```
localbrain://settings?tab=bridge
localbrain://audit?type=search&days=30
localbrain://status?service=ingestion
```

## Command Processing Flow

1. **URL Interception**: Electron main process captures `localbrain://` URLs
2. **URL Parsing**: Extract command, parameters, and validate format
3. **Authentication**: Verify request source and permissions
4. **Permission Check**: Validate against bridge settings and access controls
5. **Service Routing**: Direct to appropriate backend service (search, ingest, etc.)
6. **Execution**: Process command and generate response
7. **Response Formatting**: Structure return value for protocol handler
8. **Audit Logging**: Record request and response for security tracking

## Service Integration

**Backend Services:**
- **Retrieval Engine**: Handle search and query commands
- **Ingestion Engine**: Process content ingestion requests
- **MCP Server**: Route API tool requests
- **Bridge Service**: Apply access controls and permissions
- **Filesystem**: Manage file operations and directory listing

**Frontend Integration:**
- **URL Generation**: Create protocol URLs from UI actions
- **Response Handling**: Process and display protocol responses
- **Error Display**: Show user-friendly error messages
- **Deep Linking**: Support external links into specific app states

## Security Implementation

**Request Validation:**
- **URL Format**: Validate against allowed command patterns
- **Parameter Sanitization**: Clean and validate all parameters
- **Source Verification**: Authenticate request origin
- **Permission Enforcement**: Apply bridge access controls

**Access Controls:**
- **Command Restrictions**: Limit available commands per user
- **Parameter Limits**: Enforce reasonable parameter constraints
- **Rate Limiting**: Prevent protocol abuse
- **Audit Trail**: Complete logging of all protocol requests

## Response Handling

**Response Format:**
```json
{
  "success": true,
  "command": "search",
  "result": {
    "data": [...],
    "metadata": {...}
  },
  "error": null
}
```

**Error Responses:**
```json
{
  "success": false,
  "command": "search",
  "result": null,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Access to this resource is restricted"
  }
}
```

## External Integration

**Browser Integration:**
- Register `localbrain://` as system protocol handler
- Handle URLs from external applications
- Support deep linking from web pages
- Manage protocol security permissions

**Application Integration:**
- Accept protocol URLs from other desktop applications
- Provide API for generating protocol URLs
- Support command-line protocol execution
- Integration with system URL handlers

## Development Features

**Testing Support:**
- **Mock Protocol Handler**: Test URL parsing and routing
- **Test URL Generation**: Validate protocol URL creation
- **Response Simulation**: Mock backend service responses
- **Error Scenario Testing**: Validate error handling flows

**Debug Tools:**
- **Protocol Logging**: Detailed request/response logging
- **URL Validation**: Real-time URL format checking
- **Performance Monitoring**: Track protocol processing times
- **Integration Testing**: End-to-end protocol flow testing

## Configuration

**Protocol Settings:**
- **Allowed Commands**: Whitelist of permitted operations
- **Parameter Validation**: Rules for parameter formats and limits
- **Response Formats**: Configurable response structures
- **Security Policies**: Access control and authentication rules

**System Registration:**
- **Protocol Registration**: macOS/Windows protocol handler setup
- **URL Scheme Management**: System-level URL scheme configuration
- **Security Permissions**: OS-level protocol access permissions
- **Update Management**: Protocol handler version management

## Future Enhancements

**Advanced Commands:**
- **batch_search**: Multiple queries in single request
- **export**: Export data in various formats
- **backup**: Create system backups
- **restore**: Restore from backups

**Enhanced Security:**
- **API Key Authentication**: Token-based protocol access
- **OAuth Integration**: Third-party authentication for protocol access
- **Request Signing**: Cryptographic verification of requests
- **Audit Analytics**: Advanced analysis of protocol usage patterns

## Integration Examples

**External Application:**
```bash
# Open specific file
open "localbrain://open?filepath=projects/ai-research.md"

# Search for content
open "localbrain://search?q=machine+learning+research"

# Ingest new content
open "localbrain://ingest?text=Research findings from today"
```

**Web Integration:**
```html
<!-- Link to specific LocalBrain content -->
<a href="localbrain://open?filepath=notes/meeting-summary.md">
  View Meeting Notes
</a>

<!-- Search link -->
<a href="localbrain://search?q=project+timeline">
  Search Project Timeline
</a>
```

**Command Line:**
```bash
# Generate protocol URLs programmatically
node -e "console.log('localbrain://search?q=' + encodeURIComponent('my search query'))"

# Test protocol handling
curl "localbrain://search?q=test"  # (if supported)
```
