"""
Authentication and Authorization for MCP Server

Implements ACL (Access Control List) system for tool permissions,
client authentication, and rate limiting.
"""

import os
import json
import hashlib
import secrets
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger

from .models import MCPClientAuth, MCPPermission


class MCPAuthManager:
    """
    Manages authentication and authorization for MCP clients.

    Features:
    - API key-based authentication
    - Per-tool permissions
    - Scope restrictions (directory, file type filters)
    - Rate limiting per client
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize authentication manager.

        Args:
            config_path: Path to clients config file (JSON)
        """
        self.config_path = Path(config_path) if config_path else None
        self.clients: Dict[str, MCPClientAuth] = {}
        self.rate_limiter: Dict[str, List[datetime]] = defaultdict(list)

        # Load clients from config
        if self.config_path and self.config_path.exists():
            self._load_clients()
        else:
            logger.warning("No auth config found, using permissive defaults")
            self._init_default_clients()

    def _load_clients(self):
        """Load client configurations from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            for client_data in data.get('clients', []):
                client = MCPClientAuth(**client_data)
                self.clients[client.api_key] = client

            logger.info(f"Loaded {len(self.clients)} MCP clients")
        except Exception as e:
            logger.error(f"Failed to load auth config: {e}")
            self._init_default_clients()

    def _init_default_clients(self):
        """Initialize with default permissive client for development."""
        default_key = os.getenv("MCP_API_KEY", "dev-key-local-only")

        default_client = MCPClientAuth(
            client_id="local_dev",
            api_key=default_key,
            permissions=[
                MCPPermission(tool="search", allowed=True),
                MCPPermission(tool="search_agentic", allowed=True),
                MCPPermission(tool="open", allowed=True),
                MCPPermission(tool="summarize", allowed=True),
                MCPPermission(tool="list", allowed=True),
            ],
            rate_limit=1000,  # High limit for dev
            enabled=True
        )

        self.clients[default_key] = default_client
        logger.info("Initialized default MCP client for development")

    def authenticate(self, api_key: str) -> Optional[MCPClientAuth]:
        """
        Authenticate client by API key.

        Args:
            api_key: Client API key

        Returns:
            MCPClientAuth if valid, None otherwise
        """
        client = self.clients.get(api_key)

        if not client:
            logger.warning(f"Authentication failed: invalid API key")
            return None

        if not client.enabled:
            logger.warning(f"Authentication failed: client {client.client_id} disabled")
            return None

        return client

    def check_permission(self, client: MCPClientAuth, tool: str) -> tuple[bool, Optional[str]]:
        """
        Check if client has permission to use tool.

        Args:
            client: Authenticated client
            tool: Tool name

        Returns:
            Tuple of (allowed, error_message)
        """
        for perm in client.permissions:
            if perm.tool == tool:
                if perm.allowed:
                    return True, None
                else:
                    return False, f"Permission denied: tool '{tool}' not allowed"

        # Tool not in permission list = denied
        return False, f"Permission denied: tool '{tool}' not configured"

    def check_rate_limit(self, client: MCPClientAuth) -> tuple[bool, Optional[str]]:
        """
        Check if client has exceeded rate limit.

        Args:
            client: Authenticated client

        Returns:
            Tuple of (allowed, error_message)
        """
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)

        # Get request history for this client
        requests = self.rate_limiter[client.client_id]

        # Remove old requests (> 1 hour ago)
        requests = [r for r in requests if r > hour_ago]
        self.rate_limiter[client.client_id] = requests

        # Check limit
        if len(requests) >= client.rate_limit:
            return False, f"Rate limit exceeded: {client.rate_limit} requests per hour"

        # Add current request
        requests.append(now)

        return True, None

    def check_scope_restriction(
        self,
        client: MCPClientAuth,
        tool: str,
        request_params: Dict
    ) -> tuple[bool, Optional[str]]:
        """
        Check if request parameters comply with scope restrictions.

        Args:
            client: Authenticated client
            tool: Tool name
            request_params: Request parameters to validate

        Returns:
            Tuple of (allowed, error_message)
        """
        # Find permission for this tool
        perm = None
        for p in client.permissions:
            if p.tool == tool:
                perm = p
                break

        if not perm or not perm.scope_restrictions:
            return True, None  # No restrictions

        restrictions = perm.scope_restrictions

        # Check allowed directories
        if 'allowed_directories' in restrictions:
            allowed_dirs = restrictions['allowed_directories']
            file_path = request_params.get('file_path') or request_params.get('path')

            if file_path:
                # Check if file_path is within allowed directories
                if not any(file_path.startswith(d) for d in allowed_dirs):
                    return False, f"Access denied: path '{file_path}' not in allowed directories"

        # Check allowed file types
        if 'allowed_file_types' in restrictions:
            allowed_types = restrictions['allowed_file_types']
            file_path = request_params.get('file_path')

            if file_path and '.' in file_path:
                ext = file_path.split('.')[-1]
                if ext not in allowed_types:
                    return False, f"Access denied: file type '{ext}' not allowed"

        # Check max_results restriction
        if 'max_results' in restrictions:
            max_results = restrictions['max_results']
            top_k = request_params.get('top_k')

            if top_k and top_k > max_results:
                return False, f"Request exceeds max_results: {max_results}"

        return True, None

    @staticmethod
    def generate_api_key(client_id: str) -> str:
        """
        Generate a secure API key.

        Args:
            client_id: Client identifier

        Returns:
            Generated API key
        """
        # Combine random bytes with client_id for uniqueness
        random_part = secrets.token_urlsafe(32)
        combined = f"{client_id}:{random_part}"
        hash_part = hashlib.sha256(combined.encode()).hexdigest()[:16]

        return f"lb_{hash_part}_{random_part}"

    def add_client(self, client: MCPClientAuth) -> bool:
        """
        Add new client to auth manager.

        Args:
            client: Client configuration

        Returns:
            True if added successfully
        """
        if client.api_key in self.clients:
            logger.warning(f"Client with API key already exists")
            return False

        self.clients[client.api_key] = client
        logger.info(f"Added new MCP client: {client.client_id}")

        # Save to config if path is set
        if self.config_path:
            self._save_clients()

        return True

    def remove_client(self, api_key: str) -> bool:
        """
        Remove client from auth manager.

        Args:
            api_key: API key of client to remove

        Returns:
            True if removed successfully
        """
        if api_key not in self.clients:
            return False

        client_id = self.clients[api_key].client_id
        del self.clients[api_key]
        logger.info(f"Removed MCP client: {client_id}")

        # Save to config
        if self.config_path:
            self._save_clients()

        return True

    def _save_clients(self):
        """Save clients configuration to JSON file."""
        try:
            data = {
                "clients": [
                    client.dict() for client in self.clients.values()
                ]
            }

            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved {len(self.clients)} clients to config")
        except Exception as e:
            logger.error(f"Failed to save auth config: {e}")


# ============================================================================
# FastAPI Dependency for Authentication
# ============================================================================

def get_current_client(
    auth_manager: MCPAuthManager,
    api_key: str
) -> MCPClientAuth:
    """
    FastAPI dependency to get authenticated client.

    Args:
        auth_manager: Auth manager instance
        api_key: API key from request header

    Returns:
        Authenticated client

    Raises:
        HTTPException if authentication fails
    """
    from fastapi import HTTPException, status

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    client = auth_manager.authenticate(api_key)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Check rate limit
    allowed, error = auth_manager.check_rate_limit(client)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error
        )

    return client
