"""
Browser History Connector for LocalBrain

Ingests browsing history from Chromium-based browsers (Chrome, Edge, Brave, etc.)
"""

import sqlite3
import shutil
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from ..base_connector import BaseConnector, ConnectorMetadata, ConnectorData, ConnectorStatus

logger = logging.getLogger(__name__)


class BrowserConnector(BaseConnector):
    """Connector for Chromium browser history"""
    
    # Connector metadata
    CONNECTOR_ID = "browser"
    CONNECTOR_NAME = "Browser History"
    CONNECTOR_DESCRIPTION = "Sync and search browsing history from Chromium-based browsers"
    CONNECTOR_VERSION = "1.0.0"
    
    # Auth and capabilities
    AUTH_TYPE = "path"
    REQUIRES_CONFIG = True
    CAPABILITIES = ["sync", "search"]
    
    # Default browser history paths
    DEFAULT_PATHS = {
        "chrome": "~/Library/Application Support/Google/Chrome/Default/History",
        "edge": "~/Library/Application Support/Microsoft Edge/Default/History",
        "brave": "~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History",
    }
    
    def __init__(self, vault_path: Optional[Path] = None, config_dir: Optional[Path] = None):
        super().__init__(vault_path, config_dir)
        self.history_path: Optional[str] = None
        self.browser_name: str = "Chrome"
        self.credentials_file = self.config_dir / 'credentials.json'
    
    def _save_credentials(self, credentials: Dict[str, Any]):
        """Save credentials to file"""
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
    
    def _load_credentials(self) -> Optional[Dict[str, Any]]:
        """Load credentials from file"""
        if self.credentials_file.exists():
            with open(self.credentials_file, 'r') as f:
                return json.load(f)
        return None
    
    def _delete_credentials(self):
        """Delete credentials file"""
        if self.credentials_file.exists():
            self.credentials_file.unlink()
    
    def _load_state(self) -> Optional[Dict[str, Any]]:
        """Load state from file"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return None
    
    def _save_state(self, state: Dict[str, Any]):
        """Save state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def get_metadata(self) -> ConnectorMetadata:
        """Return connector metadata"""
        return ConnectorMetadata(
            id=self.CONNECTOR_ID,
            name=self.CONNECTOR_NAME,
            description=self.CONNECTOR_DESCRIPTION,
            version=self.CONNECTOR_VERSION,
            author="LocalBrain",
            auth_type=self.AUTH_TYPE,
            requires_config=self.REQUIRES_CONFIG,
            capabilities=self.CAPABILITIES,
        )
        
    def authenticate(self, credentials: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Set up browser history path
        
        Args:
            credentials: Dict with 'history_path' or 'browser' key
        """
        try:
            # Check if user provided a path
            if "history_path" in credentials:
                path = os.path.expanduser(credentials["history_path"])
                if os.path.exists(path):
                    self.history_path = path
                    self.browser_name = credentials.get("browser_name", "Custom")
                    self._save_credentials({"history_path": path, "browser_name": self.browser_name})
                    logger.info(f"Browser history path set to: {path}")
                    return True, None
                else:
                    logger.error(f"History file not found: {path}")
                    return False, f"History file not found: {path}"
            
            # Auto-detect browser
            elif "browser" in credentials:
                browser = credentials["browser"].lower()
                if browser in self.DEFAULT_PATHS:
                    path = os.path.expanduser(self.DEFAULT_PATHS[browser])
                    if os.path.exists(path):
                        self.history_path = path
                        self.browser_name = browser.capitalize()
                        self._save_credentials({"history_path": path, "browser_name": self.browser_name})
                        logger.info(f"Auto-detected {browser} history: {path}")
                        return True, None
                    else:
                        logger.error(f"{browser} history not found at: {path}")
                        return False, f"{browser} history not found at: {path}"
            
            # Try auto-detect all browsers
            for browser, default_path in self.DEFAULT_PATHS.items():
                path = os.path.expanduser(default_path)
                if os.path.exists(path):
                    self.history_path = path
                    self.browser_name = browser.capitalize()
                    self._save_credentials({"history_path": path, "browser_name": self.browser_name})
                    logger.info(f"Auto-detected {browser} history: {path}")
                    return True, None
            
            logger.error("No browser history found. Please provide history_path.")
            return False, "No browser history found. Please provide history_path."
            
        except Exception as e:
            logger.error(f"Browser authentication failed: {e}")
            return False, str(e)
    
    def is_authenticated(self) -> bool:
        """Check if browser history path is configured"""
        if not self.history_path:
            creds = self._load_credentials()
            if creds and "history_path" in creds:
                self.history_path = creds["history_path"]
                self.browser_name = creds.get("browser_name", "Chrome")
        
        return self.history_path is not None and os.path.exists(self.history_path)
    
    def revoke_access(self) -> bool:
        """Remove stored browser path"""
        try:
            self._delete_credentials()
            self.history_path = None
            self.browser_name = "Chrome"
            logger.info("Browser history path removed")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke browser access: {e}")
            return False
    
    def has_updates(self, since: Optional[datetime] = None) -> bool:
        """Check if there are new URLs since last check"""
        return True  # Browser history always has potential updates
    
    def fetch_updates(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[ConnectorData]:
        """Fetch browser history updates and format for ingestion"""
        hours = 24 if since is None else int((datetime.now() - since).total_seconds() / 3600)
        result = self._fetch_history(limit=limit or 100, hours=hours)
        
        if not result.get("success"):
            return []
        
        # Convert to ConnectorData format for ingestion agent
        # The ingestion agent will synthesize this into insights
        items = []
        for item in result.get("items", []):
            # Natural language format for ingestion
            content = f"Visited: {item['title']} at {item['url']} on {item['last_visit']}. "
            content += f"Visit count: {item['visit_count']}. "
            
            # Extract domain for categorization
            from urllib.parse import urlparse
            domain = urlparse(item['url']).netloc
            content += f"Domain: {domain}."
            
            items.append(ConnectorData(
                content=content,
                source_id=item['url'],
                timestamp=datetime.fromisoformat(item['timestamp']),
                metadata={
                    "source": "browser_history",
                    "browser": self.browser_name,
                    "url": item['url'],
                    "title": item['title'],
                    "domain": domain,
                    "visit_count": item['visit_count'],
                },
            ))
        return items
    
    def get_status(self) -> ConnectorStatus:
        """Get connector status"""
        authenticated = self.is_authenticated()
        
        state = self._load_state()
        last_sync = None
        if state and 'last_sync' in state:
            last_sync = datetime.fromisoformat(state['last_sync'])
        
        return ConnectorStatus(
            connected=authenticated,
            authenticated=authenticated,
            last_sync=last_sync,
            last_error=None,
            total_items_synced=state.get('total_items_synced', 0) if state else 0,
        )
    
    def _fetch_history(self, limit: int = 100, hours: int = 24) -> Dict[str, Any]:
        """
        Fetch recent browser history from SQLite database
        
        Args:
            limit: Maximum number of URLs to fetch
            hours: Look back this many hours
        
        Returns:
            Dict with success, count, items, browser
        """
        if not self.is_authenticated():
            raise Exception("Browser not configured. Please authenticate first.")
        
        try:
            # Copy history file to temp location (Chrome locks the original)
            temp_path = "/tmp/localbrain_browser_history.db"
            shutil.copy2(self.history_path, temp_path)
            
            # Query history
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            # Calculate time threshold (Chrome uses microseconds since 1601-01-01)
            chrome_epoch = datetime(1601, 1, 1)
            time_threshold = datetime.now() - timedelta(hours=hours)
            threshold_microseconds = int((time_threshold - chrome_epoch).total_seconds() * 1_000_000)
            
            # Query recent URLs
            query = """
                SELECT url, title, visit_count, last_visit_time
                FROM urls
                WHERE last_visit_time > ?
                ORDER BY last_visit_time DESC
                LIMIT ?
            """
            
            cursor.execute(query, (threshold_microseconds, limit))
            rows = cursor.fetchall()
            conn.close()
            
            # Clean up temp file
            os.remove(temp_path)
            
            # Format results
            history_items = []
            for url, title, visit_count, last_visit_time in rows:
                # Convert Chrome timestamp to Python datetime
                visit_datetime = chrome_epoch + timedelta(microseconds=last_visit_time)
                
                history_items.append({
                    "url": url,
                    "title": title or url,
                    "visit_count": visit_count,
                    "last_visit": visit_datetime.isoformat(),
                    "timestamp": visit_datetime.isoformat(),
                })
            
            logger.info(f"Retrieved {len(history_items)} URLs from {self.browser_name}")
            return {
                "success": True,
                "count": len(history_items),
                "items": history_items,
                "browser": self.browser_name,
            }
            
        except Exception as e:
            logger.error(f"Browser history sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "count": 0,
                "items": [],
            }
    
# Register connector
def get_connector_class():
    """Return the connector class for registration"""
    return BrowserConnector
