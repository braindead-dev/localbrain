"""
GitHub Connector - Syncs GitHub activity via OAuth.

This connector authenticates with GitHub using OAuth 2.0 and fetches
repositories, issues, pull requests, and commits for ingestion into LocalBrain.
"""

import os
import json
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


# GitHub OAuth 2.0 URLs
AUTHORIZATION_URL = 'https://github.com/login/oauth/authorize'
TOKEN_URL = 'https://github.com/login/oauth/access_token'
REDIRECT_URI = 'http://localhost:8765/connectors/github/auth/callback'

# GitHub API configuration
GITHUB_API_BASE = 'https://api.github.com'

# Scopes required for reading repositories and activity
SCOPES = [
    'repo',  # Full control of private repositories
    'read:user'  # Read user profile data
]


class GitHubConnector(BaseConnector):
    """
    GitHub connector for syncing repositories, issues, and activity.

    Handles OAuth flow, token management, and content retrieval from GitHub.
    """

    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        """
        Initialize GitHub connector.

        Args:
            vault_path: Path to LocalBrain vault for ingestion
            config_dir: Directory to store connector config (default: ~/.localbrain/connectors/github)
        """
        # Initialize base connector
        super().__init__(vault_path=vault_path, config_dir=config_dir)

        # Set up credentials directory
        self.credentials_dir = Path.home() / '.localbrain' / 'credentials'
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.token_file = self.credentials_dir / 'github_token.json'
        self.config_file = self.credentials_dir / 'github_config.json'

    # ========================================================================
    # BaseConnector Required Methods
    # ========================================================================

    def get_metadata(self) -> ConnectorMetadata:
        """Return GitHub connector metadata."""
        return ConnectorMetadata(
            id="github",
            name="GitHub",
            description="Sync GitHub repositories, issues, and activity",
            version="1.0.0",
            author="LocalBrain Team",
            auth_type="oauth",
            requires_config=True,
            sync_interval_minutes=30,  # Check for updates every 30 minutes
            capabilities=["read"]
        )

    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """Check if there are new activities available."""
        if not self.is_authenticated():
            return False

        try:
            access_token = self.get_access_token()
            if not access_token:
                return False

            # Check for recent events
            response = requests.get(
                f'{GITHUB_API_BASE}/users/{self._get_username()}/events',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/vnd.github+json'
                },
                params={'per_page': 1}
            )

            if response.status_code != 200:
                return False

            events = response.json()
            if not events:
                return False

            if since:
                event_time = datetime.fromisoformat(events[0]['created_at'].replace('Z', '+00:00'))
                return event_time > since

            return True

        except Exception as e:
            print(f"Error checking for GitHub updates: {e}")
            return False

    def fetch_updates(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[ConnectorData]:
        """Fetch GitHub activities since last sync."""
        if not self.is_authenticated():
            return []

        try:
            access_token = self.get_access_token()
            if not access_token:
                return []

            # Fetch events (activity feed)
            events = self._fetch_events(access_token, limit or 100)

            # Convert to ConnectorData format
            connector_data = []

            for event in events:
                try:
                    # Filter by time if since is provided
                    created_at = event.get('created_at')
                    if since and created_at:
                        event_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if event_time <= since:
                            continue

                    event_data = self._event_to_text(event)
                    if event_data:
                        timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if created_at else datetime.now(timezone.utc)

                        connector_data.append(ConnectorData(
                            content=event_data['text'],
                            source_id=event['id'],
                            timestamp=timestamp,
                            metadata=event_data['metadata']
                        ))

                except Exception as e:
                    print(f"Error processing GitHub event {event.get('id')}: {e}")
                    continue

            return connector_data

        except Exception as e:
            print(f"Error fetching GitHub updates: {e}")
            return []

    def get_status(self) -> ConnectorStatus:
        """Get current GitHub connector status."""
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
                total_items_synced=config.get('total_events_synced', 0),
                config_valid=True,
                metadata={
                    'username': config.get('username'),
                    'name': config.get('name'),
                    'email': config.get('email'),
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
        """Revoke GitHub access."""
        try:
            # Delete local token file
            if self.token_file.exists():
                self.token_file.unlink()

            # Reset config
            config = self._load_config()
            config['username'] = None
            config['name'] = None
            config['email'] = None
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
        scope_string = ' '.join(SCOPES)
        auth_url = (
            f"{AUTHORIZATION_URL}"
            f"?client_id={client_id}"
            f"&redirect_uri={REDIRECT_URI}"
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

        if not code:
            raise ValueError("No authorization code in callback")

        # Exchange code for token
        client_id = self._get_client_id()
        client_secret = self._get_client_secret()

        response = requests.post(
            TOKEN_URL,
            headers={
                'Accept': 'application/json'
            },
            data={
                'client_id': client_id,
                'client_secret': client_secret,
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
        config['username'] = user_info.get('login')
        config['name'] = user_info.get('name')
        config['email'] = user_info.get('email')
        config['connected_at'] = datetime.now().isoformat()
        self._save_config(config)

        return {
            'username': config['username'],
            'name': config['name'],
            'connected': True
        }

    def is_authenticated(self) -> bool:
        """Check if user has valid authentication."""
        return self.token_file.exists()

    def get_access_token(self) -> Optional[str]:
        """Get stored access token."""
        token_data = self._load_token()
        if not token_data:
            return None
        return token_data.get('access_token')

    # ========================================================================
    # GitHub API Methods
    # ========================================================================

    def _get_user_info(self, access_token: str) -> Dict:
        """Get user profile information."""
        response = requests.get(
            f'{GITHUB_API_BASE}/user',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/vnd.github+json'
            }
        )

        if response.status_code != 200:
            return {}

        return response.json()

    def _get_username(self) -> str:
        """Get stored username."""
        config = self._load_config()
        return config.get('username', 'unknown')

    def _fetch_events(self, access_token: str, limit: int) -> List[Dict]:
        """
        Fetch user events (activity feed) from GitHub.

        Args:
            access_token: Valid access token
            limit: Maximum number of events to fetch

        Returns:
            List of event objects
        """
        events = []
        username = self._get_username()

        page = 1
        per_page = min(100, limit)

        while len(events) < limit:
            response = requests.get(
                f'{GITHUB_API_BASE}/users/{username}/events',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/vnd.github+json'
                },
                params={
                    'per_page': per_page,
                    'page': page
                }
            )

            if response.status_code != 200:
                print(f"Error fetching events: {response.text}")
                break

            page_events = response.json()
            if not page_events:
                break

            events.extend(page_events)
            page += 1

        return events[:limit]

    def _event_to_text(self, event: Dict) -> Optional[Dict]:
        """
        Convert GitHub event to text format.

        Args:
            event: GitHub event object

        Returns:
            Dict with text content and metadata
        """
        event_type = event.get('type')
        repo_name = event.get('repo', {}).get('name', 'Unknown')
        created_at = event.get('created_at', '')
        payload = event.get('payload', {})

        # Format based on event type
        if event_type == 'PushEvent':
            commits = payload.get('commits', [])
            commit_messages = '\n'.join([f"- {c.get('message', '')}" for c in commits[:5]])
            text = f"""GitHub Push Event
Repository: {repo_name}
Date: {created_at}

Commits:
{commit_messages}
"""
            quote = f"Pushed {len(commits)} commit(s) to {repo_name}"

        elif event_type == 'IssuesEvent':
            action = payload.get('action', 'unknown')
            issue = payload.get('issue', {})
            title = issue.get('title', 'Unknown')
            body = issue.get('body', '')
            text = f"""GitHub Issue {action.capitalize()}
Repository: {repo_name}
Date: {created_at}
Title: {title}

{body}
"""
            quote = f"{action.capitalize()} issue: {title}"

        elif event_type == 'PullRequestEvent':
            action = payload.get('action', 'unknown')
            pr = payload.get('pull_request', {})
            title = pr.get('title', 'Unknown')
            body = pr.get('body', '')
            text = f"""GitHub Pull Request {action.capitalize()}
Repository: {repo_name}
Date: {created_at}
Title: {title}

{body}
"""
            quote = f"{action.capitalize()} PR: {title}"

        elif event_type == 'CreateEvent':
            ref_type = payload.get('ref_type', 'unknown')
            ref = payload.get('ref', '')
            text = f"""GitHub Create Event
Repository: {repo_name}
Date: {created_at}
Created: {ref_type} {ref}
"""
            quote = f"Created {ref_type} in {repo_name}"

        elif event_type == 'WatchEvent':
            text = f"""GitHub Watch Event
Repository: {repo_name}
Date: {created_at}
Action: Starred repository
"""
            quote = f"Starred {repo_name}"

        else:
            # Generic event
            text = f"""GitHub {event_type}
Repository: {repo_name}
Date: {created_at}
"""
            quote = f"{event_type} in {repo_name}"

        return {
            'text': text,
            'metadata': {
                'platform': 'GitHub',
                'type': event_type.lower(),
                'repository': repo_name,
                'timestamp': created_at,
                'quote': quote
            }
        }

    # ========================================================================
    # Config/Token Management
    # ========================================================================

    def _save_token(self, token_data: Dict):
        """Save OAuth token to file."""
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
        """Get GitHub OAuth client ID from environment."""
        client_id = os.getenv('GITHUB_CLIENT_ID')
        if not client_id:
            raise ValueError(
                "GITHUB_CLIENT_ID environment variable not set.\n"
                "Please set it with your GitHub OAuth App client ID."
            )
        return client_id

    def _get_client_secret(self) -> str:
        """Get GitHub OAuth client secret from environment."""
        client_secret = os.getenv('GITHUB_CLIENT_SECRET')
        if not client_secret:
            raise ValueError(
                "GITHUB_CLIENT_SECRET environment variable not set.\n"
                "Please set it with your GitHub OAuth App client secret."
            )
        return client_secret


# ============================================================================
# Helper Function for Background Sync
# ============================================================================

def sync_github(vault_path: Path, limit: int = 100) -> Dict:
    """
    Helper function to sync GitHub activity and ingest it.

    Args:
        vault_path: Path to LocalBrain vault
        limit: Maximum number of events to fetch

    Returns:
        Dict with sync results
    """
    connector = GitHubConnector(vault_path=vault_path)

    if not connector.is_authenticated():
        return {
            'success': False,
            'error': 'GitHub not authenticated'
        }

    # Use the built-in sync method
    result = connector.sync(auto_ingest=False, limit=limit)

    return {
        'success': result.success,
        'items_fetched': result.items_fetched,
        'items_ingested': result.items_ingested,
        'errors': result.errors
    }
