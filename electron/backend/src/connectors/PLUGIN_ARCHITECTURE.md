# LocalBrain Connector Plugin Architecture

**Status**: ✅ Refactored from hardcoded mess to clean plugin system (October 2025)

---

## Overview

Connectors are **plugins** that fetch data from external sources (Gmail, Discord, iMessage, etc.) and convert it into a standardized format for ingestion.

**Before**: Hardcoded routes for each connector in `daemon.py` 🤮  
**After**: Dynamic plugin system with auto-discovery ✨

---

## Core Principles

1. **Plugins, not hardcode** - Drop a connector in `src/connectors/<name>/` and it's auto-discovered
2. **Standardized interface** - All connectors implement `BaseConnector`
3. **Generic API routes** - One set of routes works for ALL connectors
4. **Simple structure** - Check for updates → Fetch → Ingest. That's it.

---

## File Structure

```
src/connectors/
├── base_connector.py        # Base class ALL connectors inherit from
├── connector_manager.py      # Auto-discovers and loads connectors
├── connector_api.py          # Generic API routes for all connectors
├── PLUGIN_ARCHITECTURE.md    # This file
│
├── gmail/                    # Example connector
│   ├── gmail_connector.py    # Implements BaseConnector
│   └── README.md            # Setup instructions
│
├── discord/
│   ├── discord_connector.py
│   └── README.md
│
└── <your-connector>/        # Add your own!
    ├── <name>_connector.py  # Must follow naming convention
    └── README.md
```

---

## Creating a Connector

### 1. Basic Structure

Create a new directory: `src/connectors/my_connector/`

Create `my_connector_connector.py`:

```python
from connectors.base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorStatus,
    ConnectorData
)
from datetime import datetime
from typing import List, Optional

class MyConnectorConnector(BaseConnector):
    """My awesome connector!"""
    
    def get_metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            id="my_connector",           # Unique ID (lowercase, no spaces)
            name="My Connector",          # Display name
            description="Fetches data from My Service",
            version="1.0.0",
            author="Your Name",
            auth_type="api_key",          # "oauth", "api_key", "token", "none"
            requires_config=True,
            sync_interval_minutes=10,
            capabilities=["read"]
        )
    
    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """Check if new data is available."""
        # Query your API: "are there new items since {since}?"
        # Return True if yes, False if no
        return True  # Implement your logic
    
    def fetch_updates(self, 
                     since: Optional[datetime] = None,
                     limit: Optional[int] = None) -> List[ConnectorData]:
        """Fetch new data."""
        items = []
        
        # Fetch from your API
        raw_data = self._fetch_from_api(since, limit)
        
        # Convert to standardized format
        for item in raw_data:
            items.append(ConnectorData(
                content=item['text'],          # Main content
                source_id=item['id'],          # Unique ID from source
                timestamp=item['created_at'],  # When it was created
                metadata={
                    "platform": "my_connector",
                    "type": "message",
                    "author": item['author'],
                    "title": item['title']
                }
            ))
        
        return items
    
    def get_status(self) -> ConnectorStatus:
        """Return current status."""
        # Check if connected, authenticated, etc.
        return ConnectorStatus(
            connected=True,
            authenticated=self._is_authenticated(),
            last_sync=self._get_last_sync(),
            config_valid=True
        )
    
    def _fetch_from_api(self, since, limit):
        """Your API-specific fetch logic."""
        # Implement your API calls here
        pass
    
    def _is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        # Implement your auth check
        return True
```

### 2. That's It!

The connector manager will auto-discover it. No registration needed.

---

## API Endpoints

**All connectors automatically get these endpoints:**

### List Connectors
```bash
GET /connectors
```

Returns all available connectors.

### Connector Status
```bash
GET /connectors/{connector_id}/status
```

Example: `GET /connectors/gmail/status`

### Authenticate
```bash
POST /connectors/{connector_id}/auth
Body: {credentials...}
```

Example:
```bash
POST /connectors/gmail/auth
{"code": "oauth_code", "state": "oauth_state"}
```

### Sync
```bash
POST /connectors/{connector_id}/sync?auto_ingest=true&limit=100
```

Example: `POST /connectors/discord/sync?auto_ingest=true`

### Sync All
```bash
POST /connectors/sync-all?auto_ingest=true
```

### Revoke Access
```bash
POST /connectors/{connector_id}/auth/revoke
```

---

## Data Flow

```
1. User triggers sync (manual or automatic)
   ↓
2. has_updates() checks if new data exists
   ↓
3. fetch_updates() retrieves new items
   ↓
4. Items converted to ConnectorData format
   ↓
5. Optionally ingested as markdown files in vault
   ↓
6. Last sync timestamp saved
```

---

## Authentication Types

### API Key
```python
auth_type="api_key"

def authenticate(self, credentials):
    api_key = credentials.get('api_key')
    # Validate and store
    return True, None
```

### OAuth
```python
auth_type="oauth"

def authenticate(self, credentials):
    code = credentials.get('code')
    # Exchange code for tokens
    # Store tokens securely
    return True, None
```

### Token (e.g., Discord bot token)
```python
auth_type="token"

def authenticate(self, credentials):
    token = credentials.get('token')
    # Validate token
    return True, None
```

