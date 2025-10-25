"""
MCP Tools Implementation

Provides the core MCP tools: search, search_agentic, open, summarize, and list.
Integrates with retrieval engine and file system for data access.
"""

import os
import json
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
    Implementation of all MCP tools.

    Provides semantic search, file access, summarization, and directory listing.
    """

    def __init__(
        self,
        vault_path: str,
        retrieval_engine=None,
        llm_client=None
    ):
        """
        Initialize MCP tools.

        Args:
            vault_path: Path to LocalBrain vault directory
            retrieval_engine: Instance of RetrievalEngine for search
            llm_client: LLM client for summarization (optional)
        """
        self.vault_path = Path(vault_path).expanduser().resolve()
        self.retrieval_engine = retrieval_engine
        self.llm_client = llm_client

        logger.info(f"MCPTools initialized with vault: {self.vault_path}")

    # ========================================================================
    # TOOL: search
    # ========================================================================

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Natural language search across knowledge base.

        Args:
            request: SearchRequest with query and parameters

        Returns:
            SearchResponse with results
        """
        if not self.retrieval_engine:
            raise RuntimeError("Retrieval engine not initialized")

        logger.info(f"MCP search: '{request.query}' (top_k={request.top_k})")

        # Handle multiple queries
        queries = request.query if isinstance(request.query, list) else [request.query]

        # Execute searches and merge results
        all_results = []
        for query in queries:
            result = self.retrieval_engine.search(
                query=query,
                top_k=request.top_k,
                filters=request.filters,
                min_similarity=request.min_similarity
            )

            # Convert to SearchResult models
            for r in result['results']:
                all_results.append(SearchResult(**r))

        # Deduplicate and re-rank if multiple queries
        if len(queries) > 1:
            # Simple deduplication by chunk_id
            seen = set()
            unique_results = []
            for r in all_results:
                if r.chunk_id not in seen:
                    unique_results.append(r)
                    seen.add(r.chunk_id)
            all_results = sorted(unique_results, key=lambda x: x.final_score, reverse=True)

        # Limit to top_k
        all_results = all_results[:request.top_k]

        return SearchResponse(
            query=str(request.query),
            processed_query=queries[0] if queries else "",
            results=all_results,
            total=len(all_results),
            took_ms=0  # Calculated by caller
        )

    # ========================================================================
    # TOOL: search_agentic
    # ========================================================================

    async def search_agentic(self, request: SearchAgenticRequest) -> SearchResponse:
        """
        Structured search with specific filters and parameters.

        Args:
            request: SearchAgenticRequest with filters

        Returns:
            SearchResponse with filtered results
        """
        if not self.retrieval_engine:
            raise RuntimeError("Retrieval engine not initialized")

        logger.info(f"MCP search_agentic: keywords={request.keywords}, platform={request.platform}")

        # Build query from keywords
        query = " ".join(request.keywords) if request.keywords else "*"

        # Build filters
        filters = {}

        if request.platform:
            filters['platform'] = request.platform

        if request.file_path:
            filters['file_path'] = request.file_path

        # Handle date filters
        if request.days:
            date_from = (datetime.now() - timedelta(days=request.days)).isoformat()
            filters['date_from'] = date_from
        elif request.date_from:
            filters['date_from'] = request.date_from

        if request.date_to:
            filters['date_to'] = request.date_to

        # Execute search
        result = self.retrieval_engine.search(
            query=query,
            top_k=request.top_k,
            filters=filters,
            min_similarity=0.0  # Agentic search includes lower similarity matches
        )

        # Convert to SearchResult models
        results = [SearchResult(**r) for r in result['results']]

        return SearchResponse(
            query=query,
            processed_query=result['processed_query'],
            results=results,
            total=len(results),
            took_ms=result['took_ms']
        )

    # ========================================================================
    # TOOL: open
    # ========================================================================

    async def open(self, request: OpenRequest) -> OpenResponse:
        """
        Retrieve full contents of a specific file.

        Args:
            request: OpenRequest with file path

        Returns:
            OpenResponse with file content and metadata
        """
        # Resolve file path within vault
        file_path = self.vault_path / request.file_path

        # Security check: ensure path is within vault
        if not self._is_safe_path(file_path):
            raise PermissionError(f"Access denied: {request.file_path}")

        # Check file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {request.file_path}")

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValueError(f"Cannot read binary file: {request.file_path}")

        # Get metadata if requested
        metadata = None
        if request.include_metadata:
            stat = file_path.stat()
            metadata = FileMetadata(
                name=file_path.name,
                path=str(request.file_path),
                size=stat.st_size,
                created=datetime.fromtimestamp(stat.st_ctime),
                modified=datetime.fromtimestamp(stat.st_mtime),
                file_type=file_path.suffix[1:] if file_path.suffix else "unknown"
            )

        logger.info(f"MCP open: {request.file_path} ({len(content)} bytes)")

        return OpenResponse(
            file_path=str(request.file_path),
            content=content,
            metadata=metadata
        )

    # ========================================================================
    # TOOL: summarize
    # ========================================================================

    async def summarize(self, request: SummarizeRequest) -> SummarizeResponse:
        """
        Generate summary of file or content.

        Args:
            request: SummarizeRequest with file path or content

        Returns:
            SummarizeResponse with summary
        """
        # Get content
        if request.file_path:
            # Read file
            file_path = self.vault_path / request.file_path
            if not self._is_safe_path(file_path):
                raise PermissionError(f"Access denied: {request.file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            source = request.file_path
        else:
            content = request.content
            source = "provided_content"

        # Generate summary
        if self.llm_client:
            # Use LLM for summarization
            summary = await self._llm_summarize(content, request.max_length, request.style)
        else:
            # Fallback: simple extractive summary
            summary = self._simple_summarize(content, request.max_length, request.style)

        word_count = len(summary.split())

        logger.info(f"MCP summarize: {source} -> {word_count} words")

        return SummarizeResponse(
            summary=summary,
            word_count=word_count,
            source=source,
            style=request.style
        )

    async def _llm_summarize(self, content: str, max_length: int, style: str) -> str:
        """Generate summary using LLM."""
        # TODO: Implement LLM-based summarization
        # For now, fall back to simple summarization
        return self._simple_summarize(content, max_length, style)

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
        List directory contents.

        Args:
            request: ListRequest with path and options

        Returns:
            ListResponse with directory listing
        """
        # Resolve directory path
        dir_path = self.vault_path / (request.path or "")

        # Security check
        if not self._is_safe_path(dir_path):
            raise PermissionError(f"Access denied: {request.path}")

        # Check directory exists
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {request.path}")

        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {request.path}")

        # List items
        items = []
        total_size = 0

        if request.recursive:
            # Recursive listing
            for item in dir_path.rglob('*'):
                if self._should_include(item, request.file_types):
                    list_item = self._create_list_item(item, request.include_metadata)
                    items.append(list_item)
                    if list_item.size:
                        total_size += list_item.size
        else:
            # Non-recursive listing
            for item in dir_path.iterdir():
                if self._should_include(item, request.file_types):
                    list_item = self._create_list_item(item, request.include_metadata)
                    items.append(list_item)
                    if list_item.size:
                        total_size += list_item.size

        # Sort items: directories first, then alphabetically
        items.sort(key=lambda x: (not x.is_directory, x.name.lower()))

        logger.info(f"MCP list: {request.path or '/'} -> {len(items)} items")

        return ListResponse(
            path=str(request.path or "/"),
            items=items,
            total_items=len(items),
            total_size=total_size if request.include_metadata else None
        )

    def _create_list_item(self, path: Path, include_metadata: bool) -> ListItem:
        """Create ListItem from path."""
        relative_path = path.relative_to(self.vault_path)

        if include_metadata and path.is_file():
            stat = path.stat()
            return ListItem(
                name=path.name,
                path=str(relative_path),
                is_directory=False,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                file_type=path.suffix[1:] if path.suffix else "unknown"
            )
        else:
            return ListItem(
                name=path.name,
                path=str(relative_path),
                is_directory=path.is_dir(),
                size=None,
                modified=None,
                file_type=None
            )

    def _should_include(self, path: Path, file_types: Optional[List[str]]) -> bool:
        """Check if path should be included in listing."""
        # Skip hidden files
        if path.name.startswith('.'):
            return False

        # Skip __pycache__
        if '__pycache__' in path.parts:
            return False

        # Filter by file type
        if file_types and path.is_file():
            ext = path.suffix[1:] if path.suffix else ""
            if ext not in file_types:
                return False

        return True

    def _is_safe_path(self, path: Path) -> bool:
        """
        Check if path is safe (within vault, no traversal).

        Args:
            path: Path to check

        Returns:
            True if path is safe
        """
        try:
            resolved = path.resolve()
            return resolved.is_relative_to(self.vault_path)
        except (ValueError, RuntimeError):
            return False
