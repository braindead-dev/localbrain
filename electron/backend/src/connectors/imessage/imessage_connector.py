"""
iMessage Connector - Reads macOS Messages database and feeds into LocalBrain.

This connector reads the local Messages database (chat.db) on macOS and extracts
text messages for ingestion into LocalBrain.
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

from connectors.base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorStatus,
    ConnectorData,
)


class IMessageConnector(BaseConnector):
    """
    iMessage connector for reading macOS Messages database.

    Reads from ~/Library/Messages/chat.db and extracts text messages
    for ingestion into LocalBrain.
    """

    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        """
        Initialize iMessage connector.

        Args:
            vault_path: Path to LocalBrain vault for ingestion
            config_dir: Directory to store connector config (default: ~/.localbrain/connectors/imessage)
        """
        # Initialize base connector
        super().__init__(vault_path=vault_path, config_dir=config_dir)

        # Path to Messages database
        self.db_path = Path.home() / 'Library' / 'Messages' / 'chat.db'

        # State file for tracking last processed ROWID
        self.state_file = self.config_dir / 'state.json'

    # ========================================================================
    # BaseConnector Required Methods
    # ========================================================================

    def get_metadata(self) -> ConnectorMetadata:
        """Return iMessage connector metadata."""
        return ConnectorMetadata(
            id="imessage",
            name="iMessage",
            description="Sync iMessage conversations from macOS Messages",
            version="1.0.0",
            author="LocalBrain Team",
            auth_type="none",  # No authentication needed - local database
            requires_config=False,
            sync_interval_minutes=10,  # Check for new messages every 10 minutes
            capabilities=["read"]
        )

    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """
        Check if there are new messages available.

        Args:
            since: Not used - we track by ROWID instead

        Returns:
            True if new messages are available, False otherwise
        """
        if not self._is_db_accessible():
            return False

        try:
            # Get last processed ROWID
            last_rowid = self._get_last_rowid()

            # Check if there are messages with higher ROWID
            conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM message WHERE ROWID > ?",
                (last_rowid,)
            )
            count = cursor.fetchone()[0]

            conn.close()

            return count > 0

        except Exception as e:
            print(f"Error checking for iMessage updates: {e}")
            return False

    def fetch_updates(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[ConnectorData]:
        """
        Fetch new messages since last sync.

        Args:
            since: Not used - we track by ROWID instead
            limit: Maximum number of messages to fetch (default: 100)

        Returns:
            List of ConnectorData objects ready for ingestion
        """
        if not self._is_db_accessible():
            return []

        try:
            # Get last processed ROWID
            last_rowid = self._get_last_rowid()

            # Default limit
            if limit is None:
                limit = 100

            # Fetch new messages
            messages = self._fetch_messages(last_rowid, limit)

            # Convert to ConnectorData format
            connector_data = []
            max_rowid = last_rowid

            for msg in messages:
                try:
                    # Update max ROWID
                    if msg['rowid'] > max_rowid:
                        max_rowid = msg['rowid']

                    # Create ConnectorData object
                    connector_data.append(ConnectorData(
                        content=msg['content'],
                        source_id=f"imessage_{msg['rowid']}",
                        timestamp=msg['timestamp'],
                        metadata={
                            'platform': 'iMessage',
                            'type': 'message',
                            'sender': msg['sender'],
                            'chat_id': msg['chat_id'],
                            'is_from_me': msg['is_from_me'],
                            'quote': msg['content'][:100] + '...' if len(msg['content']) > 100 else msg['content']
                        }
                    ))
                except Exception as e:
                    print(f"Error processing message {msg.get('rowid')}: {e}")
                    continue

            # Update last processed ROWID
            if max_rowid > last_rowid:
                self._save_last_rowid(max_rowid)

            return connector_data

        except Exception as e:
            print(f"Error fetching iMessage updates: {e}")
            return []

    def get_status(self) -> ConnectorStatus:
        """
        Get current iMessage connector status.

        Returns:
            ConnectorStatus with connection info and statistics
        """
        try:
            # Check if database is accessible
            if not self._is_db_accessible():
                return ConnectorStatus(
                    connected=False,
                    authenticated=True,  # No auth needed
                    last_error="Messages database not accessible. This connector only works on macOS.",
                    config_valid=True
                )

            # Get last processed ROWID
            last_rowid = self._get_last_rowid()

            # Get total message count
            conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM message")
            total_messages = cursor.fetchone()[0]
            conn.close()

            return ConnectorStatus(
                connected=True,
                authenticated=True,
                last_sync=self._get_last_sync(),
                total_items_synced=last_rowid,
                config_valid=True,
                metadata={
                    'last_rowid': last_rowid,
                    'total_messages': total_messages,
                    'db_path': str(self.db_path)
                }
            )

        except Exception as e:
            return ConnectorStatus(
                connected=False,
                authenticated=True,
                last_error=str(e),
                config_valid=True
            )

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _is_db_accessible(self) -> bool:
        """Check if Messages database exists and is accessible."""
        return self.db_path.exists() and os.access(self.db_path, os.R_OK)

    def _get_last_rowid(self) -> int:
        """
        Get last processed ROWID from state file.

        Returns:
            Last processed ROWID (0 if never synced)
        """
        if not self.state_file.exists():
            return 0

        try:
            with open(self.state_file) as f:
                state = json.load(f)
                return state.get('last_rowid', 0)
        except Exception:
            return 0

    def _save_last_rowid(self, rowid: int):
        """
        Save last processed ROWID to state file.

        Args:
            rowid: ROWID to save
        """
        state = {}
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
            except Exception:
                pass

        state['last_rowid'] = rowid

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _fetch_messages(self, last_rowid: int, limit: int) -> List[Dict]:
        """
        Fetch messages from database with ROWID > last_rowid.

        Args:
            last_rowid: Only fetch messages with ROWID > this value
            limit: Maximum number of messages to fetch

        Returns:
            List of message dictionaries
        """
        messages = []

        try:
            # Connect to database in read-only mode
            conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
            cursor = conn.cursor()

            # Query messages with proper timestamp conversion
            # Apple's timestamp: seconds since 2001-01-01 00:00:00 UTC
            # SQL conversion: datetime(date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch')
            query = """
                SELECT
                    message.ROWID,
                    message.text,
                    message.is_from_me,
                    message.cache_roomnames,
                    datetime(message.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch') as timestamp,
                    COALESCE(handle.id, 'Unknown') as sender
                FROM message
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                WHERE message.ROWID > ?
                    AND message.text IS NOT NULL
                    AND message.text != ''
                ORDER BY message.ROWID ASC
                LIMIT ?
            """

            cursor.execute(query, (last_rowid, limit))
            rows = cursor.fetchall()

            for row in rows:
                rowid, text, is_from_me, chat_id, timestamp_str, sender = row

                # Parse timestamp
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    # Assume UTC
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                except Exception:
                    timestamp = datetime.now(timezone.utc)

                # Format message content
                sender_label = "Me" if is_from_me else sender
                content = f"[{timestamp_str}] {sender_label}: {text}"

                messages.append({
                    'rowid': rowid,
                    'content': content,
                    'timestamp': timestamp,
                    'sender': sender,
                    'is_from_me': bool(is_from_me),
                    'chat_id': chat_id or 'Unknown'
                })

            conn.close()

        except Exception as e:
            print(f"Error fetching messages from database: {e}")

        return messages


# ============================================================================
# Helper Function for Background Sync
# ============================================================================

def sync_imessage(vault_path: Path, limit: int = 100) -> Dict:
    """
    Helper function to sync iMessage messages and ingest them.

    Args:
        vault_path: Path to LocalBrain vault
        limit: Maximum number of messages to fetch

    Returns:
        Dict with sync results
    """
    connector = IMessageConnector(vault_path=vault_path)

    if not connector._is_db_accessible():
        return {
            'success': False,
            'error': 'Messages database not accessible. This connector only works on macOS.'
        }

    # Use the built-in sync method
    result = connector.sync(auto_ingest=False, limit=limit)

    return {
        'success': result.success,
        'items_fetched': result.items_fetched,
        'items_ingested': result.items_ingested,
        'errors': result.errors
    }
