# Discord Connector

Processes Discord Direct Messages (DMs) for ingestion into LocalBrain. This connector focuses exclusively on private conversations, not server messages.

## ⚠️ Important: DMs Only

This connector **only syncs Direct Messages (DMs)**. Server/guild messages are not supported. This is by design to focus on personal conversations and maintain privacy.

## Core Functionality

- **DM Sync**: Fetch direct messages from all DM channels
- **Message History**: Retrieve messages with time-based filtering
- **User Attribution**: Track sender and recipient information
- **Media Links**: Capture attachment and embed URLs
- **Conversation Context**: Maintain DM thread context

## Authentication & Setup

**Bot Token Integration:**
- Discord bot creation in Developer Portal
- Simple token-based authentication (no OAuth needed)
- Message Content Intent required (privileged intent)
- Secure local token storage

**Bot Setup:**
- Bot creation and configuration
- Authorization to access your account
- Read-only permissions (cannot send messages)
- DM-specific access permissions

See [SETUP.md](./SETUP.md) for detailed setup instructions.

## Data Processing

**Message Content:**
- Text message extraction and cleaning
- Message threading and reply chains
- Timestamp and edit history
- Reaction and interaction data
- Message formatting (bold, italic, code blocks)

**Metadata Extraction:**
- User information (username, discriminator, avatar)
- Channel details (name, type, topic)
- Server information (name, member count, roles)
- Message IDs and threading relationships
- Pin status and system messages

**Media & Attachments:**
- Image download and processing
- File attachment handling
- Embedded content extraction (links, videos, tweets)
- Media metadata and descriptions
- File type validation and size limits

## DM Management

**Supported:**
- ✅ One-on-one direct messages
- ✅ Message history (after bot authorization)
- ✅ Text content
- ✅ Attachment URLs
- ✅ Embed content
- ✅ User information

**Not Supported:**
- ❌ Server/guild messages
- ❌ Group DMs (not yet implemented)
- ❌ Voice channel messages
- ❌ Messages before bot authorization
- ❌ Server channels of any kind

## Privacy & Security

**Content Filtering:**
- Time-based filtering (sync last N hours/days)
- Empty message skipping
- Optional bot message filtering
- Attachment URL preservation

**Access Controls:**
- DM-only access (no servers)
- Read-only permissions
- Date range limitations
- Message count limits per DM
- Local token storage only

## Sync Strategy

**Current Implementation:**
- Manual sync via API endpoint
- Time-based filtering (last N hours)
- Message limit per DM channel
- Async message fetching
- Discord.py handles rate limiting

**Performance Features:**
- Async message processing
- Parallel DM channel fetching
- Message deduplication via message IDs
- Automatic rate limit compliance
- Error handling and retry logic

**Planned:**
- Auto-sync background task
- Real-time webhook integration
- Incremental delta sync

## Conversation Context

**Threading Support:**
- Reply chain reconstruction
- Message context preservation
- Conversation topic identification
- User interaction patterns
- Temporal conversation flow

**Contextual Insights:**
- Topic modeling and conversation themes
- User relationship mapping
- Channel activity patterns
- Important conversation identification
- Decision and action tracking

## Integration Points

**Ingestion Engine:**
- Send processed messages for chunking
- Provide conversation context for embedding
- Handle media files for separate processing
- Maintain threading relationships

**Frontend:**
- Display sync status and server list
- Allow configuration of channel settings
- Show connected server information
- Enable/disable Discord processing

**Bridge Service:**
- Include Discord DM results in search responses
- Audit Discord message access
- Privacy-focused DM handling
- Source attribution in search results

## Advanced Features

**Smart Filtering:**
- Important message detection
- Conversation summarization
- Topic extraction and categorization
- Sentiment analysis (if enabled)
- Action item identification

**Media Processing:**
- Image OCR and text extraction
- Video transcription (if available)
- Embedded content expansion
- Media metadata indexing
- Thumbnail generation and caching

## Configuration Options

**Sync Settings:**
- Time window (hours or days to look back)
- Max messages per DM channel
- Auto-ingest toggle
- Sync frequency

**Content Filters:**
- Bot message filtering (optional)
- Date range limitations
- Message count limits
- Empty message skipping

**Privacy Settings:**
- Local-only token storage
- No cloud sync
- Read-only bot permissions
- Secure credential management

## Status

**Implemented:** ✅
- Bot token authentication
- DM message fetching
- Time-based filtering
- Metadata extraction
- Text and attachment handling
- API endpoints
- Status checking

**Planned:** 🚧
- Auto-sync background task
- Group DM support
- Real-time webhooks
- Advanced filtering
- Media download

## Quick Start

```bash
# Install dependencies
pip install discord.py>=2.3.2

# Start daemon
python src/daemon.py

# Save bot token
curl -X POST http://localhost:8765/connectors/discord/auth/save-token \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_BOT_TOKEN"}'

# Sync DMs
curl -X POST "http://localhost:8765/connectors/discord/sync?hours=24&ingest=true"
```

See [SETUP.md](./SETUP.md) for detailed instructions.
