"""
Twitter/X Connector - Syncs tweets via OAuth 2.0.

This connector authenticates with Twitter/X API v2 using OAuth 2.0 and fetches
tweets from user's timeline for ingestion into LocalBrain.
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


# Twitter OAuth 2.0 URLs
AUTHORIZATION_URL = 'https://twitter.com/i/oauth2/authorize'
TOKEN_URL = 'https://api.twitter.com/2/oauth2/token'
REDIRECT_URI = 'http://localhost:8765/connectors/twitter/auth/callback'

# Twitter API v2 configuration
TWITTER_API_BASE = 'https://api.twitter.com/2'

# Scopes required for reading tweets
SCOPES = [
    'tweet.read',
    'users.read',
    'offline.access'  # For refresh token
]


class TwitterConnector(BaseConnector):
    """
    Twitter/X connector for syncing tweets and timeline.

    Handles OAuth 2.0 PKCE flow, token management, and tweet retrieval from Twitter API v2.
    """

    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        """
        Initialize Twitter connector.

        Args:
            vault_path: Path to LocalBrain vault for ingestion
            config_dir: Directory to store connector config (default: ~/.localbrain/connectors/twitter)
        """
        # Initialize base connector
        super().__init__(vault_path=vault_path, config_dir=config_dir)

        # Set up credentials directory
        self.credentials_dir = Path.home() / '.localbrain' / 'credentials'
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.token_file = self.credentials_dir / 'twitter_token.json'
        self.config_file = self.credentials_dir / 'twitter_config.json'

    # ========================================================================
    # BaseConnector Required Methods
    # ========================================================================

    def get_metadata(self) -> ConnectorMetadata:
        """Return Twitter connector metadata."""
        return ConnectorMetadata(
            id="twitter",
            name="Twitter/X",
            description="Sync tweets and timeline from Twitter/X",
            version="1.0.0",
            author="LocalBrain Team",
            auth_type="oauth",
            requires_config=True,
            sync_interval_minutes=15,  # Check for new tweets every 15 minutes
            capabilities=["read"]
        )

    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """Check if there are new tweets available."""
        if not self.is_authenticated():
            return False

        try:
            access_token = self.get_access_token()
            if not access_token:
                return False

            # Get user ID
            user_id = self._get_user_id()
            if not user_id:
                return False

            # Fetch one tweet to check
            response = requests.get(
                f'{TWITTER_API_BASE}/users/{user_id}/tweets',
                headers={
                    'Authorization': f'Bearer {access_token}'
                },
                params={
                    'max_results': 5
                }
            )

            if response.status_code != 200:
                return False

            data = response.json()
            tweets = data.get('data', [])

            if not tweets:
                return False

            # Twitter API v2 doesn't return created_at by default, need to request it
            return True

        except Exception as e:
            print(f"Error checking for Twitter updates: {e}")
            return False

    def fetch_updates(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[ConnectorData]:
        """Fetch tweets since last sync."""
        if not self.is_authenticated():
            return []

        try:
            access_token = self.get_access_token()
            if not access_token:
                return []

            # Fetch tweets
            tweets = self._fetch_tweets(access_token, limit or 100)

            # Convert to ConnectorData format
            connector_data = []

            for tweet in tweets:
                try:
                    created_at = tweet.get('created_at')
                    if since and created_at:
                        tweet_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if tweet_time <= since:
                            continue

                    tweet_data = self._tweet_to_text(tweet)
                    timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if created_at else datetime.now(timezone.utc)

                    connector_data.append(ConnectorData(
                        content=tweet_data['text'],
                        source_id=tweet['id'],
                        timestamp=timestamp,
                        metadata=tweet_data['metadata']
                    ))

                except Exception as e:
                    print(f"Error processing tweet {tweet.get('id')}: {e}")
                    continue

            return connector_data

        except Exception as e:
            print(f"Error fetching Twitter updates: {e}")
            return []

    def get_status(self) -> ConnectorStatus:
        """Get current Twitter connector status."""
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
                total_items_synced=config.get('total_tweets_synced', 0),
                config_valid=True,
                metadata={
                    'username': config.get('username'),
                    'name': config.get('name'),
                    'user_id': config.get('user_id'),
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
        """Revoke Twitter access."""
        try:
            # Delete local token file
            if self.token_file.exists():
                self.token_file.unlink()

            # Reset config
            config = self._load_config()
            config['username'] = None
            config['name'] = None
            config['user_id'] = None
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
        Start OAuth 2.0 flow with PKCE.

        Returns:
            Authorization URL for user to visit

        Raises:
            ValueError: If required environment variables are not set
        """
        client_id = self._get_client_id()

        # Generate PKCE code verifier and challenge
        import secrets
        import hashlib

        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')

        # Save code verifier for callback
        self._save_pkce_verifier(code_verifier)

        # Build authorization URL
        scope_string = ' '.join(SCOPES)
        auth_url = (
            f"{AUTHORIZATION_URL}"
            f"?client_id={client_id}"
            f"&response_type=code"
            f"&redirect_uri={REDIRECT_URI}"
            f"&scope={scope_string}"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
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

        if not code:
            raise ValueError("No authorization code in callback")

        # Get PKCE code verifier
        code_verifier = self._load_pkce_verifier()
        if not code_verifier:
            raise ValueError("PKCE code verifier not found")

        # Exchange code for token
        client_id = self._get_client_id()

        response = requests.post(
            TOKEN_URL,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'client_id': client_id,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': REDIRECT_URI,
                'code_verifier': code_verifier
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
        config['user_id'] = user_info.get('id')
        config['username'] = user_info.get('username')
        config['name'] = user_info.get('name')
        config['connected_at'] = datetime.now().isoformat()
        self._save_config(config)

        return {
            'username': config['username'],
            'name': config['name'],
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

            response = requests.post(
                TOKEN_URL,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data={
                    'client_id': client_id,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token'
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
    # Twitter API Methods
    # ========================================================================

    def _get_user_info(self, access_token: str) -> Dict:
        """Get user profile information."""
        response = requests.get(
            f'{TWITTER_API_BASE}/users/me',
            headers={
                'Authorization': f'Bearer {access_token}'
            }
        )

        if response.status_code != 200:
            return {}

        data = response.json()
        return data.get('data', {})

    def _get_user_id(self) -> Optional[str]:
        """Get stored user ID."""
        config = self._load_config()
        return config.get('user_id')

    def _fetch_tweets(self, access_token: str, limit: int) -> List[Dict]:
        """
        Fetch user tweets from Twitter API v2.

        Args:
            access_token: Valid access token
            limit: Maximum number of tweets to fetch

        Returns:
            List of tweet objects
        """
        user_id = self._get_user_id()
        if not user_id:
            return []

        tweets = []
        pagination_token = None

        while len(tweets) < limit:
            params = {
                'max_results': min(100, limit - len(tweets)),
                'tweet.fields': 'created_at,public_metrics,referenced_tweets'
            }

            if pagination_token:
                params['pagination_token'] = pagination_token

            response = requests.get(
                f'{TWITTER_API_BASE}/users/{user_id}/tweets',
                headers={
                    'Authorization': f'Bearer {access_token}'
                },
                params=params
            )

            if response.status_code != 200:
                print(f"Error fetching tweets: {response.text}")
                break

            data = response.json()
            page_tweets = data.get('data', [])

            if not page_tweets:
                break

            tweets.extend(page_tweets)

            # Check for pagination
            meta = data.get('meta', {})
            pagination_token = meta.get('next_token')

            if not pagination_token:
                break

        return tweets[:limit]

    def _tweet_to_text(self, tweet: Dict) -> Dict:
        """
        Convert Twitter tweet to text format.

        Args:
            tweet: Twitter API v2 tweet object

        Returns:
            Dict with text content and metadata
        """
        tweet_id = tweet.get('id')
        text = tweet.get('text', '')
        created_at = tweet.get('created_at', '')
        public_metrics = tweet.get('public_metrics', {})

        username = self._load_config().get('username', 'unknown')

        # Format as text
        text_content = f"""Tweet from @{username}
Date: {created_at}

{text}

Likes: {public_metrics.get('like_count', 0)}
Retweets: {public_metrics.get('retweet_count', 0)}
Replies: {public_metrics.get('reply_count', 0)}

URL: https://twitter.com/{username}/status/{tweet_id}
"""

        return {
            'text': text_content,
            'metadata': {
                'platform': 'Twitter',
                'type': 'tweet',
                'tweet_id': tweet_id,
                'author': username,
                'timestamp': created_at,
                'quote': text[:100] + '...' if len(text) > 100 else text,
                'likes': public_metrics.get('like_count', 0),
                'retweets': public_metrics.get('retweet_count', 0)
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

    def _save_pkce_verifier(self, verifier: str):
        """Save PKCE code verifier temporarily."""
        pkce_file = self.credentials_dir / 'twitter_pkce.json'
        with open(pkce_file, 'w') as f:
            json.dump({'code_verifier': verifier}, f)

    def _load_pkce_verifier(self) -> Optional[str]:
        """Load and delete PKCE code verifier."""
        pkce_file = self.credentials_dir / 'twitter_pkce.json'
        if not pkce_file.exists():
            return None

        try:
            with open(pkce_file) as f:
                data = json.load(f)
                verifier = data.get('code_verifier')

            # Delete the file after reading
            pkce_file.unlink()

            return verifier
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
        """Get Twitter OAuth client ID from environment."""
        client_id = os.getenv('TWITTER_CLIENT_ID')
        if not client_id:
            raise ValueError(
                "TWITTER_CLIENT_ID environment variable not set.\n"
                "Please set it with your Twitter/X OAuth 2.0 client ID."
            )
        return client_id


# ============================================================================
# Helper Function for Background Sync
# ============================================================================

def sync_twitter(vault_path: Path, limit: int = 100) -> Dict:
    """
    Helper function to sync Twitter tweets and ingest them.

    Args:
        vault_path: Path to LocalBrain vault
        limit: Maximum number of tweets to fetch

    Returns:
        Dict with sync results
    """
    connector = TwitterConnector(vault_path=vault_path)

    if not connector.is_authenticated():
        return {
            'success': False,
            'error': 'Twitter not authenticated'
        }

    # Use the built-in sync method
    result = connector.sync(auto_ingest=False, limit=limit)

    return {
        'success': result.success,
        'items_fetched': result.items_fetched,
        'items_ingested': result.items_ingested,
        'errors': result.errors
    }
