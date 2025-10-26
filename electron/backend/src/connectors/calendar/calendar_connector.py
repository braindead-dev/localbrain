"""
Google Calendar Connector - Handles OAuth authentication and calendar event fetching.

This connector manages Google Calendar API access, fetches calendar events,
and converts them to plain text format for ingestion into LocalBrain.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Allow OAuth over HTTP for localhost development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from connectors.base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorStatus,
    ConnectorData,
    SyncResult
)


# OAuth 2.0 scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events.readonly'
]

# Redirect URI for OAuth callback
REDIRECT_URI = 'http://localhost:8765/connectors/calendar/auth/callback'


class CalendarConnector(BaseConnector):
    """
    Google Calendar connector for authenticating and fetching calendar events.
    
    Handles OAuth flow, token management, event retrieval, and text conversion.
    """
    
    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        """
        Initialize Calendar connector.
        
        Args:
            vault_path: Path to LocalBrain vault for ingestion
            config_dir: Directory to store connector config (default: ~/.localbrain/connectors/calendar)
        """
        # Initialize base connector
        super().__init__(vault_path=vault_path, config_dir=config_dir)
        
        # Set up credentials directory (separate from config)
        self.credentials_dir = Path.home() / '.localbrain' / 'credentials'
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.client_secrets_file = self.credentials_dir / 'calendar_client_secret.json'
        self.token_file = self.credentials_dir / 'calendar_token.json'
        self.calendar_config_file = self.credentials_dir / 'calendar_config.json'  # Legacy config
        self.flow_state_file = self.credentials_dir / 'calendar_flow_state.json'
        
        # Calendar service (initialized on first use)
        self._service = None
    
    # ========================================================================
    # BaseConnector Required Methods
    # ========================================================================
    
    def get_metadata(self) -> ConnectorMetadata:
        """Return Calendar connector metadata."""
        return ConnectorMetadata(
            id="calendar",
            name="Google Calendar",
            description="Sync calendar events and meetings",
            version="1.0.0",
            author="LocalBrain Team",
            auth_type="oauth",
            requires_config=True,
            sync_interval_minutes=60,  # Check for calendar updates hourly
            capabilities=["read"]
        )
    
    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """Check if there are new calendar events available."""
        if not self.is_authenticated():
            return False
        
        try:
            # Check for events in the next 7 days or since last sync
            now = datetime.now(timezone.utc)
            if since:
                start_time = since
            else:
                # Default to last 24 hours
                start_time = now - timedelta(days=1)
            
            end_time = now + timedelta(days=7)  # Look ahead 7 days
            
            # Fetch a small number of events to check if any exist
            events = self._fetch_events(start_time, end_time, 1)
            return len(events) > 0
            
        except Exception as e:
            print(f"Error checking for Calendar updates: {e}")
            return False
    
    def fetch_updates(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[ConnectorData]:
        """Fetch new calendar events since last sync."""
        if not self.is_authenticated():
            return []
        
        try:
            # Use existing sync method but adapt the return format
            if since:
                # Calculate days since the timestamp
                now = datetime.now(timezone.utc)
                days_diff = max(1, int((now - since).total_seconds() / 86400))  # Convert to days
                result = self.sync(max_results=limit or 100, days=days_diff)
            else:
                # Default to last 7 days
                result = self.sync(max_results=limit or 100, days=7)
            
            # Convert to ConnectorData format
            connector_data = []
            for event_data in result.get('events', []):
                connector_data.append(ConnectorData(
                    content=event_data['text'],
                    source_id=event_data['metadata']['source'].split('/')[-1],  # Extract event ID
                    timestamp=datetime.fromisoformat(event_data['metadata']['timestamp'].replace('Z', '+00:00')) if 'T' in event_data['metadata']['timestamp'] else datetime.now(),
                    metadata=event_data['metadata']
                ))
            
            return connector_data
            
        except Exception as e:
            print(f"Error fetching Calendar updates: {e}")
            return []
    
    def get_status(self) -> ConnectorStatus:
        """Get current Calendar connector status."""
        try:
            if not self.is_authenticated():
                return ConnectorStatus(
                    connected=False,
                    authenticated=False,
                    last_error="Not authenticated"
                )
            
            # Get status from existing method
            status_data = self._get_status_data()
            
            return ConnectorStatus(
                connected=status_data.get('connected', False),
                authenticated=True,
                last_sync=self._get_last_sync(),
                total_items_synced=status_data.get('totalProcessed', 0),
                config_valid=True,
                metadata={
                    'email': status_data.get('email'),
                    'calendar_count': status_data.get('calendar_count', 0),
                    'connectedAt': status_data.get('connectedAt')
                }
            )
            
        except Exception as e:
            return ConnectorStatus(
                connected=False,
                authenticated=False,
                last_error=str(e)
            )
    
    def authenticate(self, credentials: Dict) -> tuple[bool, Optional[str]]:
        """Handle OAuth authentication."""
        try:
            if 'authorization_response' in credentials:
                # Handle OAuth callback
                result = self.handle_callback(credentials['authorization_response'])
                return True, None
            else:
                return False, "Invalid credentials format"
        except Exception as e:
            return False, str(e)
    
    def revoke_access(self) -> bool:
        """Revoke Calendar access."""
        try:
            return self._revoke_calendar_access()
        except Exception:
            return False
    
    def sync(self, auto_ingest: bool = False, limit: Optional[int] = None) -> SyncResult:
        """
        Override BaseConnector sync to handle Calendar-specific logic and use agentic ingestion.
        
        On first sync: Fetches 3 months of past events
        On subsequent syncs: Fetches 7 days of events
        """
        try:
            # Check if this is the first sync
            last_sync = self._get_last_sync()
            is_first_sync = last_sync is None
            
            # Determine time range based on first sync
            if is_first_sync:
                # First sync: Get 1 week of past data
                days_to_fetch = 7  # 1 week
                print(f"📅 First Calendar sync - fetching {days_to_fetch} days of events...")
            else:
                # Regular sync: Get last 7 days
                days_to_fetch = 7
                print(f"📅 Regular Calendar sync - fetching {days_to_fetch} days of events...")
            
            # Calculate time range
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(days=days_to_fetch)
            
            # Fetch events
            events = self._fetch_events(start_time, now, limit or 500)
            
            # Convert to ConnectorData format
            connector_data = []
            for event in events:
                try:
                    event_data = self._event_to_structured_data(event)
                    connector_data.append(ConnectorData(
                        content=event_data['text'],
                        source_id=event_data['metadata']['source'].split('/')[-1],
                        timestamp=datetime.fromisoformat(event_data['metadata']['timestamp'].replace('Z', '+00:00')) if 'T' in event_data['metadata']['timestamp'] else datetime.now(),
                        metadata=event_data['metadata']
                    ))
                except Exception as e:
                    print(f"Error processing event: {e}")
                    continue
            
            print(f"📥 Fetched {len(connector_data)} calendar events")
            
            # Optionally ingest using Agentic Ingestion Pipeline
            ingested_count = 0
            if auto_ingest and self.vault_path:
                print(f"🔄 Ingesting {len(connector_data)} events into vault...")
                ingested_count = self._ingest_data_agentic(connector_data)
                print(f"✅ Ingested {ingested_count} events")
            
            # Update last sync timestamp
            now_timestamp = datetime.now()
            self._save_last_sync(now_timestamp)
            
            # Update config with sync stats
            config = self._load_config()
            config['last_sync'] = now_timestamp.isoformat()
            config['event_count'] = len(connector_data)
            config['total_events_processed'] = config.get('total_events_processed', 0) + len(connector_data)
            if is_first_sync:
                config['initial_sync_completed'] = True
                config['initial_sync_date'] = now_timestamp.isoformat()
            self._save_config(config)
            
            return SyncResult(
                success=True,
                items_fetched=len(connector_data),
                items_ingested=ingested_count,
                last_sync_timestamp=now_timestamp,
                metadata={
                    'is_first_sync': is_first_sync,
                    'days_fetched': days_to_fetch
                }
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return SyncResult(
                success=False,
                errors=[str(e)]
            )
    
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
        # Get client config from environment variables or file
        client_config = self._get_client_config()
        
        # Create OAuth flow
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Generate authorization URL
        auth_url, state = flow.authorization_url(
            access_type='offline',  # Request refresh token
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
        )
        
        # Save flow state for callback
        self._save_flow_state(flow, SCOPES)
        
        return auth_url
    
    def handle_callback(self, authorization_response: str) -> Dict:
        """
        Handle OAuth callback and save tokens.
        
        Args:
            authorization_response: Full callback URL with authorization code
            
        Returns:
            User info dict with email and connection status
        """
        # Get client config from environment variables or file
        client_config = self._get_client_config()
        
        # Create new flow from client config
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Exchange authorization code for tokens
        flow.fetch_token(authorization_response=authorization_response)
        
        # Save credentials
        credentials = flow.credentials
        self._save_credentials(credentials)
        
        # Get user email from OAuth info
        service = self._get_service(credentials)
        
        # Get primary calendar to verify access
        try:
            calendar_list = service.calendarList().list().execute()
            primary_calendar = None
            for calendar in calendar_list.get('items', []):
                if calendar.get('primary'):
                    primary_calendar = calendar
                    break
            
            user_email = primary_calendar.get('id', 'unknown@gmail.com') if primary_calendar else 'unknown@gmail.com'
        except Exception as e:
            print(f"Error getting calendar info: {e}")
            user_email = 'unknown@gmail.com'
        
        # Initialize config
        config = self._load_config()
        is_first_connection = config.get('email') is None
        config['email'] = user_email
        config['connected_at'] = datetime.now().isoformat()
        config['is_first_connection'] = is_first_connection
        self._save_config(config)
        
        # Clean up flow state file
        if self.flow_state_file.exists():
            self.flow_state_file.unlink()
        
        return {
            'email': user_email,
            'connected': True
        }
    
    def _revoke_calendar_access(self) -> bool:
        """
        Revoke OAuth access and delete local tokens.
        
        Returns:
            True if successful
        """
        # Get current credentials
        creds = self.get_credentials()
        
        if creds:
            # Revoke on Google's side
            try:
                import requests
                requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': creds.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
            except Exception as e:
                print(f"Error revoking token: {e}")
        
        # Delete local files
        if self.token_file.exists():
            self.token_file.unlink()
        if self.flow_state_file.exists():
            self.flow_state_file.unlink()
        
        # Reset config
        config = self._load_config()
        config['email'] = None
        config['connected_at'] = None
        self._save_config(config)
        
        return True
    
    def is_authenticated(self) -> bool:
        """Check if user has valid authentication."""
        creds = self.get_credentials()
        return creds is not None and creds.valid
    
    def needs_initial_sync(self) -> bool:
        """Check if initial sync (30 days of events) is needed."""
        config = self._load_config()
        return config.get('is_first_connection', False) and not config.get('initial_sync_completed', False)
    
    def get_credentials(self) -> Optional[Credentials]:
        """
        Get stored credentials, refreshing if needed.
        
        Returns:
            Valid Credentials object or None
        """
        if not self.token_file.exists():
            return None
        
        try:
            # Load credentials
            creds = Credentials.from_authorized_user_file(
                str(self.token_file),
                SCOPES
            )
            
            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self._save_credentials(creds)
            
            return creds if creds and creds.valid else None
            
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    # ========================================================================
    # Calendar Event Fetching Methods
    # ========================================================================
    
    def initial_sync(self, max_results: int = 500) -> Dict:
        """
        Initial sync to fetch calendar events from the past 30 days.
        
        Args:
            max_results: Maximum number of events to fetch (default: 500)
            
        Returns:
            Dict with sync statistics
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please connect Google Calendar first.")
        
        # Calculate timestamp for 30 days ago
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        now = datetime.now(timezone.utc)
        
        # Fetch events
        events = self._fetch_events(thirty_days_ago, now, max_results)
        
        # Convert to text format
        processed_events = []
        for event in events:
            try:
                event_data = self._event_to_structured_data(event)
                processed_events.append(event_data)
            except Exception as e:
                print(f"Error processing event {event.get('id')}: {e}")
                continue
        
        # Update config with initial sync completion
        config = self._load_config()
        config['initial_sync_completed'] = True
        config['initial_sync_date'] = datetime.now().isoformat()
        config['initial_sync_count'] = len(processed_events)
        config['is_first_connection'] = False  # Clear first connection flag
        config['last_sync'] = datetime.now().isoformat()
        config['event_count'] = len(processed_events)
        config['total_events_processed'] = config.get('total_events_processed', 0) + len(processed_events)
        self._save_config(config)
        
        return {
            'success': True,
            'events_fetched': len(events),
            'events_processed': len(processed_events),
            'time_window_days': 30,
            'query_start': thirty_days_ago.isoformat(),
            'query_end': now.isoformat(),
            'initial_sync': True,
            'events': processed_events
        }

    def _sync_legacy(self, max_results: int = 100, days: int = 7) -> Dict:
        """
        Legacy sync method - kept for compatibility.
        Use the sync() method from BaseConnector instead for agentic ingestion.
        
        Args:
            max_results: Maximum number of events to fetch (default: 100)
            days: Fetch events from last N days (default: 7)
            
        Returns:
            Dict with sync statistics
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please connect Google Calendar first.")
        
        # Calculate timestamp for N days ago
        time_ago = datetime.now(timezone.utc) - timedelta(days=days)
        now = datetime.now(timezone.utc)
        
        # Fetch events
        events = self._fetch_events(time_ago, now, max_results)
        
        # Convert to text format
        processed_events = []
        for event in events:
            try:
                event_data = self._event_to_structured_data(event)
                processed_events.append(event_data)
            except Exception as e:
                print(f"Error processing event {event.get('id')}: {e}")
                continue
        
        # Update config with sync stats
        config = self._load_config()
        config['last_sync'] = datetime.now().isoformat()
        config['event_count'] = len(processed_events)
        config['total_events_processed'] = config.get('total_events_processed', 0) + len(processed_events)
        self._save_config(config)
        
        return {
            'success': True,
            'events_fetched': len(events),
            'events_processed': len(processed_events),
            'time_window_days': days,
            'query_start': time_ago.isoformat(),
            'query_end': now.isoformat(),
            'events': processed_events
        }
    
    def fetch_upcoming_events(self, days: int = 14, max_results: int = 50) -> List[Dict]:
        """
        Fetch upcoming calendar events for the next N days.
        
        Args:
            days: Number of days to look ahead
            max_results: Maximum events to fetch
            
        Returns:
            List of event dicts with content and metadata
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please connect Google Calendar first.")
        
        # Calculate time range
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=days)
        
        # Fetch events
        events = self._fetch_events(now, end_date, max_results)
        
        # Convert to text
        processed_events = []
        for event in events:
            try:
                event_data = self._event_to_structured_data(event)
                processed_events.append(event_data)
            except Exception as e:
                print(f"Error processing event {event.get('id')}: {e}")
                continue
        
        return processed_events
    
    def _get_status_data(self) -> Dict:
        """
        Get Calendar connector status data.
        
        Returns:
            Status dict with connection info and stats
        """
        if not self.is_authenticated():
            return {'connected': False}
        
        try:
            # Get calendar list to verify access
            service = self._get_service()
            calendar_list = service.calendarList().list().execute()
            
            # Find primary calendar
            primary_calendar = None
            for calendar in calendar_list.get('items', []):
                if calendar.get('primary'):
                    primary_calendar = calendar
                    break
            
            # Load config
            config = self._load_config()
            
            return {
                'connected': True,
                'email': primary_calendar.get('id', 'unknown@gmail.com') if primary_calendar else config.get('email', 'unknown@gmail.com'),
                'calendar_count': len(calendar_list.get('items', [])),
                'lastSync': config.get('last_sync'),
                'eventCount': config.get('event_count', 0),
                'totalProcessed': config.get('total_events_processed', 0),
                'connectedAt': config.get('connected_at')
            }
        except Exception as e:
            print(f"Error getting status: {e}")
            return {'connected': False, 'error': str(e)}
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _get_service(self, credentials: Optional[Credentials] = None):
        """Get or create Calendar API service."""
        if self._service is None:
            if credentials is None:
                credentials = self.get_credentials()
            if credentials is None:
                raise Exception("No valid credentials available")
            self._service = build('calendar', 'v3', credentials=credentials)
        return self._service
    
    def _fetch_events(self, start_time: datetime, end_time: datetime, max_results: int) -> List[Dict]:
        """
        Fetch calendar events within time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            max_results: Maximum events to fetch
            
        Returns:
            List of calendar event objects
        """
        events = []
        service = self._get_service()
        
        try:
            # Get list of calendars
            calendar_list = service.calendarList().list().execute()
            
            for calendar in calendar_list.get('items', []):
                calendar_id = calendar['id']
                
                try:
                    # Fetch events from this calendar
                    events_result = service.events().list(
                        calendarId=calendar_id,
                        timeMin=start_time.isoformat(),
                        timeMax=end_time.isoformat(),
                        maxResults=max_results,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    calendar_events = events_result.get('items', [])
                    
                    # Add calendar info to each event
                    for event in calendar_events:
                        event['_calendar_name'] = calendar.get('summary', calendar_id)
                        event['_calendar_id'] = calendar_id
                    
                    events.extend(calendar_events)
                    
                except HttpError as e:
                    print(f"Error fetching events from calendar {calendar_id}: {e}")
                    continue
        
        except HttpError as e:
            print(f"Error listing calendars: {e}")
        
        return events
    
    def _ingest_data_agentic(self, items: List[ConnectorData]) -> int:
        """
        Ingest Calendar data using the Agentic Ingestion Pipeline.
        
        This uses the sophisticated ingestion system that:
        - Analyzes content intelligently
        - Routes to appropriate existing files
        - Uses proper citations and formatting
        - Follows vault structure (personal/, career/, etc.)
        """
        if not self.vault_path or not items:
            return 0
        
        try:
            # Import the agentic ingestion pipeline
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from agentic_ingest import AgenticIngestionPipeline
            
            # Initialize pipeline
            pipeline = AgenticIngestionPipeline(self.vault_path)
            
            ingested_count = 0
            for item in items:
                try:
                    # Prepare source metadata for the pipeline
                    source_metadata = {
                        'platform': 'Google Calendar',
                        'timestamp': item.timestamp.isoformat() if item.timestamp else datetime.now().isoformat(),
                        'url': item.metadata.get('url'),
                        'quote': item.metadata.get('quote', item.content[:200] + '...' if len(item.content) > 200 else item.content)
                    }
                    
                    # Use the agentic pipeline to ingest
                    result = pipeline.ingest(
                        context=item.content,
                        source_metadata=source_metadata
                    )
                    
                    if result.get('success', False):
                        ingested_count += 1
                        print(f"✅ Ingested Calendar event: {item.metadata.get('quote', 'Event')[:50]}...")
                    else:
                        print(f"⚠️  Failed to ingest Calendar event: {result.get('errors', ['Unknown error'])}")
                        
                except Exception as e:
                    print(f"⚠️  Error ingesting Calendar item: {e}")
                    continue
            
            return ingested_count
            
        except Exception as e:
            print(f"⚠️  Agentic ingestion failed, falling back to simple ingestion: {e}")
            # Fallback to simple ingestion if agentic pipeline fails
            return self._ingest_data(items)
    
    def _event_to_structured_data(self, event: Dict) -> Dict:
        """
        Convert Google Calendar event to simple text format for ingestion.
        
        Args:
            event: Google Calendar API event object
            
        Returns:
            Dict with simple text content and minimal metadata
        """
        # Extract basic info
        title = event.get('summary', '(No Title)')
        description = event.get('description', '')
        location = event.get('location', '')
        calendar_name = event.get('_calendar_name', 'Unknown Calendar')
        
        # Extract start and end times
        start = event.get('start', {})
        end = event.get('end', {})
        
        # Handle all-day events vs timed events
        if 'date' in start:
            # All-day event
            start_str = start['date']
            end_str = end.get('date', start['date'])
            event_type = 'All-day event'
        else:
            # Timed event
            start_str = start.get('dateTime', 'Unknown time')
            end_str = end.get('dateTime', 'Unknown time')
            event_type = 'Timed event'
        
        # Extract attendees
        attendees = event.get('attendees', [])
        attendees_text = ""
        if attendees:
            attendees_text = "\n\nAttendees:\n"
            for attendee in attendees:
                name = attendee.get('displayName', attendee.get('email', 'Unknown'))
                status = attendee.get('responseStatus', 'unknown')
                attendees_text += f"- {name} ({status})\n"
        
        # Extract recurring event info
        recurring_text = ""
        if event.get('recurringEventId'):
            recurring_text = "\n\n(This is a recurring event)"
        
        # Calendar URL
        calendar_url = event.get('htmlLink', f"https://calendar.google.com/calendar/event?eid={event.get('id', '')}")
        
        # Format as simple text (like a .txt file)
        text_content = f"""Calendar Event: {title}
Calendar: {calendar_name}
Type: {event_type}
Start: {start_str}
End: {end_str}
Location: {location}

{description}{attendees_text}{recurring_text}

---
Calendar URL: {calendar_url}
"""
        
        # Return simple format for ingestion
        return {
            'text': text_content,
            'metadata': {
                'platform': 'Google Calendar',
                'timestamp': start_str,
                'url': calendar_url,
                'quote': title,
                'source': f"Calendar/{event.get('id', 'unknown')}",
                'type': 'calendar_event',
                'calendar': calendar_name,
                'location': location,
                'start_time': start_str,
                'end_time': end_str
            }
        }
    
    # ========================================================================
    # Config/State Management
    # ========================================================================
    
    def _save_credentials(self, credentials: Credentials):
        """Save credentials to file."""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_file, 'w') as f:
            f.write(credentials.to_json())
    
    def _save_flow_state(self, flow: Flow, scopes: List[str]):
        """Save OAuth flow state for callback."""
        with open(self.flow_state_file, 'w') as f:
            json.dump({
                'client_config': flow.client_config,
                'redirect_uri': flow.redirect_uri,
                'scopes': scopes
            }, f)
    
    def _restore_flow_state(self) -> Flow:
        """Restore OAuth flow from saved state."""
        if not self.flow_state_file.exists():
            raise Exception("Flow state not found. Please start auth flow again.")
        
        with open(self.flow_state_file, 'r') as f:
            state = json.load(f)
        
        return Flow.from_client_config(
            client_config=state['client_config'],
            scopes=state['scopes'],
            redirect_uri=state['redirect_uri']
        )
    
    def _load_config(self) -> Dict:
        """Load connector configuration (legacy Calendar config)."""
        if self.calendar_config_file.exists():
            with open(self.calendar_config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_config(self, config: Dict):
        """Save connector configuration (legacy Calendar config)."""
        self.calendar_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.calendar_config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _get_client_config(self) -> Dict:
        """
        Get OAuth client configuration from environment variables or file.
        
        Priority:
        1. CALENDAR_CLIENT_CONFIG (entire JSON as string)
        2. Individual env vars (CALENDAR_CLIENT_ID, CALENDAR_CLIENT_SECRET, etc.)
        3. JSON file (calendar_client_secret.json)
        4. Fallback to Gmail credentials (since they're the same Google project)
        
        Returns:
            Client configuration dict for OAuth flow
            
        Raises:
            ValueError: If neither environment variables nor file are available
        """
        # Option 1: Try full JSON config from environment variable
        json_config = os.getenv('CALENDAR_CLIENT_CONFIG')
        if json_config:
            try:
                return json.loads(json_config)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in CALENDAR_CLIENT_CONFIG: {e}")
        
        # Option 2: Try individual environment variables
        client_id = os.getenv('CALENDAR_CLIENT_ID') or os.getenv('GMAIL_CLIENT_ID')
        client_secret = os.getenv('CALENDAR_CLIENT_SECRET') or os.getenv('GMAIL_CLIENT_SECRET')
        project_id = os.getenv('CALENDAR_PROJECT_ID') or os.getenv('GMAIL_PROJECT_ID', 'localbrain')
        
        if client_id and client_secret:
            # Use environment variables
            return {
                "installed": {
                    "client_id": client_id,
                    "project_id": project_id,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": client_secret,
                    "redirect_uris": ["http://localhost"]
                }
            }
        
        # Option 3: Try calendar-specific JSON file
        if self.client_secrets_file.exists():
            with open(self.client_secrets_file, 'r') as f:
                return json.load(f)
        
        # Option 4: Fallback to Gmail credentials file (same Google project)
        gmail_secrets_file = self.credentials_dir / 'gmail_client_secret.json'
        if gmail_secrets_file.exists():
            with open(gmail_secrets_file, 'r') as f:
                return json.load(f)
        
        # Neither available
        raise ValueError(
            "Google Calendar OAuth credentials not configured.\n\n"
            "Please either:\n"
            "1. Set CALENDAR_CLIENT_CONFIG with entire JSON:\n"
            '   CALENDAR_CLIENT_CONFIG=\'{"installed":{...}}\'\n\n'
            "2. Set individual environment variables:\n"
            "   CALENDAR_CLIENT_ID=your_client_id\n"
            "   CALENDAR_CLIENT_SECRET=your_client_secret\n"
            "   CALENDAR_PROJECT_ID=your_project_id (optional)\n\n"
            "3. Or place calendar_client_secret.json at:\n"
            f"   {self.client_secrets_file}\n\n"
            "4. Or use the same Gmail credentials (gmail_client_secret.json)"
        )


# ============================================================================
# Sync Function for Background Tasks
# ============================================================================

def sync_calendar_events(vault_path: Path, max_results: int = 100, days: int = 7) -> Dict:
    """
    Helper function to sync Google Calendar events and ingest them.
    
    Args:
        vault_path: Path to LocalBrain vault
        max_results: Max events to fetch
        days: Fetch events from last N days
        
    Returns:
        Dict with sync results
    """
    connector = CalendarConnector(vault_path=vault_path)
    
    if not connector.is_authenticated():
        return {
            'success': False,
            'error': 'Google Calendar not authenticated'
        }
    
    result = connector.sync(max_results=max_results, days=days)
    return result
