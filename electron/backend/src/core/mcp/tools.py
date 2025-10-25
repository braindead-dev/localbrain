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
    SearchRequest, SearchAgenticRequest, OpenRequest,
    SummarizeRequest, ListRequest,
    SearchResponse, OpenResponse, SummarizeResponse, ListResponse,
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
        Natural language search - proxies to daemon /protocol/search.

        Args:
            request: SearchRequest with query and parameters

        Returns:
            SearchResponse with results
        """
        logger.info(f"MCP proxy search: '{request.query}'")

        # Handle multiple queries
        query = request.query if isinstance(request.query, str) else " ".join(request.query)

        # Forward to daemon
        try:
            response = await self.client.post(
                f"{self.daemon_url}/protocol/search",
                json={"q": query}
            )
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                raise RuntimeError(data.get('error', 'Search failed'))

            # Convert daemon response to MCP SearchResponse format
            contexts = data.get('contexts', [])
            results = []
            for ctx in contexts[:request.top_k]:
                results.append(SearchResult(
                    chunk_id=ctx.get('chunk_id', ''),
                    text=ctx.get('text', ''),
                    snippet=ctx.get('snippet', ctx.get('text', '')[:200]),
                    file_path=ctx.get('file_path', ''),
                    similarity_score=ctx.get('similarity_score', 0.0),
                    final_score=ctx.get('final_score', ctx.get('similarity_score', 0.0)),
                    platform=ctx.get('platform'),
                    timestamp=ctx.get('timestamp'),
                    chunk_position=ctx.get('chunk_position', 0),
                    source=ctx.get('source', {})
                ))

            return SearchResponse(
                query=query,
                processed_query=data.get('query', query),
                results=results,
                total=len(results),
                took_ms=0  # Calculated by caller
            )

        except httpx.HTTPError as e:
            logger.error(f"Daemon request failed: {e}")
            raise RuntimeError(f"Failed to connect to daemon: {e}")

    # ========================================================================
    # TOOL: search_agentic
    # ========================================================================

    async def search_agentic(self, request: SearchAgenticRequest) -> SearchResponse:
        """
        Structured search - proxies to daemon /protocol/search with structured params.

        Args:
            request: SearchAgenticRequest with filters

        Returns:
            SearchResponse with filtered results
        """
        logger.info(f"MCP proxy search_agentic: keywords={request.keywords}, platform={request.platform}")

        # Build query from keywords
        query = " ".join(request.keywords) if request.keywords else ""

        # Add platform and other filters to query for daemon
        query_parts = [query] if query else []
        if request.platform:
            query_parts.append(f"platform:{request.platform}")
        if request.file_path:
            query_parts.append(f"file:{request.file_path}")

        full_query = " ".join(query_parts)

        # Forward to daemon
        try:
            response = await self.client.post(
                f"{self.daemon_url}/protocol/search",
                json={"q": full_query}
            )
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                raise RuntimeError(data.get('error', 'Search failed'))

            # Convert daemon response to MCP SearchResponse format
            contexts = data.get('contexts', [])
            results = []
            for ctx in contexts[:request.top_k]:
                results.append(SearchResult(
                    chunk_id=ctx.get('chunk_id', ''),
                    text=ctx.get('text', ''),
                    snippet=ctx.get('snippet', ctx.get('text', '')[:200]),
                    file_path=ctx.get('file_path', ''),
                    similarity_score=ctx.get('similarity_score', 0.0),
                    final_score=ctx.get('final_score', ctx.get('similarity_score', 0.0)),
                    platform=ctx.get('platform'),
                    timestamp=ctx.get('timestamp'),
                    chunk_position=ctx.get('chunk_position', 0),
                    source=ctx.get('source', {})
                ))

            return SearchResponse(
                query=full_query,
                processed_query=data.get('query', full_query),
                results=results,
                total=len(results),
                took_ms=0  # Calculated by caller
            )

        except httpx.HTTPError as e:
            logger.error(f"Daemon request failed: {e}")
            raise RuntimeError(f"Failed to connect to daemon: {e}")

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
    # TOOL: summarize
    # ========================================================================

    async def summarize(self, request: SummarizeRequest) -> SummarizeResponse:
        """
        Generate summary of file or content.

        Note: Daemon doesn't have a summarize endpoint yet, so this provides
        a simple extractive summary directly.

        Args:
            request: SummarizeRequest with file path or content

        Returns:
            SummarizeResponse with summary
        """
        logger.info(f"MCP proxy summarize: {request.file_path or 'content'}")

        # Get content
        if request.file_path:
            # Fetch file from daemon
            try:
                response = await self.client.get(
                    f"{self.daemon_url}/file/{request.file_path}"
                )
                response.raise_for_status()
                data = response.json()
                content = data['content']
                source = request.file_path
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch file for summarization: {e}")
                raise RuntimeError(f"Failed to fetch file: {e}")
        else:
            content = request.content
            source = "provided_content"

        # Generate simple extractive summary
        summary = self._simple_summarize(content, request.max_length, request.style)
        word_count = len(summary.split())

        logger.info(f"MCP summarize: {source} -> {word_count} words")

        return SummarizeResponse(
            summary=summary,
            word_count=word_count,
            source=source,
            style=request.style
        )

    def _simple_summarize(self, content: str, max_length: int, style: str) -> str:
        """Simple extractive summarization."""
        words = content.split()

        if len(words) <= max_length:
            return content

        if style == "bullets":
            # Extract first sentence of each paragraph
            paragraphs = content.split('\n\n')
            bullets = []
            for para in paragraphs[:5]:  # Max 5 bullets
                sentences = para.split('.')
                if sentences[0].strip():
                    bullets.append(f"- {sentences[0].strip()}")
            return '\n'.join(bullets)
        else:
            # Extract first N words
            summary_words = words[:max_length]
            summary = ' '.join(summary_words)

            # Try to end at sentence boundary
            last_period = summary.rfind('.')
            if last_period > len(summary) * 0.7:
                summary = summary[:last_period + 1]
            else:
                summary += "..."

            return summary

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
