"""
Reddit Connector - Syncs Reddit posts and comments via OAuth 2.0.

This connector authenticates with Reddit API using OAuth 2.0 and fetches
posts, comments, and saved items for ingestion into LocalBrain.
"""

import os
import json
import base64
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
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


# Reddit OAuth 2.0 URLs
AUTHORIZATION_URL = 'https://www.reddit.com/api/v1/authorize'
TOKEN_URL = 'https://www.reddit.com/api/v1/access_token'
REDIRECT_URI = 'http://localhost:8765/connectors/reddit/auth/callback'

# Reddit API configuration
REDDIT_API_BASE = 'https://oauth.reddit.com'

# Scopes required for reading posts and comments
SCOPES = [
    'identity',  # Access user identity
    'read',  # Read posts and comments
    'history',  # Access user history
    'save'  # Access saved items
]


class RedditConnector(BaseConnector):
    """
    Reddit connector for syncing posts, comments, and saved items.

    Handles OAuth flow, token management, and content retrieval from Reddit.
    """

    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        """
        Initialize Reddit connector.

        Args:
            vault_path: Path to LocalBrain vault for ingestion
            config_dir: Directory to store connector config (default: ~/.localbrain/connectors/reddit)
        """
        # Initialize base connector
        super().__init__(vault_path=vault_path, config_dir=config_dir)

        # Set up credentials directory
        self.credentials_dir = Path.home() / '.localbrain' / 'credentials'
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.token_file = self.credentials_dir / 'reddit_token.json'
        self.config_file = self.credentials_dir / 'reddit_config.json'

    # ========================================================================
    # BaseConnector Required Methods
    # ========================================================================

    def get_metadata(self) -> ConnectorMetadata:
        """Return Reddit connector metadata."""
        return ConnectorMetadata(
            id="reddit",
            name="Reddit",
            description="Sync Reddit posts, comments, and saved items",
            version="1.0.0",
            author="LocalBrain Team",
            auth_type="oauth",
            requires_config=True,
            sync_interval_minutes=30,  # Check for updates every 30 minutes
            capabilities=["read"]
        )

    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """Check if there are new posts/comments available."""
        if not self.is_authenticated():
            return False

        try:
            access_token = self.get_access_token()
            if not access_token:
                return False

            # Check for recent posts
            response = requests.get(
                f'{REDDIT_API_BASE}/user/{self._get_username()}/submitted',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'User-Agent': 'LocalBrain/1.0'
                },
                params={'limit': 1}
            )

            if response.status_code != 200:
                return False

            data = response.json()
            items = data.get('data', {}).get('children', [])

            if not items:
                return False

            if since:
                item_time = datetime.fromtimestamp(items[0]['data']['created_utc'], tz=timezone.utc)
                return item_time > since

            return True

        except Exception as e:
            print(f"Error checking for Reddit updates: {e}")
            return False

    def fetch_updates(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[ConnectorData]:
        """Fetch Reddit posts and comments since last sync."""
        if not self.is_authenticated():
            return []

        try:
            access_token = self.get_access_token()
            if not access_token:
                return []

            # Fetch both posts and comments
            posts = self._fetch_user_posts(access_token, limit or 50)
            comments = self._fetch_user_comments(access_token, limit or 50)

            # Combine and convert to ConnectorData format
            connector_data = []

            # Process posts
            for post in posts:
                try:
                    created_utc = post['data'].get('created_utc')
                    if since and created_utc:
                        post_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                        if post_time <= since:
                            continue

                    post_data = self._post_to_text(post['data'])
                    timestamp = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else datetime.now(timezone.utc)

                    connector_data.append(ConnectorData(
                        content=post_data['text'],
                        source_id=post['data']['id'],
                        timestamp=timestamp,
                        metadata=post_data['metadata']
                    ))

                except Exception as e:
                    print(f"Error processing Reddit post: {e}")
                    continue

            # Process comments
            for comment in comments:
                try:
                    created_utc = comment['data'].get('created_utc')
                    if since and created_utc:
                        comment_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                        if comment_time <= since:
                            continue

                    comment_data = self._comment_to_text(comment['data'])
                    timestamp = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else datetime.now(timezone.utc)

                    connector_data.append(ConnectorData(
                        content=comment_data['text'],
                        source_id=comment['data']['id'],
                        timestamp=timestamp,
                        metadata=comment_data['metadata']
                    ))

                except Exception as e:
                    print(f"Error processing Reddit comment: {e}")
                    continue

            # Sort by timestamp (most recent first)
            connector_data.sort(key=lambda x: x.timestamp, reverse=True)

            return connector_data

        except Exception as e:
            print(f"Error fetching Reddit updates: {e}")
            return []

    def get_status(self) -> ConnectorStatus:
        """Get current Reddit connector status."""
        try:
            if not self.is_authenticated():
                return ConnectorStatus(
                    connected=False,
                    authenticated=False,
                    last_error="Not authenticated",
                    config_valid=True
                )

            # Get user info
            config = self._load_config()

            return ConnectorStatus(
                connected=True,
                authenticated=True,
                last_sync=self._get_last_sync(),
                total_items_synced=config.get('total_items_synced', 0),
                config_valid=True,
                metadata={
                    'username': config.get('username'),
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
        """Revoke Reddit access."""
        try:
            # Delete local token file
            if self.token_file.exists():
                self.token_file.unlink()

            # Reset config
            config = self._load_config()
            config['username'] = None
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

        # Generate random state for CSRF protection
        import secrets
        state = secrets.token_urlsafe(16)
        self._save_state(state)

        # Build authorization URL
        scope_string = ' '.join(SCOPES)
        auth_url = (
            f"{AUTHORIZATION_URL}"
            f"?client_id={client_id}"
            f"&response_type=code"
            f"&state={state}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&duration=permanent"  # Request permanent access (refresh token)
            f"&scope={scope_string}"
        )

        return auth_url

    def handle_callback(self, authorization_response: str) -> Dict:
        """
        Handle OAuth callback and save tokens.

        Args:
            authorization_response: Full callback URL with authorization code

        Returns:
            User info dict
        """
        # Extract authorization code from URL
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(authorization_response)
        params = parse_qs(parsed.query)
        code = params.get('code', [None])[0]
        state = params.get('state', [None])[0]

        if not code:
            raise ValueError("No authorization code in callback")

        # Verify state
        saved_state = self._load_state()
        if state != saved_state:
            raise ValueError("State mismatch - possible CSRF attack")

        # Exchange code for token
        client_id = self._get_client_id()
        client_secret = self._get_client_secret()

        # Reddit requires Basic Auth
        auth_string = f"{client_id}:{client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_base64 = base64.b64encode(auth_bytes).decode('ascii')

        response = requests.post(
            TOKEN_URL,
            headers={
                'Authorization': f'Basic {auth_base64}',
                'User-Agent': 'LocalBrain/1.0'
            },
            data={
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

        # Get user info
        access_token = token_data.get('access_token')
        user_info = self._get_user_info(access_token)

        # Update config
        config = self._load_config()
        config['username'] = user_info.get('name')
        config['connected_at'] = datetime.now().isoformat()
        self._save_config(config)

        return {
            'username': config['username'],
            'connected': True
        }

    def is_authenticated(self) -> bool:
        """Check if user has valid authentication."""
        if not self.token_file.exists():
            return False

        try:
            token_data = self._load_token()
            if not token_data:
                return False

            # Check if access token exists
            if 'access_token' not in token_data:
                return False

            return True

        except Exception:
            return False

    def get_access_token(self) -> Optional[str]:
        """Get valid access token, refreshing if necessary."""
        token_data = self._load_token()
        if not token_data:
            return None

        # Check if token needs refresh
        expires_at = token_data.get('expires_at')
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at)
            if datetime.now(timezone.utc) >= expires_dt:
                # Token expired, refresh it
                token_data = self._refresh_token(token_data)
                if not token_data:
                    return None

        return token_data.get('access_token')

    def _refresh_token(self, token_data: Dict) -> Optional[Dict]:
        """Refresh access token using refresh token."""
        refresh_token = token_data.get('refresh_token')
        if not refresh_token:
            return None

        try:
            client_id = self._get_client_id()
            client_secret = self._get_client_secret()

            # Reddit requires Basic Auth
            auth_string = f"{client_id}:{client_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_base64 = base64.b64encode(auth_bytes).decode('ascii')

            response = requests.post(
                TOKEN_URL,
                headers={
                    'Authorization': f'Basic {auth_base64}',
                    'User-Agent': 'LocalBrain/1.0'
                },
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token
                }
            )

            if response.status_code != 200:
                print(f"Token refresh failed: {response.text}")
                return None

            new_token_data = response.json()

            # Save new token
            self._save_token(new_token_data)

            return new_token_data

        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None

    # ========================================================================
    # Reddit API Methods
    # ========================================================================

    def _get_user_info(self, access_token: str) -> Dict:
        """Get user profile information."""
        response = requests.get(
            f'{REDDIT_API_BASE}/api/v1/me',
            headers={
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'LocalBrain/1.0'
            }
        )

        if response.status_code != 200:
            return {}

        return response.json()

    def _get_username(self) -> str:
        """Get stored username."""
        config = self._load_config()
        return config.get('username', 'unknown')

    def _fetch_user_posts(self, access_token: str, limit: int) -> List[Dict]:
        """Fetch user's submitted posts."""
        username = self._get_username()

        response = requests.get(
            f'{REDDIT_API_BASE}/user/{username}/submitted',
            headers={
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'LocalBrain/1.0'
            },
            params={'limit': min(100, limit)}
        )

        if response.status_code != 200:
            print(f"Error fetching posts: {response.text}")
            return []

        data = response.json()
        return data.get('data', {}).get('children', [])

    def _fetch_user_comments(self, access_token: str, limit: int) -> List[Dict]:
        """Fetch user's comments."""
        username = self._get_username()

        response = requests.get(
            f'{REDDIT_API_BASE}/user/{username}/comments',
            headers={
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'LocalBrain/1.0'
            },
            params={'limit': min(100, limit)}
        )

        if response.status_code != 200:
            print(f"Error fetching comments: {response.text}")
            return []

        data = response.json()
        return data.get('data', {}).get('children', [])

    def _post_to_text(self, post: Dict) -> Dict:
        """Convert Reddit post to text format."""
        title = post.get('title', '(No Title)')
        selftext = post.get('selftext', '')
        subreddit = post.get('subreddit', 'unknown')
        author = post.get('author', 'unknown')
        score = post.get('score', 0)
        num_comments = post.get('num_comments', 0)
        url = post.get('url', '')
        permalink = f"https://reddit.com{post.get('permalink', '')}"
        created_utc = post.get('created_utc')

        created_str = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat() if created_utc else 'Unknown'

        text_content = f"""Reddit Post in r/{subreddit}
Title: {title}
Author: u/{author}
Date: {created_str}
Score: {score} | Comments: {num_comments}

{selftext}

URL: {url}
Permalink: {permalink}
"""

        return {
            'text': text_content,
            'metadata': {
                'platform': 'Reddit',
                'type': 'post',
                'title': title,
                'subreddit': subreddit,
                'author': author,
                'score': score,
                'num_comments': num_comments,
                'timestamp': created_str,
                'quote': title,
                'url': permalink
            }
        }

    def _comment_to_text(self, comment: Dict) -> Dict:
        """Convert Reddit comment to text format."""
        body = comment.get('body', '')
        subreddit = comment.get('subreddit', 'unknown')
        author = comment.get('author', 'unknown')
        score = comment.get('score', 0)
        link_title = comment.get('link_title', 'Unknown post')
        permalink = f"https://reddit.com{comment.get('permalink', '')}"
        created_utc = comment.get('created_utc')

        created_str = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat() if created_utc else 'Unknown'

        text_content = f"""Reddit Comment in r/{subreddit}
Post: {link_title}
Author: u/{author}
Date: {created_str}
Score: {score}

{body}

Permalink: {permalink}
"""

        return {
            'text': text_content,
            'metadata': {
                'platform': 'Reddit',
                'type': 'comment',
                'subreddit': subreddit,
                'author': author,
                'score': score,
                'link_title': link_title,
                'timestamp': created_str,
                'quote': body[:100] + '...' if len(body) > 100 else body,
                'url': permalink
            }
        }

    # ========================================================================
    # Config/Token Management
    # ========================================================================

    def _save_token(self, token_data: Dict):
        """Save OAuth token to file with expiration time."""
        # Calculate expiration time
        if 'expires_in' in token_data:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data['expires_in'])
            token_data['expires_at'] = expires_at.isoformat()

        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)

    def _load_token(self) -> Optional[Dict]:
        """Load OAuth token from file."""
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file) as f:
                return json.load(f)
        except Exception:
            return None

    def _save_state(self, state: str):
        """Save OAuth state for CSRF protection."""
        state_file = self.credentials_dir / 'reddit_state.json'
        with open(state_file, 'w') as f:
            json.dump({'state': state}, f)

    def _load_state(self) -> Optional[str]:
        """Load and delete OAuth state."""
        state_file = self.credentials_dir / 'reddit_state.json'
        if not state_file.exists():
            return None

        try:
            with open(state_file) as f:
                data = json.load(f)
                state = data.get('state')

            # Delete the file after reading
            state_file.unlink()

            return state
        except Exception:
            return None

    def _load_config(self) -> Dict:
        """Load connector configuration."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {}

    def _save_config(self, config: Dict):
        """Save connector configuration."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def _get_client_id(self) -> str:
        """Get Reddit OAuth client ID from environment."""
        client_id = os.getenv('REDDIT_CLIENT_ID')
        if not client_id:
            raise ValueError(
                "REDDIT_CLIENT_ID environment variable not set.\n"
                "Please set it with your Reddit OAuth app client ID."
            )
        return client_id

    def _get_client_secret(self) -> str:
        """Get Reddit OAuth client secret from environment."""
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        if not client_secret:
            raise ValueError(
                "REDDIT_CLIENT_SECRET environment variable not set.\n"
                "Please set it with your Reddit OAuth app client secret."
            )
        return client_secret


# ============================================================================
# Helper Function for Background Sync
# ============================================================================

def sync_reddit(vault_path: Path, limit: int = 100) -> Dict:
    """
    Helper function to sync Reddit posts/comments and ingest them.

    Args:
        vault_path: Path to LocalBrain vault
        limit: Maximum number of items to fetch

    Returns:
        Dict with sync results
    """
    connector = RedditConnector(vault_path=vault_path)

    if not connector.is_authenticated():
        return {
            'success': False,
            'error': 'Reddit not authenticated'
        }

    # Use the built-in sync method
    result = connector.sync(auto_ingest=False, limit=limit)

    return {
        'success': result.success,
        'items_fetched': result.items_fetched,
        'items_ingested': result.items_ingested,
        'errors': result.errors
    }