### None (no auth required)
```python
auth_type="none"
```

---

## Configuration Storage

Each connector gets its own config directory:
```
~/.localbrain/connectors/{connector_id}/
├── state.json          # Last sync timestamp, etc.
├── credentials.json    # Auth tokens (encrypted)
└── config.json         # User settings
```

Access via `self.config_dir` in your connector.

---

## Testing Your Connector

### 1. Auto-discovery test
```bash
cd electron/backend
python -c "from connectors.connector_manager import get_connector_manager; \
           m = get_connector_manager(); \
           print([c.name for c in m.list_connectors()])"
```

Should print your connector name!

### 2. Status check
```bash
curl http://localhost:8765/connectors/my_connector/status
```

### 3. Trigger sync
```bash
curl -X POST "http://localhost:8765/connectors/my_connector/sync?auto_ingest=false"
```

---

## Example Connectors

### Simple: Browser History
```python
def fetch_updates(self, since=None, limit=None):
    # Read Chrome history SQLite DB
    # Convert to ConnectorData
    # Return list
    pass
```

### Medium: Discord
```python
def has_updates(self, since=None):
    # Use discord.py to check DMs
    # Compare timestamps
    return bool(new_messages)

def fetch_updates(self, since=None, limit=None):
    # Fetch DM messages
    # Convert to ConnectorData with metadata
    return messages
```

### Complex: Gmail (OAuth)
```python
def authenticate(self, credentials):
    # OAuth flow
    # Exchange code for tokens
    # Store refresh token
    pass

def fetch_updates(self, since=None, limit=None):
    # Use Gmail API
    # Fetch emails with proper pagination
    # Convert HTML to markdown
    # Return as ConnectorData
    pass
```

---

## Auto-Sync

Connectors can be synced automatically:

```python
# In daemon.py startup
async def auto_sync_task():
    while True:
        manager = get_connector_manager()
        results = manager.sync_all(auto_ingest=True)
        await asyncio.sleep(600)  # Every 10 minutes
```

---

## Custom Actions

Connectors can expose custom actions:

```python
class MyConnector(BaseConnector):
    def action_send_message(self, recipient: str, message: str):
        """Custom action: send a message."""
        # Your logic here
        return {"sent": True}
```

Call it:
```bash
POST /connectors/my_connector/action/send_message
{"recipient": "user@example.com", "message": "Hello!"}
```

---

## Supported Connectors (Future)

Current state:
- ✅ Gmail (needs refactor to BaseConnector)
- ✅ Discord (needs refactor to BaseConnector)
- ⚠️ Browser History (partial)
- ⚠️ Calendar (partial)
- ⚠️ iMessage (partial)

Easy to add:
- Beeper
- Slack
- LinkedIn Messages
- Twitter/X DMs
- WhatsApp (via unofficial API)
- iMessage (via chat.db)
- Telegram
- Signal (via unofficial API)
- Browser bookmarks
- Notion
- Todoist
- Spotify history
- Fitness apps
- Smart home devices

---

## Migration Guide

### Old (Hardcoded in daemon.py)
```python
@app.post("/connectors/gmail/sync")
async def gmail_sync(max_results: int = 100):
    from connectors.gmail.gmail_connector import GmailConnector
    connector = GmailConnector()
    # ... hardcoded logic
```

### New (Plugin System)
```python
# In daemon.py startup:
from connectors.connector_api import create_connector_router
app.include_router(create_connector_router(vault_path=VAULT_PATH))

# That's it! All connectors get endpoints automatically.
```

---

## Best Practices

### Do ✅
- Implement all required methods
- Handle errors gracefully (return empty list, not crash)
- Use incremental sync (track `since` timestamp)
- Store minimal state in `state.json`
- Encrypt sensitive credentials
- Provide clear error messages
- Add docstrings and comments

### Don't ❌
- Hardcode paths or credentials
- Make blocking calls in `has_updates()`
- Return gigabytes of data at once
- Ignore rate limits
- Store passwords in plain text
- Crash on network errors

---

## Debugging

### Connector not discovered?
1. Check naming: `<name>_connector.py` in `connectors/<name>/`
2. Class must inherit from `BaseConnector`
3. Check for import errors:
   ```bash
   python -c "from connectors.<name>.<name>_connector import *"
   ```

### Sync failing?
1. Check `get_status()` - is connector authenticated?
2. Test `has_updates()` - returns bool?
3. Test `fetch_updates()` - returns list of ConnectorData?
4. Check logs in terminal

### Auth not working?
1. Verify `auth_type` in metadata
2. Implement `authenticate()` method
3. Store credentials in `self.config_dir`

---

## Summary

**The plugin system makes adding connectors trivial:**

1. Create `connectors/<name>/<name>_connector.py`
2. Inherit from `BaseConnector`
3. Implement 4 methods: `get_metadata`, `has_updates`, `fetch_updates`, `get_status`
4. Done!

No more hardcoding routes. No more mess. Just clean, discoverable plugins.

**Want to add iMessage support?** 20 lines of code.  
**Want to sync Beeper?** 30 lines of code.  
**Want to track browser history?** 15 lines of code.

The architecture handles discovery, API routes, auth, sync, and ingestion. You just write the data fetching logic.

🎉 **Clean. Simple. Extensible.**
