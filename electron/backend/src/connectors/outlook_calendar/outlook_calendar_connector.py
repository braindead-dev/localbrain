"""
Outlook Calendar Connector - Syncs Outlook calendar events via Microsoft Graph API.

This connector authenticates with Microsoft Graph using OAuth 2.0 and fetches
calendar events for ingestion into LocalBrain.
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


# Microsoft OAuth 2.0 URLs
AUTHORIZATION_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
REDIRECT_URI = 'http://localhost:8765/connectors/outlook_calendar/auth/callback'

# Microsoft Graph API configuration
GRAPH_API_BASE = 'https://graph.microsoft.com/v1.0'

# Scopes required for reading calendar
SCOPES = [
    'offline_access',
    'User.Read',
    'Calendars.Read'
]


class OutlookCalendarConnector(BaseConnector):
    """
    Outlook Calendar connector for syncing calendar events.

    Handles OAuth flow, token management, and event retrieval from Outlook/Microsoft 365 Calendar.
    """

    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        """
        Initialize Outlook Calendar connector.

        Args:
            vault_path: Path to LocalBrain vault for ingestion
            config_dir: Directory to store connector config (default: ~/.localbrain/connectors/outlook_calendar)
        """
        # Initialize base connector
        super().__init__(vault_path=vault_path, config_dir=config_dir)

        # Set up credentials directory
        self.credentials_dir = Path.home() / '.localbrain' / 'credentials'
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.token_file = self.credentials_dir / 'outlook_calendar_token.json'
        self.config_file = self.credentials_dir / 'outlook_calendar_config.json'

    # ========================================================================
    # BaseConnector Required Methods
    # ========================================================================

    def get_metadata(self) -> ConnectorMetadata:
        """Return Outlook Calendar connector metadata."""
        return ConnectorMetadata(
            id="outlook_calendar",
            name="Outlook Calendar",
            description="Sync Outlook/Microsoft 365 calendar events",
            version="1.0.0",
            author="LocalBrain Team",
            auth_type="oauth",
            requires_config=True,
            sync_interval_minutes=30,  # Check for new events every 30 minutes
            capabilities=["read"]
        )

    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """Check if there are new/updated calendar events available."""
        if not self.is_authenticated():
            return False

        try:
            access_token = self.get_access_token()
            if not access_token:
                return False

            # Check for events in a reasonable time window
            now = datetime.now(timezone.utc)
            start_time = since if since else (now - timedelta(days=7))
            end_time = now + timedelta(days=30)  # Look ahead 30 days

            # Build query parameters
            params = {
                '$top': 1,
                '$orderby': 'start/dateTime',
                '$filter': f"start/dateTime ge '{start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}' and start/dateTime le '{end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}'"
            }

            response = requests.get(
                f'{GRAPH_API_BASE}/me/calendar/events',
                headers={
                    'Authorization': f'Bearer {access_token}'
                },
                params=params
            )

            if response.status_code != 200:
                print(f"Error checking for updates: {response.text}")
                return False

            data = response.json()
            return len(data.get('value', [])) > 0

        except Exception as e:
            print(f"Error checking for Outlook Calendar updates: {e}")
            return False

    def fetch_updates(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[ConnectorData]:
        """Fetch calendar events since last sync."""
        if not self.is_authenticated():
            return []

        try:
            access_token = self.get_access_token()
            if not access_token:
                return []

            # Fetch events
            events = self._fetch_events(access_token, since, limit or 100)

            # Convert to ConnectorData format
            connector_data = []

            for event in events:
                try:
                    event_data = self._event_to_text(event)

                    start_dt_str = event.get('start', {}).get('dateTime')
                    if start_dt_str:
                        timestamp = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))
                    else:
                        timestamp = datetime.now(timezone.utc)

                    connector_data.append(ConnectorData(
                        content=event_data['text'],
                        source_id=event['id'],
                        timestamp=timestamp,
                        metadata=event_data['metadata']
                    ))

                except Exception as e:
                    print(f"Error processing event {event.get('id')}: {e}")
                    continue

            return connector_data

        except Exception as e:
            print(f"Error fetching Outlook Calendar updates: {e}")
            return []

    def get_status(self) -> ConnectorStatus:
        """Get current Outlook Calendar connector status."""
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
                    'email': config.get('email'),
                    'display_name': config.get('display_name'),
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
        """Revoke Outlook Calendar access."""
        try:
            # Delete local token file
            if self.token_file.exists():
                self.token_file.unlink()

            # Reset config
            config = self._load_config()
            config['email'] = None
            config['display_name'] = None
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
            f"&response_type=code"
            f"&redirect_uri={REDIRECT_URI}"
            f"&response_mode=query"
            f"&scope={scope_string}"
        )

        return auth_url

    def handle_callback(self, authorization_response: str) -> Dict:
        """
        Handle OAuth callback and save tokens.

        Args:
            authorization_response: Full callback URL with authorization code

        Returns:
            User info dict with email and connection status
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
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'redirect_uri': REDIRECT_URI,
                'grant_type': 'authorization_code',
                'scope': ' '.join(SCOPES)
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
        config['email'] = user_info.get('mail') or user_info.get('userPrincipalName')
        config['display_name'] = user_info.get('displayName')
        config['connected_at'] = datetime.now().isoformat()
        self._save_config(config)

        return {
            'email': config['email'],
            'display_name': config['display_name'],
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

            # Try to refresh if we have a refresh token
            if 'refresh_token' in token_data:
                return True

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

            response = requests.post(
                TOKEN_URL,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token',
                    'scope': ' '.join(SCOPES)
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
    # Microsoft Graph API Methods
    # ========================================================================

    def _get_user_info(self, access_token: str) -> Dict:
        """Get user profile information."""
        response = requests.get(
            f'{GRAPH_API_BASE}/me',
            headers={
                'Authorization': f'Bearer {access_token}'
            }
        )

        if response.status_code != 200:
            return {}

        return response.json()

    def _fetch_events(self, access_token: str, since: Optional[datetime], limit: int) -> List[Dict]:
        """
        Fetch calendar events from Outlook/Microsoft 365.

        Args:
            access_token: Valid access token
            since: Only fetch events starting after this time
            limit: Maximum number of events to fetch

        Returns:
            List of event objects
        """
        events = []

        # Calculate time window
        now = datetime.now(timezone.utc)
        start_time = since if since else (now - timedelta(days=7))
        end_time = now + timedelta(days=30)  # Look ahead 30 days

        # Build query parameters
        params = {
            '$top': min(100, limit),
            '$orderby': 'start/dateTime',
            '$select': 'id,subject,start,end,location,bodyPreview,attendees,isAllDay,organizer',
            '$filter': f"start/dateTime ge '{start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}' and start/dateTime le '{end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}'"
        }

        url = f'{GRAPH_API_BASE}/me/calendar/events'

        while url and len(events) < limit:
            response = requests.get(
                url,
                headers={
                    'Authorization': f'Bearer {access_token}'
                },
                params=params if url == f'{GRAPH_API_BASE}/me/calendar/events' else None
            )

            if response.status_code != 200:
                print(f"Error fetching events: {response.text}")
                break

            data = response.json()
            events.extend(data.get('value', []))

            # Check for pagination
            url = data.get('@odata.nextLink')

        return events[:limit]

    def _event_to_text(self, event: Dict) -> Dict:
        """
        Convert Outlook calendar event to text format.

        Args:
            event: Microsoft Graph event object

        Returns:
            Dict with text content and metadata
        """
        # Extract fields
        subject = event.get('subject', '(No Subject)')

        start_obj = event.get('start', {})
        start_dt = start_obj.get('dateTime', '')
        start_tz = start_obj.get('timeZone', 'UTC')

        end_obj = event.get('end', {})
        end_dt = end_obj.get('dateTime', '')
        end_tz = end_obj.get('timeZone', 'UTC')

        is_all_day = event.get('isAllDay', False)

        location = event.get('location', {}).get('displayName', '')
        body_preview = event.get('bodyPreview', '')

        # Organizer
        organizer = event.get('organizer', {}).get('emailAddress', {})
        organizer_name = organizer.get('name', organizer.get('address', 'Unknown'))

        # Attendees
        attendees = event.get('attendees', [])
        attendees_text = ""
        if attendees:
            attendees_text = "\n\nAttendees:\n"
            for attendee in attendees:
                email_address = attendee.get('emailAddress', {})
                name = email_address.get('name', email_address.get('address', 'Unknown'))
                response_status = attendee.get('status', {}).get('response', 'none')
                attendees_text += f"- {name} ({response_status})\n"

        # Format as text
        event_type = "All-day event" if is_all_day else "Event"

        text_content = f"""Calendar Event: {subject}
Organizer: {organizer_name}
Type: {event_type}
Start: {start_dt} ({start_tz})
End: {end_dt} ({end_tz})
Location: {location}

{body_preview}{attendees_text}
"""

        return {
            'text': text_content,
            'metadata': {
                'platform': 'Outlook Calendar',
                'type': 'calendar_event',
                'subject': subject,
                'organizer': organizer_name,
                'location': location,
                'start_time': start_dt,
                'end_time': end_dt,
                'is_all_day': is_all_day,
                'timestamp': start_dt,
                'quote': subject
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
        """Get Microsoft OAuth client ID from environment."""
        client_id = os.getenv('OUTLOOK_CLIENT_ID') or os.getenv('MICROSOFT_CLIENT_ID')
        if not client_id:
            raise ValueError(
                "OUTLOOK_CLIENT_ID or MICROSOFT_CLIENT_ID environment variable not set.\n"
                "Please set it with your Microsoft Azure application client ID."
            )
        return client_id

    def _get_client_secret(self) -> str:
        """Get Microsoft OAuth client secret from environment."""
        client_secret = os.getenv('OUTLOOK_CLIENT_SECRET') or os.getenv('MICROSOFT_CLIENT_SECRET')
        if not client_secret:
            raise ValueError(
                "OUTLOOK_CLIENT_SECRET or MICROSOFT_CLIENT_SECRET environment variable not set.\n"
                "Please set it with your Microsoft Azure application client secret."
            )
        return client_secret


# ============================================================================
# Helper Function for Background Sync
# ============================================================================

def sync_outlook_calendar(vault_path: Path, limit: int = 100) -> Dict:
    """
    Helper function to sync Outlook calendar events and ingest them.

    Args:
        vault_path: Path to LocalBrain vault
        limit: Maximum number of events to fetch

    Returns:
        Dict with sync results
    """
    connector = OutlookCalendarConnector(vault_path=vault_path)

    if not connector.is_authenticated():
        return {
            'success': False,
            'error': 'Outlook Calendar not authenticated'
        }

    # Use the built-in sync method
    result = connector.sync(auto_ingest=False, limit=limit)

    return {
        'success': result.success,
        'items_fetched': result.items_fetched,
        'items_ingested': result.items_ingested,
        'errors': result.errors
    }
