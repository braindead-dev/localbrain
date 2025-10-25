# Bridge Service

Manages external access and communication with the LocalBrain system. Controls which files and data external tools can access while maintaining security and audit logging.

## Core Responsibilities

- **Access Control**: Manage external tool permissions and file access
- **Authentication**: Validate external tool credentials and requests
- **Audit Logging**: Track all external access and system interactions
- **Security Enforcement**: Apply user-configured access restrictions
- **Request Routing**: Direct external requests to appropriate services
- **Rate Limiting**: Prevent abuse and ensure system performance

## External Access Management

**Permission System:**
- **File Access Control**: Restrict access by directory, file type, or content
- **Tool Permissions**: Control which MCP tools are available externally
- **User Consent**: Require explicit user approval for external access
- **Scope Configuration**: Limit external queries to specific data ranges

**Security Features:**
- **Request Validation**: Verify all external requests for authenticity
- **Content Filtering**: Apply access controls to search results
- **Rate Limiting**: Prevent API abuse and resource exhaustion
- **Timeout Management**: Limit processing time for external requests

## Audit & Logging

**Comprehensive Tracking:**
- **Request Logging**: All external requests with timestamps and sources
- **Access Patterns**: Monitor which files are accessed by external tools
- **Performance Metrics**: Track response times and system impact
- **Security Events**: Log suspicious activity and access violations

**Audit Dashboard Data:**
- External tool connection history
- File access frequency and patterns
- Permission changes and updates
- System performance impact of external access

## Configuration Management

**Bridge Settings (`.localbrain/app.json`):**
```json
{
  "bridge": {
    "enabled": true,
    "allowedDirectories": ["projects", "notes"],
    "blockedDirectories": ["private", "sensitive"],
    "allowedTools": ["search", "list"],
    "maxRequestsPerHour": 1000,
    "requireApproval": true
  }
}
```

**Access Levels:**
- **Full Access**: Complete filesystem access (admin only)
- **Restricted Access**: Limited to approved directories and tools
- **Read-Only**: Search and list operations only
- **Disabled**: No external access allowed

## Integration Points

**MCP Server:**
- Apply bridge permissions to MCP tool requests
- Filter search results based on access controls
- Log all MCP API interactions
- Enforce rate limiting on external tools

**Frontend:**
- Bridge settings management interface
- Real-time permission configuration
- Audit dashboard for external access
- Security alerts and notifications

**Protocol Handler:**
- Apply bridge restrictions to `localbrain://` URLs
- Validate external protocol requests
- Route approved requests to backend services
- Block unauthorized access attempts

## Security Enforcement

**Access Control Implementation:**
1. **Request Reception**: Receive external request via MCP or protocol
2. **Authentication Check**: Validate request source and credentials
3. **Permission Validation**: Check user-configured access permissions
4. **Content Filtering**: Apply restrictions to data access
5. **Audit Logging**: Record access for security monitoring
6. **Response Processing**: Format and return approved content

**Security Monitoring:**
- **Intrusion Detection**: Identify suspicious access patterns
- **Anomaly Detection**: Alert on unusual external activity
- **Access Violation**: Block and log unauthorized attempts
- **Performance Impact**: Monitor system load from external access

## External Tool Integration

**MCP API Access:**
- Tool availability based on bridge settings
- Response filtering for sensitive content
- Request attribution for audit trails
- Rate limiting per external source

**Protocol URL Handling:**
- Deep link validation and routing
- Permission-based command execution
- Response formatting for external consumption
- Access logging for security compliance

## Development Features

**Testing Support:**
- Mock external tool requests for development
- Permission testing and validation
- Audit log verification
- Security scenario testing

**Configuration Management:**
- Settings validation and migration
- User interface for permission management
- Real-time settings updates
- Backup and restore of security configurations

## Future Enhancements

**Advanced Security:**
- **API Key Management**: Token-based authentication for external tools
- **OAuth Integration**: Third-party authentication support
- **Access Analytics**: Detailed usage patterns and insights
- **Automated Threat Detection**: AI-powered security monitoring

**Enhanced Controls:**
- **Time-Based Access**: Schedule external access permissions
- **Content-Based Filtering**: Dynamic filtering based on content sensitivity
- **Geographic Restrictions**: Location-based access controls
- **Advanced Audit**: Detailed behavioral analysis and reporting
