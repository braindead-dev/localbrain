# Filesystem

Local file management and operations for LocalBrain. Manages the `.localbrain/` directory structure, file operations, and integration with the document processing pipeline.

## Core Responsibilities

- **Directory Management**: Create and maintain `.localbrain/` structure
- **File Operations**: Create, read, update, and delete markdown files
- **Path Resolution**: Handle file paths and directory navigation
- **Content Processing**: Coordinate with ingestion for file changes
- **Backup & Recovery**: File backup and version management
- **Security**: File access permissions and encryption (optional)

## Vault Selection

**Obsidian-Style Vault System:**
Users can select any directory on their filesystem to act as their LocalBrain vault. This directory becomes the `.localbrain/` root and can be:
- Synced across devices via cloud storage (Dropbox, iCloud, etc.)
- Backed up and version controlled (Git)
- Switched between multiple vaults for different contexts
- Shared with specific collaborators (future feature)

**Vault Setup:**
1. User selects a directory through file picker
2. LocalBrain initializes the vault structure if needed
3. Vault path stored in app preferences
4. All data processing scoped to selected vault
5. Switch vaults anytime from settings

**Multiple Vault Support:**
- Work vault: Professional projects and notes
- Personal vault: Personal knowledge and journal
- Research vault: Academic research and papers
- Quick switch between vaults without restart

## Directory Structure

**`.localbrain/` Root Directory (within selected vault):**
```
.localbrain/
├── app.json              # Application configuration and settings
├── notes/                # User-created markdown files
│   ├── projects/         # Project-related notes
│   ├── research/         # Research and learning notes
│   ├── personal/         # Personal notes and journal
│   └── archive/          # Archived or completed items
├── attachments/          # File attachments from connectors
│   ├── images/           # Images from emails, Discord, etc.
│   ├── documents/        # PDFs, DOCs, and other documents
│   └── media/            # Audio, video, and other media files
├── config/               # Connector and system configuration
│   ├── connectors/       # Connector-specific settings
│   ├── bridge/           # Bridge access permissions
│   └── system/           # System-wide settings
├── data/                 # Internal database and cache files
│   ├── embeddings/       # Vector embeddings database
│   ├── chunks/            # Document chunks storage
│   └── metadata/          # File and source metadata
└── logs/                 # Application logs and audit trails
    ├── ingestion/        # Ingestion process logs
    ├── search/            # Search query logs
    └── system/           # System events and errors
```

## File Management

**Markdown File Operations:**
- **Auto-Creation**: Initialize files with purpose summary
- **Content Updates**: Handle file modifications and updates
- **Metadata Tracking**: Monitor file changes and timestamps
- **Version Control**: Track file versions and changes

**Standardized File Format:**
```markdown
---
title: "File Purpose Summary"
created: "2024-01-15T10:30:00Z"
updated: "2024-01-15T10:30:00Z"
source: "manual"  # manual, gmail, discord, etc.
tags: ["project", "research"]
---

# Main Content

## Observations
- Key insight 1 with source citation
- Key insight 2 with supporting evidence

## Sources
**Source 1:** [Platform] - [Timestamp]
[Direct quotation or evidence]
[URL if applicable]

**Source 2:** [Platform] - [Timestamp]
[Supporting documentation]
```

## Integration Points

**Ingestion Engine:**
- **File Change Detection**: Monitor file modifications
- **Reprocessing Trigger**: Re-chunk and re-embed on changes
- **Content Validation**: Validate file format and structure
- **Metadata Updates**: Update file metadata and timestamps

**Frontend:**
- **File Browser**: Display directory structure and files
- **File Operations**: Create, edit, and delete files
- **Content Preview**: Show file content without full load
- **Path Resolution**: Convert UI paths to filesystem paths

**Database:**
- **File Tracking**: Maintain file-to-chunk relationships
- **Metadata Sync**: Keep file metadata synchronized
- **Change Detection**: Identify modified files for reprocessing
- **Cleanup Operations**: Remove orphaned chunks and data

**Connectors:**
- **File Creation**: Create files from external data sources
- **Attachment Storage**: Store connector attachments in filesystem
- **Path Management**: Generate appropriate file paths for content
- **Content Organization**: Auto-organize by source and type

## Configuration Management

**App Configuration (`app.json`):**
```json
{
  "version": "1.0.0",
  "created": "2024-01-15T10:00:00Z",
  "settings": {
    "autoBackup": true,
    "encryption": false,
    "retentionDays": 365,
    "maxFileSize": "10MB"
  },
  "bridge": {
    "enabled": true,
    "allowedDirectories": ["notes", "projects"],
    "externalAccess": false
  },
  "connectors": {
    "gmail": {
      "enabled": true,
      "syncFrequency": "hourly",
      "labels": ["INBOX", "IMPORTANT"]
    }
  }
}
```

## File Processing Pipeline

1. **File Creation/Modification**: User or connector creates/updates file
2. **Change Detection**: Filesystem watcher identifies changes
3. **Validation**: Verify file format and content
4. **Ingestion**: Send to ingestion engine for processing
5. **Chunking**: Split into searchable segments
6. **Embedding**: Generate vector representations
7. **Storage**: Save chunks and embeddings to database
8. **Indexing**: Update search indexes

## Security & Privacy

**Access Controls:**
- **Directory Permissions**: Restrict access by directory
- **File Encryption**: Optional encryption for sensitive files
- **Backup Security**: Secure backup and recovery
- **Audit Logging**: Track all file operations

**Data Protection:**
- **Sensitive Content Detection**: Identify and flag sensitive files
- **Retention Policies**: Automatic cleanup of old content
- **Backup Management**: Secure backup creation and storage
- **Access Logging**: Complete audit trail of file access

## Performance Features

**Efficient Operations:**
- **Incremental Updates**: Only process changed content
- **Background Processing**: Non-blocking file operations
- **Caching**: Cache frequently accessed files and metadata
- **Batch Operations**: Process multiple files efficiently

**Resource Management:**
- **File Size Limits**: Prevent oversized file ingestion
- **Storage Quotas**: Monitor and manage storage usage
- **Cleanup Operations**: Remove temporary and orphaned files
- **Compression**: Optional file compression for storage

## Development Features

**File System Simulation:**
- **Mock File System**: Test file operations in development
- **Path Resolution Testing**: Validate path handling logic
- **Change Detection Testing**: Verify file watcher functionality
- **Integration Testing**: End-to-end file processing tests

**Development Tools:**
- **File Browser**: Development interface for file management
- **Path Utilities**: Helper functions for path manipulation
- **Validation Tools**: File format and content validation
- **Performance Monitoring**: Track file operation performance

## Future Enhancements

**Advanced Features:**
- **File Versioning**: Git-like version control for files
- **Collaboration**: Multi-user file editing and sync
- **Advanced Search**: File content and metadata search
- **Smart Organization**: AI-powered file categorization

**Integration Expansion:**
- **Cloud Sync**: Synchronize with cloud storage providers
- **External Editors**: Integration with external markdown editors
- **File Format Support**: Extended format support (PDF, DOC, etc.)
- **Export Capabilities**: Export files in multiple formats
