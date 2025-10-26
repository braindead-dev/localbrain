"""
MCP Tools Implementation - Proxy Layer

Forwards MCP tool requests to the LocalBrain daemon.py backend.
Acts as a thin wrapper that translates MCP protocol to daemon API calls.
"""

import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from .models import (
    SearchRequest, OpenRequest,
    IngestRequest, ListRequest,
    SearchResponse, OpenResponse, IngestResponse, ListResponse,
    SearchResult, FileMetadata, ListItem
)


class MCPTools:
    """
    MCP Tools proxy layer.

    Forwards all tool requests to the LocalBrain daemon backend.
    """

    def __init__(
        self,
        daemon_url: str = "http://127.0.0.1:8765",
        timeout: float = 30.0
    ):
        """
        Initialize MCP tools proxy.

        Args:
            daemon_url: URL of the LocalBrain daemon backend
            timeout: HTTP request timeout in seconds
        """
        self.daemon_url = daemon_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

        logger.info(f"MCPTools proxy initialized, forwarding to daemon: {self.daemon_url}")

    # ========================================================================
    # TOOL: search
    # ========================================================================

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        PURE PROXY - forward search to daemon with ZERO logic.
        """
        logger.info(f"MCP proxy search: '{request.query}'")

        try:
            response = await self.client.post(
                f"{self.daemon_url}/protocol/search",
                json={"q": request.query}
            )
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                raise RuntimeError(data.get('error', 'Search failed'))

            # Convert daemon response to MCP SearchResponse format
            contexts = data.get('contexts', [])
            results = []
            for i, ctx in enumerate(contexts):
                # Map daemon fields to MCP SearchResult fields
                file_path = ctx.get('file', '')  # daemon uses 'file' not 'file_path'
                text = ctx.get('text', '')
                
                results.append(SearchResult(
                    chunk_id=f"{file_path}:{i}",  # Generate ID from file + index
                    text=text,
                    snippet=text[:200] if len(text) > 200 else text,
                    file_path=file_path,
                    similarity_score=1.0,  # daemon doesn't return scores yet
                    final_score=1.0,
                    platform=ctx.get('platform'),
                    timestamp=ctx.get('timestamp'),
                    chunk_position=i,
                    source={}  # Empty dict - daemon citations are list, not dict
                ))

            return SearchResponse(
                query=request.query,
                processed_query=data.get('query', request.query),
                results=results,
                total=len(results),
                took_ms=0  # Calculated by caller
            )

        except httpx.HTTPError as e:
            logger.error(f"Daemon request failed: {e}")
            raise RuntimeError(f"Failed to connect to daemon: {e}")

    # Note: No summarize tool - was fake logic in MCP layer.
    # If needed in future, implement properly in daemon.

    # ========================================================================
    # TOOL: open
    # ========================================================================

    async def open(self, request: OpenRequest) -> OpenResponse:
        """
        Retrieve full contents of a specific file - proxies to daemon /file/{filepath}.

        Args:
            request: OpenRequest with file path

        Returns:
            OpenResponse with file content and metadata
        """
        logger.info(f"MCP proxy open: {request.file_path}")

        # Forward to daemon
        try:
            response = await self.client.get(
                f"{self.daemon_url}/file/{request.file_path}"
            )
            response.raise_for_status()
            data = response.json()

            # Build metadata if requested
            metadata = None
            if request.include_metadata:
                metadata = FileMetadata(
                    name=Path(data['path']).name,
                    path=data['path'],
                    size=data.get('size', 0),
                    created=datetime.fromtimestamp(data.get('last_modified', 0)),
                    modified=datetime.fromtimestamp(data.get('last_modified', 0)),
                    file_type=Path(data['path']).suffix[1:] if Path(data['path']).suffix else "unknown"
                )

            return OpenResponse(
                file_path=data['path'],
                content=data['content'],
                metadata=metadata
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise FileNotFoundError(f"File not found: {request.file_path}")
            elif e.response.status_code == 403:
                raise PermissionError(f"Access denied: {request.file_path}")
            else:
                raise RuntimeError(f"Failed to fetch file: {e}")
        except httpx.HTTPError as e:
            logger.error(f"Daemon request failed: {e}")
            raise RuntimeError(f"Failed to connect to daemon: {e}")

    # ========================================================================
    # TOOL: ingest
    # ========================================================================

    async def ingest(self, request: IngestRequest) -> IngestResponse:
        """
        Ingest new content into the vault - proxies to daemon /protocol/ingest.

        Args:
            request: IngestRequest with content and metadata

        Returns:
            IngestResponse with success status
        """
        logger.info(f"MCP proxy ingest: {len(request.content)} chars")

        try:
            response = await self.client.post(
                f"{self.daemon_url}/protocol/ingest",
                json={
                    "context": request.content,
                    "source_metadata": request.source_metadata or {},
                    "filename": request.filename
                }
            )
            response.raise_for_status()
            data = response.json()

            return IngestResponse(
                success=data.get('success', False),
                message=data.get('message', 'Ingestion complete'),
                file_path=data.get('file_path')
            )

        except httpx.HTTPError as e:
            logger.error(f"Daemon request failed: {e}")
            raise RuntimeError(f"Failed to ingest content: {e}")

    # ========================================================================
    # TOOL: list
    # ========================================================================

    async def list(self, request: ListRequest) -> ListResponse:
        """
        List directory contents - proxies to daemon /list endpoint.

        Args:
            request: ListRequest with path and options

        Returns:
            ListResponse with directory listing
        """
        logger.info(f"MCP proxy list: {request.path or '/'}")

        # Forward to daemon
        try:
            path = request.path or ""
            url = f"{self.daemon_url}/list/{path}" if path else f"{self.daemon_url}/list"

            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            # Convert daemon response to MCP ListResponse format
            items = []
            total_size = 0
            for item in data.get('items', []):
                list_item = ListItem(
                    name=item['name'],
                    path=item.get('name'),  # daemon returns relative name
                    is_directory=item['type'] == 'directory',
                    size=item.get('size'),
                    modified=datetime.fromtimestamp(item['last_modified']) if request.include_metadata else None,
                    file_type=Path(item['name']).suffix[1:] if item['type'] == 'file' and Path(item['name']).suffix else None
                )
                items.append(list_item)
                if list_item.size:
                    total_size += list_item.size

            # Filter by file types if requested
            if request.file_types:
                items = [
                    item for item in items
                    if item.is_directory or (item.file_type and item.file_type in request.file_types)
                ]

            return ListResponse(
                path=data.get('path', '/'),
                items=items,
                total_items=len(items),
                total_size=total_size if request.include_metadata else None
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise FileNotFoundError(f"Directory not found: {request.path}")
            elif e.response.status_code == 403:
                raise PermissionError(f"Access denied: {request.path}")
            else:
                raise RuntimeError(f"Failed to list directory: {e}")
        except httpx.HTTPError as e:
            logger.error(f"Daemon request failed: {e}")
            raise RuntimeError(f"Failed to connect to daemon: {e}")

    async def close(self):
        """Close HTTP client connection."""
        await self.client.aclose()
