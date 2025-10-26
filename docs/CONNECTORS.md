# Connector System

**Plugin architecture for syncing external data sources**

---

## Overview

Connectors fetch data from external sources (Gmail, Discord, iMessage, etc.) and convert it into markdown files in your vault. They're implemented as plugins - just drop a new connector in the directory and it's auto-discovered.

---

## How It Works

### Plugin Discovery

1. On daemon startup, `ConnectorManager` scans `connectors/` directory
2. Finds any `<name>_connector.py` files
3. Loads classes that inherit from `BaseConnector`
4. Automatically generates API routes for each connector

**Result**: Zero configuration needed. New connectors work immediately.

### Data Flow

```
External API (Gmail, Discord, etc.)
    ↓
Connector fetches new data
    ↓
Converts to ConnectorData format
    ↓
Saves as markdown in vault/Connectors/<name>/
    ↓
Available for search
```

---

## Available Connectors

### Gmail
- **Auth**: OAuth 2.0
- **Syncs**: Emails, threads, attachments
- **Frequency**: Every 10 minutes
- **Format**: Email → Markdown with metadata

### Discord
- **Auth**: Bot token
- **Syncs**: DMs, channel messages
- **Frequency**: Every 10 minutes
- **Format**: Message → Markdown with user info

### Browser History
- **Auth**: None (local SQLite)
- **Syncs**: Web browsing history
- **Format**: URL visits → Markdown

### Calendar
- **Auth**: OAuth 2.0
- **Syncs**: Events, meetings
- **Format**: Event → Markdown with dates

---

## Creating a Connector

### 1. Basic Structure

Create `connectors/my_service/my_service_connector.py`:

```python
from connectors.base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorStatus,
    ConnectorData
)
from datetime import datetime
from typing import List, Optional

class MyServiceConnector(BaseConnector):
    
    def get_metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            id="my_service",
            name="My Service",
            description="Syncs data from My Service",
            version="1.0.0",
            author="Your Name",
            auth_type="api_key",  # or "oauth", "token", "none"
            sync_interval_minutes=10
        )
    
    def has_updates(self, since: Optional[datetime] = None) -> bool:
        # Check if new data is available
        # Return True if yes, False if no
        return True
    
    def fetch_updates(
        self, 
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[ConnectorData]:
        # Fetch data from API
        # Convert to standard format
        items = []
        
        for item in self._fetch_from_api():
            items.append(ConnectorData(
                content=item['text'],
                source_id=item['id'],
                timestamp=item['created_at'],
                metadata={
                    "platform": "my_service",
                    "type": "message",
                    "author": item['author'],
                    "title": item['title']
                }
            ))
        
        return items
    
    def get_status(self) -> ConnectorStatus:
        return ConnectorStatus(
            connected=True,
            authenticated=self._is_authenticated(),
            last_sync=self._get_last_sync()
        )
```

### 2. That's It!

Restart daemon and your connector is live:

```bash
GET /connectors
# Returns: [..., {"id": "my_service", "name": "My Service"}, ...]

POST /connectors/my_service/sync
# Triggers sync
```

---

## API Endpoints

All connectors automatically get these endpoints:

### List All Connectors
```bash
GET /connectors

Response:
{
  "success": true,
  "connectors": [
    {
      "id": "gmail",
      "name": "Gmail",
      "description": "Syncs Gmail emails",
      "auth_type": "oauth"
    }
  ]
}
```

### Get Status
```bash
GET /connectors/{connector_id}/status

Response:
{
  "success": true,
  "status": {
    "connected": true,
    "authenticated": true,
    "last_sync": "2025-10-25T16:00:00Z",
    "total_items_synced": 150
  }
}
```

### Authenticate
```bash
POST /connectors/{connector_id}/auth
Body: {credentials...}

Response:
{
  "success": true,
  "message": "Authentication successful"
}
```

### Sync Data
```bash
POST /connectors/{connector_id}/sync?auto_ingest=true&limit=100

Response:
{
  "success": true,
  "items_fetched": 25,
  "items_ingested": 25,
  "last_sync": "2025-10-25T16:05:00Z"
}
```

