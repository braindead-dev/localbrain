"""
Protocol Handler for localbrain:// URLs

Intercepts and processes localbrain:// protocol URLs from external sources,
routing them to appropriate MCP tools.

Examples:
  localbrain://search?q=internship+applications
  localbrain://open?filepath=career/job-search.md
  localbrain://summarize?filepath=finance/taxes.md
  localbrain://list?path=projects
"""

from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs, unquote
from loguru import logger

from .models import (
    SearchRequest, OpenRequest,
    SummarizeRequest, ListRequest
)


class ProtocolHandler:
    """
    Handles localbrain:// protocol URLs and converts them to MCP tool requests.

    Supports all MCP tools: search, open, summarize, list.
    """

    def __init__(self, tools_client=None):
        """
        Initialize protocol handler.

        Args:
            tools_client: Optional MCPTools client for direct execution
        """
        self.tools_client = tools_client

    def parse_url(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse localbrain:// URL into tool name and parameters.

        Args:
            url: Protocol URL (e.g., localbrain://search?q=test)

        Returns:
            Tuple of (tool_name, parameters)

        Raises:
            ValueError if URL is invalid
        """
        # Parse URL
        parsed = urlparse(url)

        if parsed.scheme != "localbrain":
            raise ValueError(f"Invalid protocol: {parsed.scheme}. Expected 'localbrain'")

        # Extract tool name from host/path
        tool = parsed.netloc or parsed.path.lstrip('/')

        if not tool:
            raise ValueError("No tool specified in URL")

        # Parse query parameters
        params = parse_qs(parsed.query)

        # Convert single-item lists to values
        params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

        # URL decode values
        params = {k: unquote(v) if isinstance(v, str) else v for k, v in params.items()}

        logger.debug(f"Parsed protocol URL: tool={tool}, params={params}")

        return tool, params

    def create_request(self, tool: str, params: Dict[str, Any]) -> Any:
        """
        Create MCP request object from tool and parameters.

        Args:
            tool: Tool name
            params: Parameters dictionary

        Returns:
            Request object (SearchRequest, OpenRequest, etc.)

        Raises:
            ValueError if tool is unknown or parameters are invalid
        """
        try:
            if tool == "search":
                return self._create_search_request(params)
            elif tool == "open":
                return self._create_open_request(params)
            elif tool == "summarize":
                return self._create_summarize_request(params)
            elif tool == "list":
                return self._create_list_request(params)
            else:
                raise ValueError(f"Unknown tool: {tool}")

        except Exception as e:
            logger.error(f"Failed to create request for {tool}: {e}")
            raise ValueError(f"Invalid parameters for {tool}: {e}")

    def _create_search_request(self, params: Dict[str, Any]) -> SearchRequest:
        """Create SearchRequest from parameters - pure proxy, only query."""
        query = params.get('q') or params.get('query')

        if not query:
            raise ValueError("Missing required parameter: q or query")

        return SearchRequest(query=query)

    def _create_open_request(self, params: Dict[str, Any]) -> OpenRequest:
        """Create OpenRequest from parameters."""
        file_path = params.get('filepath') or params.get('file_path') or params.get('path')

        if not file_path:
            raise ValueError("Missing required parameter: filepath, file_path, or path")

        return OpenRequest(
            file_path=file_path,
            include_metadata=params.get('include_metadata', 'true').lower() == 'true'
        )

    def _create_summarize_request(self, params: Dict[str, Any]) -> SummarizeRequest:
        """Create SummarizeRequest from parameters."""
        file_path = params.get('filepath') or params.get('file_path')
        content = params.get('content')

        if not file_path and not content:
            raise ValueError("Missing required parameter: filepath or content")

        return SummarizeRequest(
            file_path=file_path,
            content=content,
            max_length=int(params.get('max_length', 200)),
            style=params.get('style', 'concise')
        )

    def _create_list_request(self, params: Dict[str, Any]) -> ListRequest:
        """Create ListRequest from parameters."""
        file_types = params.get('file_types')
        if file_types:
            if isinstance(file_types, str):
                file_types = [ft.strip() for ft in file_types.split(',')]
        else:
            file_types = None

        return ListRequest(
            path=params.get('path'),
            recursive=params.get('recursive', 'false').lower() == 'true',
            include_metadata=params.get('include_metadata', 'true').lower() == 'true',
            file_types=file_types
        )

    async def handle_url(self, url: str) -> Dict[str, Any]:
        """
        Handle protocol URL end-to-end.

        Parse URL, create request, execute tool, and return results.

        Args:
            url: localbrain:// URL

        Returns:
            Dictionary with results or error

        Raises:
            ValueError if URL is invalid
            RuntimeError if tools client not initialized
        """
        if not self.tools_client:
            raise RuntimeError("Tools client not initialized")

        # Parse URL
        tool, params = self.parse_url(url)

        # Create request
        request = self.create_request(tool, params)

        # Execute tool
        if tool == "search":
            result = await self.tools_client.search(request)
        elif tool == "open":
            result = await self.tools_client.open(request)
        elif tool == "summarize":
            result = await self.tools_client.summarize(request)
        elif tool == "list":
            result = await self.tools_client.list(request)
        else:
            raise ValueError(f"Unknown tool: {tool}")

        return result.model_dump()

    @staticmethod
    def build_url(tool: str, **params) -> str:
        """
        Build localbrain:// URL from tool and parameters.

        Args:
            tool: Tool name
            **params: URL parameters

        Returns:
            Protocol URL string

        Examples:
            >>> build_url("search", q="test")
            'localbrain://search?q=test'
        """
        from urllib.parse import urlencode

        # Build query string
        query_string = urlencode(params)

        return f"localbrain://{tool}?{query_string}"


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example: Parse protocol URLs
    handler = ProtocolHandler()

    test_urls = [
        "localbrain://search?q=internship+applications",
        "localbrain://open?filepath=career/job-search.md",
        "localbrain://search_agentic?keywords=internship,nvidia&days=7",
        "localbrain://summarize?filepath=finance/taxes.md",
        "localbrain://list?path=projects",
    ]

    for url in test_urls:
        try:
            tool, params = handler.parse_url(url)
            request = handler.create_request(tool, params)
            print(f"\nURL: {url}")
            print(f"Tool: {tool}")
            print(f"Request: {request}")
        except Exception as e:
            print(f"\nURL: {url}")
            print(f"Error: {e}")

    # Example: Build URLs
    print("\n" + "="*80)
    print("Building URLs:")
    print("="*80)

    urls = [
        ProtocolHandler.build_url("search", q="test query"),
        ProtocolHandler.build_url("open", filepath="readme.md"),
        ProtocolHandler.build_url("summarize", filepath="document.md", style="bullets"),
        ProtocolHandler.build_url("list", path="projects", recursive=True),
    ]

    for url in urls:
        print(url)
