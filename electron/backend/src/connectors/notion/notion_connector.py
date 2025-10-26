"""
Notion Connector - Syncs Notion pages and databases via OAuth.

This connector authenticates with Notion using OAuth 2.0 and fetches
pages and databases for ingestion into LocalBrain.
"""

import os
import json
import base64
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from connectors.base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorStatus,
    ConnectorData,
    SyncResult
)


# OAuth 2.0 URLs
AUTHORIZATION_URL = 'https://api.notion.com/v1/oauth/authorize'
TOKEN_URL = 'https://api.notion.com/v1/oauth/token'
REDIRECT_URI = 'http://localhost:8765/connectors/notion/auth/callback'

# Notion API configuration
NOTION_API_VERSION = '2022-06-28'
NOTION_API_BASE = 'https://api.notion.com/v1'


class NotionConnector(BaseConnector):
    """
    Notion connector for syncing pages and databases.

    Handles OAuth flow, token management, and content retrieval from Notion.
    """

    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        """
        Initialize Notion connector.

        Args:
            vault_path: Path to LocalBrain vault for ingestion
            config_dir: Directory to store connector config (default: ~/.localbrain/connectors/notion)
        """
        # Initialize base connector
        super().__init__(vault_path=vault_path, config_dir=config_dir)

        # Set up credentials directory
        self.credentials_dir = Path.home() / '.localbrain' / 'credentials'
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.token_file = self.credentials_dir / 'notion_token.json'
        self.notion_config_file = self.credentials_dir / 'notion_config.json'

    # ========================================================================
    # BaseConnector Required Methods
    # ========================================================================

    def get_metadata(self) -> ConnectorMetadata:
        """Return Notion connector metadata."""
        return ConnectorMetadata(
            id="notion",
            name="Notion",
            description="Sync Notion pages and databases",
            version="1.0.0",
            author="LocalBrain Team",
            auth_type="oauth",
            requires_config=True,
            sync_interval_minutes=30,  # Check for updates every 30 minutes
            capabilities=["read"]
        )

    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """Check if there are updated pages/databases available."""
        if not self.is_authenticated():
            return False

        try:
            # Search for recently edited pages
            if since:
                # Notion doesn't support filtering by last_edited_time in search
                # So we'll fetch a few items and check manually
                results = self._search_content(limit=10)

                for item in results:
                    last_edited = item.get('last_edited_time')
                    if last_edited:
                        edited_dt = datetime.fromisoformat(last_edited.replace('Z', '+00:00'))
                        if edited_dt > since:
                            return True
                return False
            else:
                # Check if any content exists
                results = self._search_content(limit=1)
                return len(results) > 0

        except Exception as e:
            print(f"Error checking for Notion updates: {e}")
            return False

    def fetch_updates(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[ConnectorData]:
        """Fetch updated pages/databases since last sync."""
        if not self.is_authenticated():
            return []

        try:
            # Fetch all accessible content
            results = self._search_content(limit=limit or 100)

            # Convert to ConnectorData format
            connector_data = []

            for item in results:
                try:
                    # Filter by last_edited_time if since is provided
                    last_edited = item.get('last_edited_time')
                    if since and last_edited:
                        edited_dt = datetime.fromisoformat(last_edited.replace('Z', '+00:00'))
                        if edited_dt <= since:
                            continue

                    # Get page/database content
                    content_data = self._item_to_text(item)

                    if content_data:
                        connector_data.append(ConnectorData(
                            content=content_data['text'],
                            source_id=item['id'],
                            timestamp=datetime.fromisoformat(last_edited.replace('Z', '+00:00')) if last_edited else datetime.now(timezone.utc),
                            metadata=content_data['metadata']
                        ))

                except Exception as e:
                    print(f"Error processing Notion item {item.get('id')}: {e}")
                    continue

            return connector_data

        except Exception as e:
            print(f"Error fetching Notion updates: {e}")
            return []

    def get_status(self) -> ConnectorStatus:
        """Get current Notion connector status."""
        try:
            if not self.is_authenticated():
                return ConnectorStatus(
                    connected=False,
                    authenticated=False,
                    last_error="Not authenticated",
                    config_valid=True
                )

            # Get workspace info
            config = self._load_config()

            return ConnectorStatus(
                connected=True,
                authenticated=True,
                last_sync=self._get_last_sync(),
                total_items_synced=config.get('total_items_synced', 0),
                config_valid=True,
                metadata={
                    'workspace_name': config.get('workspace_name'),
                    'workspace_id': config.get('workspace_id'),
                    'owner': config.get('owner'),
                    'connected_at': config.get('connected_at')
                }
            )

        except Exception as e:
            return ConnectorStatus(
                connected=False,
                authenticated=False,
                last_error=str(e),
                config_valid=True
            )

    def authenticate(self, credentials: Dict) -> Tuple[bool, Optional[str]]:
        """Handle OAuth authentication."""
        try:
            if 'authorization_response' in credentials:
                # Handle OAuth callback
                self.handle_callback(credentials['authorization_response'])
                return True, None
            else:
                return False, "Invalid credentials format"
        except Exception as e:
            return False, str(e)

    def revoke_access(self) -> bool:
        """Revoke Notion access."""
        try:
            # Delete local token file
            if self.token_file.exists():
                self.token_file.unlink()

            # Reset config
            config = self._load_config()
            config['workspace_name'] = None
            config['workspace_id'] = None
            config['owner'] = None
            config['connected_at'] = None
            self._save_config(config)

            return True
        except Exception:
            return False

    # ========================================================================
    # Authentication Methods
    # ========================================================================

    def start_auth_flow(self) -> str:
        """
        Start OAuth 2.0 flow.

        Returns:
            Authorization URL for user to visit

        Raises:
            ValueError: If required environment variables are not set
        """
        client_id = self._get_client_id()

        # Build authorization URL
        auth_url = (
            f"{AUTHORIZATION_URL}"
            f"?client_id={client_id}"
            f"&response_type=code"
            f"&owner=user"
            f"&redirect_uri={REDIRECT_URI}"
        )

        return auth_url

    def handle_callback(self, authorization_response: str) -> Dict:
        """
        Handle OAuth callback and save tokens.

        Args:
            authorization_response: Full callback URL with authorization code

        Returns:
            User info dict with workspace info
        """
        # Extract authorization code from URL
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(authorization_response)
        params = parse_qs(parsed.query)
        code = params.get('code', [None])[0]

        if not code:
            raise ValueError("No authorization code in callback")

        # Exchange code for token
        client_id = self._get_client_id()
        client_secret = self._get_client_secret()

        # Notion requires Basic Auth with base64 encoded client_id:client_secret
        auth_string = f"{client_id}:{client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_base64 = base64.b64encode(auth_bytes).decode('ascii')

        response = requests.post(
            TOKEN_URL,
            headers={
                'Authorization': f'Basic {auth_base64}',
                'Content-Type': 'application/json'
            },
            json={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': REDIRECT_URI
            }
        )

        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.text}")

        token_data = response.json()

        # Save token
        self._save_token(token_data)

        # Extract workspace info
        workspace_name = token_data.get('workspace_name', 'Unknown')
        workspace_id = token_data.get('workspace_id', 'Unknown')
        owner = token_data.get('owner', {}).get('user', {}).get('name', 'Unknown')

        # Update config
        config = self._load_config()
        config['workspace_name'] = workspace_name
        config['workspace_id'] = workspace_id
        config['owner'] = owner
        config['connected_at'] = datetime.now().isoformat()
        self._save_config(config)

        return {
            'workspace_name': workspace_name,
            'workspace_id': workspace_id,
            'owner': owner,
            'connected': True
        }

    def is_authenticated(self) -> bool:
        """Check if user has valid authentication."""
        return self.token_file.exists()

    def get_access_token(self) -> Optional[str]:
        """Get stored access token."""
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file) as f:
                token_data = json.load(f)
                return token_data.get('access_token')
        except Exception:
            return None

    # ========================================================================
    # Notion API Methods
    # ========================================================================

    def _search_content(self, limit: int = 100) -> List[Dict]:
        """
        Search for all accessible pages and databases.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List of page/database objects
        """
        access_token = self.get_access_token()
        if not access_token:
            return []

        results = []
        has_more = True
        next_cursor = None

        while has_more and len(results) < limit:
            payload = {
                'page_size': min(100, limit - len(results))
            }

            if next_cursor:
                payload['start_cursor'] = next_cursor

            response = requests.post(
                f'{NOTION_API_BASE}/search',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Notion-Version': NOTION_API_VERSION,
                    'Content-Type': 'application/json'
                },
                json=payload
            )

            if response.status_code != 200:
                print(f"Search failed: {response.text}")
                break

            data = response.json()
            results.extend(data.get('results', []))

            has_more = data.get('has_more', False)
            next_cursor = data.get('next_cursor')

        return results

    def _get_page_content(self, page_id: str) -> str:
        """
        Fetch page content (blocks).

        Args:
            page_id: Notion page ID

        Returns:
            Text content of the page
        """
        access_token = self.get_access_token()
        if not access_token:
            return ""

        # Fetch blocks
        response = requests.get(
            f'{NOTION_API_BASE}/blocks/{page_id}/children',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Notion-Version': NOTION_API_VERSION
            }
        )

        if response.status_code != 200:
            return ""

        data = response.json()
        blocks = data.get('results', [])

        # Extract text from blocks
        text_parts = []
        for block in blocks:
            text = self._extract_block_text(block)
            if text:
                text_parts.append(text)

        return '\n\n'.join(text_parts)

    def _extract_block_text(self, block: Dict) -> str:
        """Extract text from a Notion block."""
        block_type = block.get('type')

        if not block_type:
            return ""

        content = block.get(block_type, {})

        # Handle rich text
        if 'rich_text' in content:
            return ''.join([rt.get('plain_text', '') for rt in content['rich_text']])

        # Handle other text fields
        if 'text' in content:
            return content['text']

        return ""

    def _item_to_text(self, item: Dict) -> Optional[Dict]:
        """
        Convert Notion page/database to text format.

        Args:
            item: Notion page or database object

        Returns:
            Dict with text content and metadata
        """
        item_type = item.get('object')
        item_id = item.get('id')

        # Get title
        title = self._extract_title(item)

        # Get URL
        url = item.get('url', f'https://notion.so/{item_id}')

        # Get timestamps
        created_time = item.get('created_time', '')
        last_edited_time = item.get('last_edited_time', '')

        # For pages, fetch content
        content = ""
        if item_type == 'page':
            content = self._get_page_content(item_id)

        # Format as text
        text_content = f"""Notion {item_type.capitalize()}: {title}
Created: {created_time}
Last Edited: {last_edited_time}

{content}

---
Notion URL: {url}
"""

        return {
            'text': text_content,
            'metadata': {
                'platform': 'Notion',
                'type': item_type,
                'title': title,
                'url': url,
                'timestamp': last_edited_time,
                'quote': title,
                'created_time': created_time,
                'last_edited_time': last_edited_time
            }
        }

    def _extract_title(self, item: Dict) -> str:
        """Extract title from Notion page/database."""
        # Try to get title from properties
        properties = item.get('properties', {})

        # Look for title property
        for prop_name, prop_value in properties.items():
            if prop_value.get('type') == 'title':
                title_array = prop_value.get('title', [])
                if title_array:
                    return ''.join([t.get('plain_text', '') for t in title_array])

        # Fallback to object type
        return f"Untitled {item.get('object', 'item')}"

    # ========================================================================
    # Config/Token Management
    # ========================================================================

    def _save_token(self, token_data: Dict):
        """Save OAuth token to file."""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)

    def _load_config(self) -> Dict:
        """Load connector configuration."""
        if self.notion_config_file.exists():
            with open(self.notion_config_file) as f:
                return json.load(f)
        return {}

    def _save_config(self, config: Dict):
        """Save connector configuration."""
        self.notion_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.notion_config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def _get_client_id(self) -> str:
        """Get Notion OAuth client ID from environment."""
        client_id = os.getenv('NOTION_CLIENT_ID')
        if not client_id:
            raise ValueError(
                "NOTION_CLIENT_ID environment variable not set.\n"
                "Please set it with your Notion OAuth client ID."
            )
        return client_id

    def _get_client_secret(self) -> str:
        """Get Notion OAuth client secret from environment."""
        client_secret = os.getenv('NOTION_CLIENT_SECRET')
        if not client_secret:
            raise ValueError(
                "NOTION_CLIENT_SECRET environment variable not set.\n"
                "Please set it with your Notion OAuth client secret."
            )
        return client_secret


# ============================================================================
# Helper Function for Background Sync
# ============================================================================

def sync_notion(vault_path: Path, limit: int = 100) -> Dict:
    """
    Helper function to sync Notion pages/databases and ingest them.

    Args:
        vault_path: Path to LocalBrain vault
        limit: Maximum number of items to fetch

    Returns:
        Dict with sync results
    """
    connector = NotionConnector(vault_path=vault_path)

    if not connector.is_authenticated():
        return {
            'success': False,
            'error': 'Notion not authenticated'
        }

    # Use the built-in sync method
    result = connector.sync(auto_ingest=False, limit=limit)

    return {
        'success': result.success,
        'items_fetched': result.items_fetched,
        'items_ingested': result.items_ingested,
        'errors': result.errors
    }
