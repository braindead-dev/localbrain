# Connectors

External data source integrations that feed data into the LocalBrain system. Provides a standardized interface for developers to build custom connectors for any data source.

## Overview

Connectors aggregate data from external locations and return structured data for ingestion. Each connector implements a common interface while handling source-specific authentication, data extraction, and processing requirements.

## Standardized Interface

All connectors must implement these core methods:

**sync()**
- Check for new data since last sync
- Fetch incremental updates efficiently
- Return structured data for ingestion
- Handle rate limiting and API quotas

**propagate()** (optional)
- Perform initial full data import
- Used for first-time connector setup
- Bulk data processing with progress tracking
- Can be merged with sync() for simpler implementations

**validate()**
- Test connection and credentials
- Verify required permissions
- Check API rate limits and quotas
- Return connection status and errors

## Implementation Guidelines

**Authentication:**
- Secure credential storage (encrypted preferences)
- OAuth flows for APIs that support it
- API key management and rotation
- User consent and permission handling

**Error Handling:**
- Graceful failure with retry logic
- Rate limit detection and backoff
- Network timeout handling
- Partial failure recovery

**Data Transformation:**
- Convert source format to LocalBrain schema
- Metadata extraction and normalization
- Content cleaning and sanitization
- Duplicate detection and merging

**Performance:**
- Incremental sync to minimize data transfer
- Batch processing for efficiency
- Local caching when appropriate
- Background processing for large datasets

## Data Schema

**Standardized Output Format:**
```typescript
interface ConnectorData {
  content: string;           // Main text content
  metadata: {
    source: string;          // Source identifier
    timestamp: Date;         // When content was created
    author?: string;         // Content creator
    title?: string;          // Content title/subject
    url?: string;            // Original URL if applicable
    platform: string;        // Source platform (gmail, discord, etc.)
    type: string;            // Content type (message, email, file, etc.)
    [key: string]: any;      // Additional metadata
  };
  attachments?: Array<{     // File attachments
    name: string;
    type: string;
    content: Buffer | string;
    metadata: object;
  }>;
}
```

## Available Connectors

**Communication & Messaging:**
- **Gmail**: Email messages, attachments, and threads
- **Discord**: Server messages, channels, and conversations
- **Slack**: Workspace messages and channels
- **iMessage**: SMS and iMessage conversations
- **LinkedIn**: Messages, posts, and activity

**Productivity & Files:**
- **Google Drive**: Documents, spreadsheets, and files
- **Calendar**: Events, meetings, and scheduling
- **Browser History**: Web browsing activity and bookmarks

**Social Media:**
- **Instagram**: Messages, posts, and stories
- **TikTok**: Direct messages and liked content

## Development Guidelines

**Creating New Connectors:**

1. **Implement Standard Interface**: Follow the sync/propagate/validate pattern
2. **Handle Authentication**: Secure credential management
3. **Data Transformation**: Convert to standard schema
4. **Error Recovery**: Robust error handling and retries
5. **Configuration**: User-configurable settings and filters

**Testing Requirements:**
- Unit tests for data transformation
- Integration tests with test accounts
- Error scenario testing
- Performance benchmarking

**Documentation:**
- Setup and authentication instructions
- Configuration options
- Rate limits and API quotas
- Troubleshooting guide

## Security Considerations

**Data Privacy:**
- No storage of sensitive credentials in plain text
- User consent for data access
- Configurable data retention policies
- Audit logging of all data access

**Access Controls:**
- User-configurable sync scope
- Content filtering options
- Rate limiting compliance
- API abuse prevention

## Performance Optimization

**Incremental Sync:**
- Track last sync timestamp
- Use delta APIs when available
- Efficient change detection
- Minimize unnecessary data transfer

**Batch Processing:**
- Process items in configurable batches
- Parallel processing where safe
- Progress tracking and resumability
- Memory-efficient streaming

## Integration Points

**Ingestion Engine:**
- Receive processed data for chunking and embedding
- Handle file attachments separately
- Update progress and status
- Error reporting and recovery

**Frontend:**
- Display connector status and configuration
- Allow enable/disable and settings management
- Show sync progress and history
- Connection validation and testing

**Bridge Service:**
- Respect user permissions for external access
- Include connector data in search results
- Audit connector usage and access patterns
- Permission-based content filtering

## Configuration Management

**Connector Settings:**
- Stored in `.localbrain/config/` directory
- JSON schema validation
- User interface for configuration
- Migration support for settings updates

**Common Settings:**
- Sync frequency and scheduling
- Content filters and exclusions
- Authentication credentials
- Performance and rate limiting options

## Monitoring & Analytics

**Health Monitoring:**
- Connection status tracking
- Sync success/failure rates
- Performance metrics (sync time, data volume)
- Error reporting and alerting

**Usage Analytics:**
- Data ingestion volume over time
- Popular content types and sources
- User engagement with connector content
- Performance and reliability metrics

## Community Plugin Model

**Open Source Ecosystem:**
Similar to Obsidian's community plugin system, anyone can build custom connectors for LocalBrain. The standardized interface makes it easy for developers to contribute new data sources.

**Plugin Distribution:**
- Community-maintained connector repository
- Plugin discovery and installation through UI
- Automatic updates and version management
- User ratings and reviews

**Developer Resources:**
- Starter templates for common connector types
- Comprehensive API documentation
- Example implementations for reference
- Testing and validation tools

**Publishing Your Connector:**
1. Implement the standardized connector interface
2. Add tests and documentation
3. Submit to community repository
4. Users can install directly from the app

This approach enables rapid ecosystem growth with connectors for any imaginable data source, from fitness trackers to smart home devices to custom APIs.
