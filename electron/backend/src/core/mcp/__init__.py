"""
LocalBrain MCP (Model Context Protocol) Server

Provides a local API interface for external tools and integrations.
Implements the Model Context Protocol to enable external applications
to access LocalBrain functionality securely.
"""

from .server import MCPServer
from .tools import MCPTools
from .models import (
    MCPRequest,
    MCPResponse,
    SearchRequest,
    SearchAgenticRequest,
    OpenRequest,
    SummarizeRequest,
    ListRequest
)

__all__ = [
    "MCPServer",
    "MCPTools",
    "MCPRequest",
    "MCPResponse",
    "SearchRequest",
    "SearchAgenticRequest",
    "OpenRequest",
    "SummarizeRequest",
    "ListRequest"
]
