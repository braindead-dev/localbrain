"""
Pydantic models for MCP request and response validation.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


# ============================================================================
# Base Models
# ============================================================================

class MCPRequest(BaseModel):
    """Base model for all MCP requests."""
    tool: str = Field(..., description="MCP tool name to execute")
    request_id: Optional[str] = Field(None, description="Optional request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MCPResponse(BaseModel):
    """Base model for all MCP responses."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    took_ms: float = Field(..., description="Processing time in milliseconds")
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Tool-Specific Request Models
# ============================================================================

class SearchRequest(BaseModel):
    """
    Pure proxy search request - ONLY query, no other parameters.
    Backend handles everything.
    """
    query: str = Field(..., description="Natural language search query")

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v


# SearchAgenticRequest REMOVED - duplicate tool deleted
# Daemon has ONE search endpoint, MCP has ONE search tool


class OpenRequest(BaseModel):
    """
    Request model for file open tool.

    Retrieve full contents of specific files.
    """
    file_path: str = Field(..., description="Path to file within vault directory")
    include_metadata: bool = Field(True, description="Include file metadata in response")

    @validator('file_path')
    def validate_file_path(cls, v):
        """Ensure file path is not empty and doesn't escape vault."""
        if not v.strip():
            raise ValueError("File path cannot be empty")
        # Prevent directory traversal attacks
        if '..' in v or v.startswith('/'):
            raise ValueError("Invalid file path: directory traversal not allowed")
        return v


class SummarizeRequest(BaseModel):
    """
    Request model for summarization tool.

    Generate summaries of files or search results.
    """
    file_path: Optional[str] = Field(None, description="Path to file to summarize")
    content: Optional[str] = Field(None, description="Raw content to summarize")
    max_length: int = Field(200, ge=50, le=1000, description="Maximum summary length in words")
    style: str = Field("concise", description="Summary style: concise, detailed, bullets")

    @validator('style')
    def validate_style(cls, v):
        """Ensure style is valid."""
        valid_styles = ["concise", "detailed", "bullets"]
        if v not in valid_styles:
            raise ValueError(f"Invalid style: {v}. Must be one of {valid_styles}")
        return v

    @validator('content')
    def validate_input(cls, v, values):
        """Ensure either file_path or content is provided."""
        if not values.get('file_path') and not v:
            raise ValueError("Either file_path or content must be provided")
        return v


class ListRequest(BaseModel):
    """
    Request model for directory listing tool.

    Browse directory structure and available files.
    """
    path: Optional[str] = Field(None, description="Directory path (optional, defaults to root)")
    recursive: bool = Field(False, description="List files recursively")
    include_metadata: bool = Field(True, description="Include file metadata (size, dates, etc.)")
    file_types: Optional[List[str]] = Field(None, description="Filter by file types (e.g., ['md', 'json'])")

    @validator('path')
    def validate_path(cls, v):
        """Prevent directory traversal."""
        if v and ('..' in v or v.startswith('/')):
            raise ValueError("Invalid path: directory traversal not allowed")
        return v


# ============================================================================
# Tool-Specific Response Models
# ============================================================================

class SearchResult(BaseModel):
    """Model for individual search result."""
    chunk_id: str
    text: str
    snippet: str
    file_path: str
    similarity_score: float
    final_score: float
    platform: Optional[str]
    timestamp: Optional[str]
    chunk_position: int
    source: Dict[str, Any]


class SearchResponse(BaseModel):
    """Response model for search tools."""
    query: str
    processed_query: str
    results: List[SearchResult]
    total: int
    took_ms: float


class FileMetadata(BaseModel):
    """Model for file metadata."""
    name: str
    path: str
    size: int
    created: datetime
    modified: datetime
    file_type: str


class OpenResponse(BaseModel):
    """Response model for open tool."""
    file_path: str
    content: str
    metadata: Optional[FileMetadata]


class SummarizeResponse(BaseModel):
    """Response model for summarize tool."""
    summary: str
    word_count: int
    source: str
    style: str


class ListItem(BaseModel):
    """Model for directory listing item."""
    name: str
    path: str
    is_directory: bool
    size: Optional[int]
    modified: Optional[datetime]
    file_type: Optional[str]


class ListResponse(BaseModel):
    """Response model for list tool."""
    path: str
    items: List[ListItem]
    total_items: int
    total_size: Optional[int]


# ============================================================================
# Authentication & Authorization Models
# ============================================================================

class MCPPermission(BaseModel):
    """Model for tool-level permissions."""
    tool: str
    allowed: bool
    scope_restrictions: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional restrictions (e.g., allowed directories, file types)"
    )


class MCPClientAuth(BaseModel):
    """Model for client authentication."""
    client_id: str
    api_key: str
    permissions: List[MCPPermission]
    rate_limit: int = Field(100, description="Requests per hour")
    enabled: bool = True


# ============================================================================
# Audit Log Models
# ============================================================================

class AuditLogEntry(BaseModel):
    """Model for audit log entries."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    client_id: str
    tool: str
    request_id: Optional[str]
    query: Optional[str]
    success: bool
    error: Optional[str]
    took_ms: float
    results_count: Optional[int]
