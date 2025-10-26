"""
Base Connector Interface

Defines the standardized interface that all LocalBrain connectors must implement.
This enables a plugin-style architecture where connectors can be dynamically loaded.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ConnectorMetadata:
    """Connector metadata for discovery and UI display."""
    id: str                              # Unique identifier (e.g., "gmail", "discord")
    name: str                            # Display name (e.g., "Gmail", "Discord")
    description: str                     # Short description
    version: str                         # Connector version
    author: str                          # Connector author
    icon_url: Optional[str] = None       # Icon for UI
    auth_type: str = "none"              # Auth type: "oauth", "api_key", "token", "none"
    requires_config: bool = False        # Whether connector needs user configuration
    sync_interval_minutes: int = 10      # Default sync interval
    capabilities: List[str] = field(default_factory=list)  # e.g., ["read", "write", "realtime"]


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    items_fetched: int = 0
    items_ingested: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_sync_timestamp: Optional[datetime] = None


@dataclass
class ConnectorStatus:
    """Current status of a connector."""
    connected: bool
    authenticated: bool
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    total_items_synced: int = 0
    config_valid: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorData:
    """Standardized data format returned by connectors."""
    content: str                         # Main text content
    source_id: str                       # Unique identifier from source (e.g., email ID)
    timestamp: datetime                  # When content was created
    metadata: Dict[str, Any]             # Source-specific metadata
    
    # Common metadata fields (optional, but recommended):
    # - platform: str (e.g., "gmail", "discord")
    # - type: str (e.g., "email", "message", "dm")
    # - author: str
    # - title: str
    # - url: str
    # - thread_id: str
    # - channel_id: str


class BaseConnector(ABC):
    """
    Base class for all LocalBrain connectors.
    
    Connectors are plugins that fetch data from external sources and convert
    it into a standardized format for ingestion.
    
    Required Methods:
        - get_metadata(): Return connector metadata
        - has_updates(): Check if new data is available
        - fetch_updates(): Fetch new data since last sync
        - get_status(): Return current connection status
    
    Optional Methods:
        - validate_config(): Validate user configuration
        - authenticate(): Handle authentication flow
        - revoke_access(): Disconnect and remove credentials
    """
    
    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        """
        Initialize connector.
        
        Args:
            vault_path: Path to LocalBrain vault (for ingestion)
            config_dir: Directory for storing connector config (default: ~/.localbrain/connectors/<id>)
        """
        self.vault_path = vault_path
        
        # Set up config directory
        if config_dir is None:
            metadata = self.get_metadata()
            config_dir = Path.home() / '.localbrain' / 'connectors' / metadata.id
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # State file for tracking last sync, etc.
        self.state_file = self.config_dir / 'state.json'
    
    # ========================================================================
    # Required Methods (must implement)
    # ========================================================================
    
    @abstractmethod
    def get_metadata(self) -> ConnectorMetadata:
        """
        Return connector metadata.
        
        This is used for connector discovery, UI display, and routing.
        """
        pass
    
    @abstractmethod
    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """
        Check if there are new updates available.
        
        Args:
            since: Check for updates since this timestamp (None = check for any updates)
        
        Returns:
            True if updates are available, False otherwise
        """
        pass
    
    @abstractmethod
    def fetch_updates(self, 
                     since: Optional[datetime] = None,
                     limit: Optional[int] = None) -> List[ConnectorData]:
        """
        Fetch new data since last sync.
        
        Args:
            since: Fetch updates since this timestamp (None = fetch all)
            limit: Maximum number of items to fetch (None = no limit)
        
        Returns:
            List of ConnectorData objects ready for ingestion
        """
        pass
    
    @abstractmethod
    def get_status(self) -> ConnectorStatus:
        """
        Get current connector status.
        
        Returns:
            ConnectorStatus with connection info, last sync, errors, etc.
        """
        pass
    
    # ========================================================================
    # Optional Methods (provide defaults)
    # ========================================================================
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate connector configuration.
        
        Args:
            config: Configuration dictionary to validate
        
        Returns:
            (is_valid, error_message)
        """
        return True, None
    
    def authenticate(self, credentials: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Handle authentication (if required).
        
        Args:
            credentials: Authentication credentials
        
        Returns:
            (success, error_message)
        """
        return True, None
    
    def revoke_access(self) -> bool:
        """
        Revoke access and remove stored credentials.
        
        Returns:
            True if successful
        """
        return True
    
    def sync(self, 
             auto_ingest: bool = False,
             limit: Optional[int] = None) -> SyncResult:
        """
        Main sync method - checks for updates and fetches them.
        
        Args:
            auto_ingest: If True, automatically ingest fetched data
            limit: Maximum number of items to sync
        
        Returns:
            SyncResult with statistics
        """
        try:
            # Get last sync timestamp
            last_sync = self._get_last_sync()
            
            # Check for updates
            if not self.has_updates(since=last_sync):
                return SyncResult(
                    success=True,
                    items_fetched=0,
                    items_ingested=0,
                    last_sync_timestamp=last_sync
                )
            
            # Fetch updates
            items = self.fetch_updates(since=last_sync, limit=limit)
            
            # Optionally ingest
            ingested_count = 0
            if auto_ingest and self.vault_path:
                ingested_count = self._ingest_data(items)
            
            # Update last sync timestamp
            now = datetime.now()
            self._save_last_sync(now)
            
            return SyncResult(
                success=True,
                items_fetched=len(items),
                items_ingested=ingested_count,
                last_sync_timestamp=now
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                errors=[str(e)]
            )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _get_last_sync(self) -> Optional[datetime]:
        """Get timestamp of last successful sync."""
        import json
        
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file) as f:
                state = json.load(f)
                last_sync_str = state.get('last_sync')
                if last_sync_str:
                    return datetime.fromisoformat(last_sync_str)
        except Exception:
            pass
        
        return None
    
    def _save_last_sync(self, timestamp: datetime):
        """Save last sync timestamp to state file."""
        import json
        
        state = {}
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
            except Exception:
                pass
        
        state['last_sync'] = timestamp.isoformat()
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _ingest_data(self, items: List[ConnectorData]) -> int:
        """
        Ingest data into LocalBrain via the ingestion API.
        
        Sends ConnectorData to the ingestion agent which will:
        1. Analyze and synthesize the data into insights
        2. Determine appropriate storage location and structure
        3. Connect it to existing knowledge in the vault
        
        Returns number of items successfully ingested.
        """
        if not items:
            return 0
        
        import requests
        
        metadata = self.get_metadata()
        ingested = 0
        
        for item in items:
            try:
                # Prepare ingestion payload
                ingestion_text = f"[Source: {metadata.name}] "
                ingestion_text += f"[Timestamp: {item.timestamp.isoformat()}] "
                ingestion_text += item.content
                
                # Add metadata as context
                if item.metadata:
                    ingestion_text += f"\n\nMetadata: {item.metadata}"
                
                # Call ingestion API
                # This will trigger the LLM-powered ingestion agent
                response = requests.post(
                    'http://127.0.0.1:8765/protocol/ingest',
                    json={
                        'text': ingestion_text,
                        'source': metadata.name,
                        'metadata': item.metadata,
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    ingested += 1
                else:
                    print(f"Ingestion API error for {item.source_id}: {response.text}")
                
            except Exception as e:
                # Log error but continue processing
                print(f"Error ingesting item {item.source_id}: {e}")
                continue
        
        return ingested