### Sync All
```bash
POST /connectors/sync-all

Response:
{
  "success": true,
  "results": {
    "gmail": {"items_fetched": 10, "items_ingested": 10},
    "discord": {"items_fetched": 5, "items_ingested": 5}
  }
}
```

### Disconnect
```bash
POST /connectors/{connector_id}/auth/revoke

Response:
{
  "success": true,
  "message": "gmail disconnected"
}
```

---

## Authentication Types

### OAuth 2.0 (Gmail, Calendar)
```python
auth_type="oauth"

def authenticate(self, credentials):
    code = credentials.get('code')
    # Exchange for tokens
    # Store tokens securely
    return True, None
```

### API Key (Many services)
```python
auth_type="api_key"

def authenticate(self, credentials):
    api_key = credentials.get('api_key')
    # Validate key
    # Store securely
    return True, None
```

### Token (Discord, Slack)
```python
auth_type="token"

def authenticate(self, credentials):
    token = credentials.get('token')
    # Test token
    # Store securely
    return True, None
```

### None (Local sources)
```python
auth_type="none"
# No authentication needed
```

---

## Configuration Storage

Each connector gets its own directory:

```
~/.localbrain/connectors/
├── gmail/
│   ├── state.json          # Last sync timestamp
│   ├── credentials.json    # OAuth tokens
│   └── config.json         # User settings
├── discord/
│   ├── state.json
│   ├── token.json
│   └── config.json
└── <connector_id>/
    └── ...
```

Access in your connector via `self.config_dir`.

---

## Auto-Sync

The daemon automatically syncs all connected connectors:

```python
# Runs every 10 minutes
async def auto_sync_connectors():
    manager = get_connector_manager(vault_path=VAULT_PATH)
    results = manager.sync_all(auto_ingest=True)
    
    for connector_id, result in results.items():
        if result.success:
            logger.info(f"✅ {connector_id}: {result.items_ingested} items")
```

---

## Testing Your Connector

### 1. Check Discovery
```bash
curl http://localhost:8765/connectors
# Should list your connector
```

### 2. Check Status
```bash
curl http://localhost:8765/connectors/my_service/status
```

### 3. Test Sync
```bash
curl -X POST http://localhost:8765/connectors/my_service/sync
```

---

## Best Practices

### Do ✅
- Handle rate limits gracefully
- Store minimal state
- Return empty list on errors (don't crash)
- Use incremental sync (respect `since` param)
- Add clear error messages
- Encrypt sensitive credentials

### Don't ❌
- Make blocking calls in `has_updates()`
- Return gigabytes of data at once
- Store passwords in plain text
- Crash on network errors
- Ignore rate limits
- Hardcode paths

---

## Connector Ideas

### Easy to Add
- **Beeper** - Unified messaging
- **Slack** - Workspace messages
- **LinkedIn** - Messages and posts
- **Twitter/X** - DMs and tweets
- **WhatsApp** - Messages (via unofficial API)
- **Telegram** - Messages
- **Notion** - Pages and databases
- **Todoist** - Tasks and projects
- **Spotify** - Listening history
- **Apple Notes** - Local notes

### Advanced
- **iMessage** - Via chat.db SQLite
- **Signal** - Via local database
- **Obsidian** - Sync vault files
- **Roam Research** - Graph database
- **Superhuman** - Email client
- **Arc Browser** - Browsing history

---

## Architecture

```
ConnectorManager
    ↓ discovers
Connector Plugins (in connectors/ directory)
    ↓ implements
BaseConnector Interface
    ↓ uses
Generic API Routes (connector_api.py)
    ↓ exposes
REST Endpoints (for all connectors)
```

**Result**: Add one file → Get full API support automatically.

---

## Related Documentation

- [Plugin Architecture](../electron/backend/src/connectors/PLUGIN_ARCHITECTURE.md) - Technical details
- [API Reference](API.md) - REST endpoints
- [Architecture](ARCHITECTURE.md) - System overview
