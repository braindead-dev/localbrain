"""
Connector Manager

Discovers, loads, and manages connector plugins dynamically.
Provides a unified interface for interacting with all connectors.
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type
from datetime import datetime

from .base_connector import BaseConnector, ConnectorMetadata, ConnectorStatus, SyncResult


class ConnectorManager:
    """
    Manages all connector plugins.
    
    Automatically discovers connectors in the connectors directory,
    provides a unified API for interacting with them, and handles
    lifecycle management.
    """
    
    def __init__(self, connectors_dir: Optional[Path] = None, vault_path: Optional[Path] = None):
        """
        Initialize connector manager.
        
        Args:
            connectors_dir: Directory containing connector plugins
            vault_path: Path to LocalBrain vault
        """
        if connectors_dir is None:
            # Default to src/connectors directory
            connectors_dir = Path(__file__).parent
        
        self.connectors_dir = Path(connectors_dir)
        self.vault_path = vault_path
        
        # Registry of available connectors
        self._registry: Dict[str, Type[BaseConnector]] = {}
        
        # Active connector instances
        self._instances: Dict[str, BaseConnector] = {}
        
        # Discover and load connectors
        self._discover_connectors()
    
    def _discover_connectors(self):
        """
        Discover all connector plugins in the connectors directory.
        
        Looks for subdirectories containing a connector class that
        inherits from BaseConnector.
        """
        if not self.connectors_dir.exists():
            return
        
        for item in self.connectors_dir.iterdir():
            if not item.is_dir():
                continue
            
            # Skip special directories
            if item.name.startswith('_') or item.name.startswith('.'):
                continue
            
            # Look for connector module
            connector_file = item / f"{item.name}_connector.py"
            if not connector_file.exists():
                continue
            
            try:
                # Import the connector module
                module_path = f"connectors.{item.name}.{item.name}_connector"
                module = importlib.import_module(module_path)
                
                # Find BaseConnector subclasses in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseConnector) and 
                        obj is not BaseConnector and
                        obj.__module__ == module.__name__):
                        
                        # Create temp instance to get metadata
                        temp_instance = obj(vault_path=self.vault_path)
                        metadata = temp_instance.get_metadata()
                        
                        # Register connector
                        self._registry[metadata.id] = obj
                        print(f"✅ Discovered connector: {metadata.name} ({metadata.id})")
                        break
                        
            except Exception as e:
                print(f"⚠️  Failed to load connector from {item.name}: {e}")
                continue
    
    def list_connectors(self) -> List[ConnectorMetadata]:
        """
        List all available connectors.
        
        Returns:
            List of connector metadata
        """
        metadata_list = []
        for connector_class in self._registry.values():
            try:
                temp_instance = connector_class(vault_path=self.vault_path)
                metadata_list.append(temp_instance.get_metadata())
            except Exception:
                continue
        
        return metadata_list
    
    def get_connector(self, connector_id: str) -> Optional[BaseConnector]:
        """
        Get or create a connector instance.
        
        Args:
            connector_id: Unique connector identifier
        
        Returns:
            Connector instance or None if not found
        """
        # Return existing instance if available
        if connector_id in self._instances:
            return self._instances[connector_id]
        
        # Create new instance
        if connector_id not in self._registry:
            return None
        
        try:
            connector_class = self._registry[connector_id]
            instance = connector_class(vault_path=self.vault_path)
            self._instances[connector_id] = instance
            return instance
        except Exception as e:
            print(f"Error creating connector instance for {connector_id}: {e}")
            return None
    
    def get_status(self, connector_id: str) -> Optional[ConnectorStatus]:
        """
        Get status of a specific connector.
        
        Args:
            connector_id: Connector identifier
        
        Returns:
            ConnectorStatus or None if connector not found
        """
        connector = self.get_connector(connector_id)
        if not connector:
            return None
        
        try:
            return connector.get_status()
        except Exception as e:
            return ConnectorStatus(
                connected=False,
                authenticated=False,
                last_error=str(e)
            )
    
    def sync_connector(self, 
                      connector_id: str,
                      auto_ingest: bool = True,
                      limit: Optional[int] = None) -> Optional[SyncResult]:
        """
        Trigger sync for a specific connector.
        
        Args:
            connector_id: Connector identifier
            auto_ingest: Whether to automatically ingest fetched data
            limit: Maximum number of items to sync
        
        Returns:
            SyncResult or None if connector not found
        """
        connector = self.get_connector(connector_id)
        if not connector:
            return None
        
        try:
            return connector.sync(auto_ingest=auto_ingest, limit=limit)
        except Exception as e:
            return SyncResult(
                success=False,
                errors=[str(e)]
            )
    
    def sync_all(self, auto_ingest: bool = True) -> Dict[str, SyncResult]:
        """
        Sync all connected connectors.
        
        Args:
            auto_ingest: Whether to automatically ingest fetched data
        
        Returns:
            Dictionary mapping connector_id to SyncResult
        """
        results = {}
        
        for connector_id in self._registry.keys():
            # Check if connector is connected
            status = self.get_status(connector_id)
            if not status or not status.connected:
                continue
            
            # Sync
            result = self.sync_connector(
                connector_id=connector_id,
                auto_ingest=auto_ingest
            )
            
            if result:
                results[connector_id] = result
        
        return results
    
    def authenticate(self, 
                    connector_id: str,
                    credentials: Dict) -> tuple[bool, Optional[str]]:
        """
        Authenticate a connector.
        
        Args:
            connector_id: Connector identifier
            credentials: Authentication credentials
        
        Returns:
            (success, error_message)
        """
        connector = self.get_connector(connector_id)
        if not connector:
            return False, f"Connector {connector_id} not found"
        
        try:
            return connector.authenticate(credentials)
        except Exception as e:
            return False, str(e)
    
    def revoke_access(self, connector_id: str) -> bool:
        """
        Revoke access for a connector.
        
        Args:
            connector_id: Connector identifier
        
        Returns:
            True if successful
        """
        connector = self.get_connector(connector_id)
        if not connector:
            return False
        
        try:
            success = connector.revoke_access()
            
            # Remove from instances cache
            if connector_id in self._instances:
                del self._instances[connector_id]
            
            return success
        except Exception:
            return False


# Global connector manager instance
_manager: Optional[ConnectorManager] = None


def get_connector_manager(vault_path: Optional[Path] = None) -> ConnectorManager:
    """
    Get the global connector manager instance.
    
    Args:
        vault_path: Path to LocalBrain vault (only used on first call)
    
    Returns:
        ConnectorManager singleton
    """
    global _manager
    
    if _manager is None:
        _manager = ConnectorManager(vault_path=vault_path)
    
    return _manager
