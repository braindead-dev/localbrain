#!/usr/bin/env python3
"""
LocalBrain MCP Stdio Server

Stdio-based MCP server wrapper that connects Claude Desktop to the LocalBrain
FastAPI server. Implements the Model Context Protocol specification.

Usage:
    python stdio_server.py

Configuration in Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "localbrain": {
          "command": "python",
          "args": ["/absolute/path/to/stdio_server.py"],
          "env": {
            "VAULT_PATH": "/path/to/vault",
            "MCP_API_KEY": "your-api-key"
          }
        }
      }
    }
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from typing import Any, Sequence
from dotenv import load_dotenv

# Load environment variables
dotenv_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
except ImportError:
    print("Error: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)


class LocalBrainMCPServer:
    """MCP server that forwards requests to LocalBrain FastAPI server."""

    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("localbrain")
        self.api_base_url = os.getenv("MCP_BASE_URL", "http://127.0.0.1:8765")
        self.api_key = os.getenv("MCP_API_KEY", "dev-key-local-only")
        self.vault_path = os.getenv("VAULT_PATH")

        if not self.vault_path:
            raise ValueError("VAULT_PATH environment variable required")

        # Setup tool handlers
        self._setup_tools()

    def _setup_tools(self):
        """Register all MCP tools."""

        # Tool 1: Search
        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name="search",
                    description="Natural language semantic search across your knowledge base. Returns relevant information from your vault.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query"
                            },
                            "top_k": {
                                "type": "number",
                                "description": "Number of results to return (default: 10)",
                                "default": 10
                            },
                            "min_similarity": {
                                "type": "number",
                                "description": "Minimum similarity threshold (0.0-1.0)",
                                "default": 0.0
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="search_agentic",
                    description="Structured search with specific filters (keywords, dates, platforms). Use for precise searches with known criteria.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific keywords to search for"
                            },
                            "days": {
                                "type": "number",
                                "description": "Search within last N days"
                            },
                            "platform": {
                                "type": "string",
                                "description": "Filter by platform (Gmail, Discord, LinkedIn, etc.)"
                            },
                            "top_k": {
                                "type": "number",
                                "description": "Number of results to return",
                                "default": 10
                            }
                        }
                    }
                ),
                types.Tool(
                    name="open",
                    description="Retrieve the full contents of a specific file from the vault. Use when you need to read an entire file.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to file within vault (e.g., 'career/job-search.md')"
                            },
                            "include_metadata": {
                                "type": "boolean",
                                "description": "Include file metadata (size, dates, etc.)",
                                "default": True
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                types.Tool(
                    name="summarize",
                    description="Generate a summary of a file or content. Useful for getting quick overviews.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to file to summarize"
                            },
                            "content": {
                                "type": "string",
                                "description": "Raw content to summarize (if not using file_path)"
                            },
                            "max_length": {
                                "type": "number",
                                "description": "Maximum summary length in words",
                                "default": 200
                            },
                            "style": {
                                "type": "string",
                                "description": "Summary style: concise, detailed, or bullets",
                                "enum": ["concise", "detailed", "bullets"],
                                "default": "concise"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="list",
                    description="List directory contents in the vault. Use to explore the file structure.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path (empty or '/' for root)"
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "List files recursively",
                                "default": False
                            },
                            "file_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by file types (e.g., ['md', 'txt'])"
                            }
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> Sequence[types.TextContent]:
            """Handle tool calls by forwarding to FastAPI server."""
            try:
                # Map tool name to endpoint
                endpoint_map = {
                    "search": "/mcp/search",
                    "search_agentic": "/mcp/search_agentic",
                    "open": "/mcp/open",
                    "summarize": "/mcp/summarize",
                    "list": "/mcp/list"
                }

                endpoint = endpoint_map.get(name)
                if not endpoint:
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Unknown tool '{name}'"
                    )]

                # Call FastAPI server
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.api_base_url}{endpoint}",
                        json=arguments,
                        headers={
                            "X-API-Key": self.api_key,
                            "Content-Type": "application/json"
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()

                        # Check if the response indicates success
                        if result.get("success"):
                            data = result.get("data", {})

                            # Format response based on tool type
                            if name == "search" or name == "search_agentic":
                                return self._format_search_results(data)
                            elif name == "open":
                                return self._format_open_results(data)
                            elif name == "summarize":
                                return self._format_summarize_results(data)
                            elif name == "list":
                                return self._format_list_results(data)
                            else:
                                return [types.TextContent(
                                    type="text",
                                    text=str(data)
                                )]
                        else:
                            error_msg = result.get("error", "Unknown error")
                            return [types.TextContent(
                                type="text",
                                text=f"Error: {error_msg}"
                            )]
                    else:
                        return [types.TextContent(
                            type="text",
                            text=f"Error: Server returned status {response.status_code}"
                        )]

            except httpx.TimeoutException:
                return [types.TextContent(
                    type="text",
                    text="Error: Request timed out. Make sure the FastAPI server is running on http://127.0.0.1:8765"
                )]
            except httpx.ConnectError:
                return [types.TextContent(
                    type="text",
                    text="Error: Cannot connect to FastAPI server. Start it with: python -m src.core.mcp.server"
                )]
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    def _format_search_results(self, data: dict) -> Sequence[types.TextContent]:
        """Format search results for display."""
        results = data.get("results", [])
        total = data.get("total", 0)
        took_ms = data.get("took_ms", 0)

        if not results:
            return [types.TextContent(
                type="text",
                text="No results found."
            )]

        output = f"Found {total} results ({took_ms:.1f}ms):\n\n"

        for i, result in enumerate(results, 1):
            file_path = result.get("file_path", "unknown")
            snippet = result.get("snippet", "")
            similarity = result.get("similarity_score", 0)
            platform = result.get("platform", "")
            timestamp = result.get("timestamp", "")

            output += f"{i}. **{file_path}** (similarity: {similarity:.2f})\n"
            if platform:
                output += f"   Source: {platform}"
                if timestamp:
                    output += f" | {timestamp[:10]}"
                output += "\n"
            output += f"   {snippet}\n\n"

        return [types.TextContent(type="text", text=output)]

    def _format_open_results(self, data: dict) -> Sequence[types.TextContent]:
        """Format file open results."""
        file_path = data.get("file_path", "")
        content = data.get("content", "")
        metadata = data.get("metadata")

        output = f"# {file_path}\n\n"

        if metadata:
            size = metadata.get("size", 0)
            modified = metadata.get("modified", "")
            output += f"*Size: {size} bytes | Modified: {modified[:10]}*\n\n"

        output += "---\n\n"
        output += content

        return [types.TextContent(type="text", text=output)]

    def _format_summarize_results(self, data: dict) -> Sequence[types.TextContent]:
        """Format summarization results."""
        summary = data.get("summary", "")
        source = data.get("source", "")
        word_count = data.get("word_count", 0)

        output = f"**Summary of {source}** ({word_count} words):\n\n{summary}"

        return [types.TextContent(type="text", text=output)]

    def _format_list_results(self, data: dict) -> Sequence[types.TextContent]:
        """Format directory listing results."""
        path = data.get("path", "/")
        items = data.get("items", [])
        total_items = data.get("total_items", 0)

        if not items:
            return [types.TextContent(
                type="text",
                text=f"Directory '{path}' is empty."
            )]

        output = f"**Contents of {path}/** ({total_items} items):\n\n"

        # Separate directories and files
        dirs = [item for item in items if item.get("is_directory")]
        files = [item for item in items if not item.get("is_directory")]

        if dirs:
            output += "**Directories:**\n"
            for item in dirs:
                output += f"  📁 {item['name']}/\n"
            output += "\n"

        if files:
            output += "**Files:**\n"
            for item in files:
                name = item['name']
                size = item.get('size', 0)
                file_type = item.get('file_type', '')
                if size:
                    size_kb = size / 1024
                    output += f"  📄 {name} ({size_kb:.1f} KB, {file_type})\n"
                else:
                    output += f"  📄 {name}\n"

        return [types.TextContent(type="text", text=output)]

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Entry point for the stdio server."""
    server = LocalBrainMCPServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
