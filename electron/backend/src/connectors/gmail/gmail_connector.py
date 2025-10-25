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


# OAuth 2.0 scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.labels'
]

# Redirect URI for OAuth callback
REDIRECT_URI = 'http://localhost:8765/connectors/gmail/auth/callback'


class GmailConnector:
    """
    Gmail connector for authenticating and fetching emails.
    
    Handles OAuth flow, token management, email retrieval, and text conversion.
    """
    
    def __init__(self, credentials_dir: Optional[Path] = None, vault_path: Optional[Path] = None):
        """
        Initialize Gmail connector.
        
        Args:
            credentials_dir: Directory to store OAuth credentials (default: ~/.localbrain/credentials)
            vault_path: Path to LocalBrain vault for ingestion
        """
        if credentials_dir is None:
            credentials_dir = Path.home() / '.localbrain' / 'credentials'
        
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.client_secrets_file = self.credentials_dir / 'gmail_client_secret.json'
        self.token_file = self.credentials_dir / 'gmail_token.json'
        self.config_file = self.credentials_dir / 'gmail_config.json'
        self.flow_state_file = self.credentials_dir / 'flow_state.json'
        
        # Vault path for ingestion
        self.vault_path = vault_path
        
        # Gmail service (initialized on first use)
        self._service = None
    
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
        config['email'] = profile['emailAddress']
        config['connected_at'] = datetime.now().isoformat()
        self._save_config(config)
        
        # Clean up flow state file
        if self.flow_state_file.exists():
            self.flow_state_file.unlink()
        
        return {
            'email': profile['emailAddress'],
            'connected': True
        }
    
    def revoke_access(self) -> bool:
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
    # Email Fetching Methods
    # ========================================================================
    
    def sync(self, max_results: int = 100, minutes: int = 10) -> Dict:
        """
        Sync emails from the last N minutes.
        
        Args:
            max_results: Maximum number of emails to fetch (default: 100)
            minutes: Fetch emails from last N minutes (default: 10)
            
        Returns:
            Dict with sync statistics
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please connect Gmail first.")
        
        # Calculate timestamp for N minutes ago
        time_ago = datetime.now() - timedelta(minutes=minutes)
        # Convert to Unix timestamp for Gmail API
        timestamp = int(time_ago.timestamp())
        
        # Build query - fetch emails from last N minutes in primary inbox
        query = f'after:{timestamp} in:inbox category:primary -in:spam -in:trash'
        
        # Fetch emails
        emails = self._fetch_emails(query, max_results)
        
        # Convert to text format
        processed_emails = []
        for email in emails:
            try:
                email_data = self._email_to_structured_data(email)
                processed_emails.append(email_data)
            except Exception as e:
                print(f"Error processing email {email.get('id')}: {e}")
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
            'time_window_minutes': minutes,
            'query_time': time_ago.isoformat(),
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
        
        # Build query for last N days - only primary inbox
        start_date = datetime.now() - timedelta(days=days)
        query = f'after:{start_date.strftime("%Y/%m/%d")} in:inbox category:primary -in:spam -in:trash'
        
        # Fetch emails
        emails = self._fetch_emails(query, max_results)
        
        # Convert to text
        processed_emails = []
        for email in emails:
            try:
                email_data = self._email_to_structured_data(email)
                processed_emails.append(email_data)
            except Exception as e:
                print(f"Error processing email {email.get('id')}: {e}")
                continue
        
        return processed_emails
    
    def get_status(self) -> Dict:
        """
        Get Gmail connector status.
        
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
            print(f"Error getting status: {e}")
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
            
            # Fetch full message for each ID
            for msg in messages:
                try:
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    emails.append(message)
                except HttpError as e:
                    print(f"Error fetching message {msg['id']}: {e}")
                    continue
        
        except HttpError as e:
            print(f"Error listing messages: {e}")
        
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
            print(f"Error decoding base64: {e}")
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
            print(f"Error converting HTML: {e}")
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
        """Load connector configuration."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_config(self, config: Dict):
        """Save connector configuration."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
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

