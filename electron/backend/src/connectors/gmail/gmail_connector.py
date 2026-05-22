"""
Gmail Connector - Handles OAuth authentication and email fetching.

This connector manages Gmail API access, fetches emails, and converts them
to plain text format for ingestion into LocalBrain.
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Allow OAuth over HTTP for localhost development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import html2text

from connectors.base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorStatus,
    ConnectorData,
    SyncResult
)


# OAuth 2.0 scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.labels'
]

# Redirect URI for OAuth callback
REDIRECT_URI = 'http://localhost:8765/connectors/gmail/auth/callback'


class GmailConnector(BaseConnector):
    """
    Gmail connector for authenticating and fetching emails.
    
    Handles OAuth flow, token management, email retrieval, and text conversion.
    """
    
    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        """
        Initialize Gmail connector.
        
        Args:
            vault_path: Path to LocalBrain vault for ingestion
            config_dir: Directory to store connector config (default: ~/.localbrain/connectors/gmail)
        """
        # Initialize base connector
        super().__init__(vault_path=vault_path, config_dir=config_dir)
        
        # Set up credentials directory (separate from config)
        self.credentials_dir = Path.home() / '.localbrain' / 'credentials'
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.client_secrets_file = self.credentials_dir / 'gmail_client_secret.json'
        self.token_file = self.credentials_dir / 'gmail_token.json'
        self.gmail_config_file = self.credentials_dir / 'gmail_config.json'  # Legacy config
        self.flow_state_file = self.credentials_dir / 'flow_state.json'
        
        # Gmail service (initialized on first use)
        self._service = None
    
    # ========================================================================
    # BaseConnector Required Methods
    # ========================================================================
    
    def get_metadata(self) -> ConnectorMetadata:
        """Return Gmail connector metadata."""
        return ConnectorMetadata(
            id="gmail",
            name="Gmail",
            description="Sync emails from Gmail inbox",
            version="1.0.0",
            author="LocalBrain Team",
            auth_type="oauth",
            requires_config=True,
            sync_interval_minutes=10,
            capabilities=["read"]
        )
    
    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """Check if there are new emails available."""
        if not self.is_authenticated():
            return False
        
        try:
            # Use Gmail API to check for new messages
            service = self._get_service()
            
            # Build query based on timestamp
            if since:
                # Convert to Unix timestamp for Gmail API
                timestamp = int(since.timestamp())
                query = f'after:{timestamp} in:inbox category:primary -in:spam -in:trash'
            else:
                # Check for any emails in last 24 hours
                yesterday = datetime.now() - timedelta(days=1)
                timestamp = int(yesterday.timestamp())
                query = f'after:{timestamp} in:inbox category:primary -in:spam -in:trash'
            
            # Just check if any messages exist
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=1
            ).execute()
            
            messages = results.get('messages', [])
            return len(messages) > 0
            
        except Exception as e:
            logger.warning(f"Error checking for Gmail updates: {e}")
            return False
    
    def fetch_updates(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[ConnectorData]:
        """Fetch new emails since last sync."""
        logger.info(f"[Gmail] fetch_updates since={since} limit={limit}")

        if not self.is_authenticated():
            logger.warning("[Gmail] Not authenticated, cannot fetch updates")
            return []
        
        try:
            # Use the since timestamp to compute a minutes-based lookback window.
            # Fall back to 24 hours if no since is recorded (first sync).
            if since:
                delta_minutes = max(1, int((datetime.now() - since.replace(tzinfo=None)).total_seconds() / 60))
            else:
                delta_minutes = 1440  # 24 hours on first sync
            fetch_limit = limit or 50
            logger.info(f"[Gmail] Fetching up to {fetch_limit} emails from the last {delta_minutes} minutes")
            result = self._sync_emails(max_results=fetch_limit, minutes=delta_minutes)
            
            # Convert to ConnectorData format
            connector_data = []
            for email_data in result.get('emails', []):
                connector_data.append(ConnectorData(
                    content=email_data['text'],
                    source_id=email_data['metadata']['source'].split('/')[-1],  # Extract Gmail ID
                    timestamp=self._parse_email_timestamp(email_data['metadata']['timestamp']),
                    metadata=email_data['metadata']
                ))
            
            logger.info(f"[Gmail] Fetched {len(connector_data)} emails")
            
            return connector_data
            
        except Exception as e:
            logger.exception(f"[Gmail] Error fetching updates: {e}")
            return []
    
    def _parse_email_timestamp(self, timestamp_str: str) -> datetime:
        """Parse email timestamp from various formats."""
        try:
            # Try RFC 2822 format first (e.g., "Sat, 25 Oct 2025 23:58:53 +0000")
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(timestamp_str)
        except:
            try:
                # Try ISO format
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                # Fallback to current time
                return datetime.now()
    
    def _ingest_data_agentic(self, items: List[ConnectorData]) -> int:
        """
        Ingest Gmail data using the Agentic Ingestion Pipeline.
        
        This uses the sophisticated ingestion system that:
        - Analyzes content intelligently
        - Routes to appropriate existing files
        - Uses proper citations and formatting
        - Follows vault structure (personal/, career/, etc.)
        """
        logger.info(f"[Gmail Ingestion] Starting agentic ingestion for {len(items)} emails")

        if not self.vault_path:
            logger.warning("[Gmail Ingestion] No vault path configured, skipping ingestion")
            return 0

        if not items:
            logger.info("[Gmail Ingestion] No items to ingest")
            return 0

        try:
            # Import the agentic ingestion pipeline
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from agentic_ingest import AgenticIngestionPipeline

            logger.debug(f"[Gmail Ingestion] Vault path: {self.vault_path}")

            # Initialize pipeline
            pipeline = AgenticIngestionPipeline(self.vault_path)

            ingested_count = 0
            for i, item in enumerate(items, 1):
                try:
                    subject = item.metadata.get('quote', 'No subject')
                    logger.info(f"[Gmail Ingestion] [{i}/{len(items)}] Ingesting: {subject[:60]}")

                    # Prepare source metadata for the pipeline
                    source_metadata = {
                        'platform': 'Gmail',
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
                        file_path = result.get('file_path', 'unknown')
                        logger.info(f"[Gmail Ingestion] Ingested to: {file_path}")
                    else:
                        errors = result.get('errors', ['Unknown error'])
                        logger.warning(f"[Gmail Ingestion] Failed to ingest: {errors}")

                except Exception as e:
                    logger.exception(f"[Gmail Ingestion] Error ingesting item: {e}")
                    continue

            logger.info(f"[Gmail Ingestion] Completed: {ingested_count}/{len(items)} emails ingested")
            return ingested_count

        except Exception as e:
            logger.exception(f"[Gmail Ingestion] Agentic ingestion failed: {e}")
            logger.info("[Gmail Ingestion] Falling back to simple ingestion")
            # Fallback to simple ingestion if agentic pipeline fails
            return self._ingest_data(items)
    
    def sync(self, auto_ingest: bool = False, limit: Optional[int] = None) -> SyncResult:
        """
        Override BaseConnector sync to handle Gmail-specific time windows.
        Gmail often wants to fetch emails from a specific time window rather than incremental sync.
        """
        logger.info(f"[Gmail Sync] Starting sync | auto_ingest={auto_ingest} limit={limit} vault={self.vault_path}")

        try:
            # Always fetch updates (Gmail doesn't follow strict incremental sync)
            items = self.fetch_updates(limit=limit)

            # Optionally ingest using Agentic Ingestion Pipeline
            ingested_count = 0
            if auto_ingest:
                if self.vault_path:
                    logger.info("[Gmail Sync] Auto-ingest enabled, starting ingestion")
                    ingested_count = self._ingest_data_agentic(items)
                else:
                    logger.warning("[Gmail Sync] Auto-ingest enabled but no vault path configured")
            else:
                logger.info("[Gmail Sync] Auto-ingest disabled, skipping ingestion")

            # Update last sync timestamp
            now = datetime.now()
            self._save_last_sync(now)

            logger.info(f"[Gmail Sync] Completed | fetched={len(items)} ingested={ingested_count}")

            return SyncResult(
                success=True,
                items_fetched=len(items),
                items_ingested=ingested_count,
                last_sync_timestamp=now
            )

        except Exception as e:
            logger.exception(f"[Gmail Sync] Failed: {e}")
            return SyncResult(
                success=False,
                errors=[str(e)]
            )
    
    def get_status(self) -> ConnectorStatus:
        """Get current Gmail connector status."""
        try:
            if not self.is_authenticated():
                return ConnectorStatus(
                    connected=False,
                    authenticated=False,
                    last_error="Not authenticated"
                )
            
            # Having valid credentials means connected. Enrich with live data if
            # available, but don't let a failing API call override connected state.
            status_data = self._get_status_data()

            return ConnectorStatus(
                connected=True,
                authenticated=True,
                last_sync=self._get_last_sync(),
                total_items_synced=status_data.get('totalProcessed', 0),
                config_valid=True,
                metadata={
                    'email': status_data.get('email'),
                    'emailCount': status_data.get('emailCount', 0),
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
        """Revoke Gmail access."""
        try:
            return self._revoke_gmail_access()
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
        
        # Get user email
        service = self._get_service(credentials)
        profile = service.users().getProfile(userId='me').execute()
        
        # Initialize config
        config = self._load_config()
        is_first_connection = config.get('email') is None
        config['email'] = profile['emailAddress']
        config['connected_at'] = datetime.now().isoformat()
        config['is_first_connection'] = is_first_connection
        self._save_config(config)
        
        # Clean up flow state file
        if self.flow_state_file.exists():
            self.flow_state_file.unlink()
        
        return {
            'email': profile['emailAddress'],
            'connected': True
        }
    
    def _revoke_gmail_access(self) -> bool:
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
                logger.warning(f"Error revoking Gmail token: {e}")

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
        """Check if initial sync (2 weeks of emails) is needed."""
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
            logger.warning(f"Error loading Gmail credentials: {e}")
            return None
    
    # ========================================================================
    # Email Fetching Methods
    # ========================================================================
    
    def initial_sync(self, max_results: int = 500) -> Dict:
        """
        Initial sync to fetch emails from the past 2 weeks.
        
        Args:
            max_results: Maximum number of emails to fetch (default: 500)
            
        Returns:
            Dict with sync statistics
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please connect Gmail first.")
        
        # Calculate timestamp for 2 weeks ago
        two_weeks_ago = datetime.now() - timedelta(days=14)  # 2 weeks = 14 days
        
        # Build query - fetch emails from last 2 weeks in inbox (all categories)
        query = f'after:{two_weeks_ago.strftime("%Y/%m/%d")} in:inbox -in:spam -in:trash'
        
        # Fetch emails
        emails = self._fetch_emails(query, max_results)
        
        # Convert to text format
        processed_emails = []
        for email in emails:
            try:
                email_data = self._email_to_structured_data(email)
                processed_emails.append(email_data)
            except Exception as e:
                logger.warning(f"Error processing email {email.get('id')}: {e}")
                continue
        
        # Update config with initial sync completion
        config = self._load_config()
        config['initial_sync_completed'] = True
        config['initial_sync_date'] = datetime.now().isoformat()
        config['initial_sync_count'] = len(processed_emails)
        config['is_first_connection'] = False  # Clear first connection flag
        config['last_sync'] = datetime.now().isoformat()
        config['email_count'] = len(processed_emails)
        config['total_emails_processed'] = config.get('total_emails_processed', 0) + len(processed_emails)
        self._save_config(config)
        
        return {
            'success': True,
            'emails_fetched': len(emails),
            'emails_processed': len(processed_emails),
            'time_window_days': 730,
            'query_date': two_years_ago.isoformat(),
            'initial_sync': True,
            'emails': processed_emails
        }

    def _sync_emails(self, max_results: int = 50, minutes: Optional[int] = None) -> Dict:
        """
        Sync emails from inbox, optionally filtered by a lookback window.

        Args:
            max_results: Maximum number of emails to fetch
            minutes: If set, only fetch emails from the last N minutes

        Returns:
            Dict with sync statistics
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please connect Gmail first.")

        if minutes is not None:
            after_ts = int((datetime.now() - timedelta(minutes=minutes)).timestamp())
            query = f'after:{after_ts} in:inbox -in:spam -in:trash'
        else:
            query = 'in:inbox -in:spam -in:trash'
        
        # Fetch emails
        emails = self._fetch_emails(query, max_results)
        
        # Convert to text format
        processed_emails = []
        for email in emails:
            try:
                email_data = self._email_to_structured_data(email)
                processed_emails.append(email_data)
            except Exception as e:
                logger.warning(f"Error processing email {email.get('id')}: {e}")
                continue
        
        # Update config with sync stats
        config = self._load_config()
        config['last_sync'] = datetime.now().isoformat()
        config['email_count'] = len(processed_emails)
        config['total_emails_processed'] = config.get('total_emails_processed', 0) + len(processed_emails)
        self._save_config(config)
        
        return {
            'success': True,
            'emails_fetched': len(emails),
            'emails_processed': len(processed_emails),
            'emails': processed_emails
        }
    
    def fetch_recent_emails(self, days: int = 7, max_results: int = 50) -> List[Dict]:
        """
        Fetch recent emails from last N days.
        
        Args:
            days: Number of days to look back
            max_results: Maximum emails to fetch
            
        Returns:
            List of email dicts with content and metadata
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please connect Gmail first.")
        
        # Build query for last N days - all inbox emails
        start_date = datetime.now() - timedelta(days=days)
        query = f'after:{start_date.strftime("%Y/%m/%d")} in:inbox -in:spam -in:trash'
        
        # Fetch emails
        emails = self._fetch_emails(query, max_results)
        
        # Convert to text
        processed_emails = []
        for email in emails:
            try:
                email_data = self._email_to_structured_data(email)
                processed_emails.append(email_data)
            except Exception as e:
                logger.warning(f"Error processing email {email.get('id')}: {e}")
                continue
        
        return processed_emails
    
    def _get_status_data(self) -> Dict:
        """
        Get Gmail connector status data.
        
        Returns:
            Status dict with connection info and stats
        """
        if not self.is_authenticated():
            return {'connected': False}
        
        # Get user profile
        try:
            creds = self.get_credentials()
            service = self._get_service(creds)
            profile = service.users().getProfile(userId='me').execute()
            
            # Load config
            config = self._load_config()
            
            return {
                'connected': True,
                'email': profile['emailAddress'],
                'lastSync': config.get('last_sync'),
                'emailCount': config.get('email_count', 0),
                'totalProcessed': config.get('total_emails_processed', 0),
                'connectedAt': config.get('connected_at')
            }
        except Exception as e:
            logger.warning(f"Error getting Gmail status: {e}")
            return {'connected': False, 'error': str(e)}
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _get_service(self, credentials: Optional[Credentials] = None):
        """Get or create Gmail API service."""
        if self._service is None:
            if credentials is None:
                credentials = self.get_credentials()
            if credentials is None:
                raise Exception("No valid credentials available")
            self._service = build('gmail', 'v1', credentials=credentials)
        return self._service
    
    def _fetch_emails(self, query: str, max_results: int) -> List[Dict]:
        """
        Fetch emails matching query.
        
        Args:
            query: Gmail search query
            max_results: Maximum emails to fetch
            
        Returns:
            List of full email objects
        """
        logger.debug(f"[Gmail API] query={query!r} max_results={max_results}")

        emails = []
        service = self._get_service()

        try:
            # List message IDs
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            result_size_estimate = results.get('resultSizeEstimate', 0)
            logger.info(f"[Gmail API] {len(messages)} message IDs (estimate: {result_size_estimate})")

            if len(messages) == 0:
                logger.info("[Gmail API] No messages found matching the query")
                return []

            # Fetch full message for each ID
            for i, msg in enumerate(messages, 1):
                try:
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    emails.append(message)
                    if i % 10 == 0:
                        logger.debug(f"[Gmail API] Fetched {i}/{len(messages)} emails")
                except HttpError as e:
                    logger.warning(f"[Gmail API] Error fetching message {msg['id']}: {e}")
                    continue

            logger.info(f"[Gmail API] Fetched {len(emails)} complete emails")

        except HttpError as e:
            logger.error(f"[Gmail API] HTTP error: {e.resp.status} - {e.reason}")
        except Exception as e:
            logger.exception(f"[Gmail API] Unexpected error: {e}")

        return emails
    
    def _email_to_structured_data(self, email: Dict) -> Dict:
        """
        Convert Gmail API email to simple text format for ingestion.
        
        Args:
            email: Gmail API message object
            
        Returns:
            Dict with simple text content and minimal metadata
        """
        # Extract headers
        headers = email['payload']['headers']
        subject = self._get_header(headers, 'Subject') or '(No Subject)'
        from_addr = self._get_header(headers, 'From') or '(Unknown)'
        to_addr = self._get_header(headers, 'To') or '(Unknown)'
        date_str = self._get_header(headers, 'Date') or '(Unknown)'
        
        # Extract body
        body = self._get_email_body(email['payload'])
        
        # Gmail URL
        gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{email['id']}"
        
        # Format as simple text (like a .txt file)
        text_content = f"""Subject: {subject}
From: {from_addr}
To: {to_addr}
Date: {date_str}

{body}

---
Gmail URL: {gmail_url}
"""
        
        # Return simple format for ingestion
        return {
            'text': text_content,
            'metadata': {
                'platform': 'Gmail',
                'timestamp': date_str,
                'url': gmail_url,
                'quote': subject,
                'source': f"Gmail/{email['id']}",
                'type': 'email',
                'from': from_addr,
                'to': to_addr
            }
        }
    
    def _get_email_body(self, payload: Dict) -> str:
        """
        Extract email body from payload.
        
        Handles multipart messages and HTML conversion.
        """
        # Check for simple body
        if 'body' in payload and payload['body'].get('data'):
            data = payload['body']['data']
            text = self._decode_base64(data)
            
            # Convert HTML to plain text if needed
            if payload.get('mimeType') == 'text/html':
                text = self._html_to_text(text)
            
            return text
        
        # Handle multipart
        if 'parts' in payload:
            parts = payload['parts']
            
            # Try plain text part first
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part.get('body', {}):
                        return self._decode_base64(part['body']['data'])
            
            # Fallback to HTML part
            for part in parts:
                if part['mimeType'] == 'text/html':
                    if 'data' in part.get('body', {}):
                        html_content = self._decode_base64(part['body']['data'])
                        return self._html_to_text(html_content)
            
            # Recursively check nested multipart
            for part in parts:
                if 'parts' in part:
                    body = self._get_email_body(part)
                    if body and body != "(No content)":
                        return body
        
        return "(No content)"
    
    def _decode_base64(self, data: str) -> str:
        """Decode base64 URL-safe encoded data."""
        try:
            # Gmail uses URL-safe base64
            decoded = base64.urlsafe_b64decode(data)
            return decoded.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Error decoding base64: {e}")
            return "(Error decoding content)"
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        try:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.ignore_emphasis = False
            return h.handle(html)
        except Exception as e:
            logger.warning(f"Error converting HTML: {e}")
            return html
    
    def _get_header(self, headers: List[Dict], name: str) -> Optional[str]:
        """Get header value by name (case-insensitive)."""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return None
    
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
        """Load connector configuration (legacy Gmail config)."""
        if self.gmail_config_file.exists():
            with open(self.gmail_config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_config(self, config: Dict):
        """Save connector configuration (legacy Gmail config)."""
        self.gmail_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.gmail_config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _get_client_config(self) -> Dict:
        """
        Get OAuth client configuration from environment variables or file.
        
        Priority:
        1. GMAIL_CLIENT_CONFIG (entire JSON as string)
        2. Individual env vars (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, etc.)
        3. JSON file (gmail_client_secret.json)
        
        Returns:
            Client configuration dict for OAuth flow
            
        Raises:
            ValueError: If neither environment variables nor file are available
        """
        # Option 0: Check user-stored OAuth app credentials
        oauth_app_file = self.config_dir / 'oauth_app.json'
        if oauth_app_file.exists():
            with open(oauth_app_file) as f:
                stored = json.load(f)
            if stored.get('client_id') and stored.get('client_secret'):
                return {
                    "installed": {
                        "client_id": stored['client_id'],
                        "project_id": stored.get('project_id', 'localbrain'),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_secret": stored['client_secret'],
                        "redirect_uris": ["http://localhost"]
                    }
                }

        # Option 1: Try full JSON config from environment variable
        json_config = os.getenv('GMAIL_CLIENT_CONFIG')
        if json_config:
            try:
                return json.loads(json_config)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in GMAIL_CLIENT_CONFIG: {e}")

        # Option 2: Try individual environment variables
        client_id = os.getenv('GMAIL_CLIENT_ID')
        client_secret = os.getenv('GMAIL_CLIENT_SECRET')
        project_id = os.getenv('GMAIL_PROJECT_ID', 'localbrain')
        
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
        
        # Option 3: Fallback to JSON file
        if self.client_secrets_file.exists():
            with open(self.client_secrets_file, 'r') as f:
                return json.load(f)
        
        # Neither available
        raise ValueError(
            "Gmail OAuth credentials not configured.\n\n"
            "Please either:\n"
            "1. Set GMAIL_CLIENT_CONFIG with entire JSON:\n"
            '   GMAIL_CLIENT_CONFIG=\'{"installed":{...}}\'\n\n'
            "2. Set individual environment variables:\n"
            "   GMAIL_CLIENT_ID=your_client_id\n"
            "   GMAIL_CLIENT_SECRET=your_client_secret\n"
            "   GMAIL_PROJECT_ID=your_project_id (optional)\n\n"
            "3. Or place gmail_client_secret.json at:\n"
            f"   {self.client_secrets_file}"
        )

