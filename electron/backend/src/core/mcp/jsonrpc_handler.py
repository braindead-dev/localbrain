"""
JSON-RPC 2.0 Handler for MCP Server

Adds JSON-RPC 2.0 endpoint to existing MCP server for compatibility with
MCP-compliant clients and remote bridges.
"""

from typing import Any, Dict, Optional, List
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from loguru import logger

from .models import SearchRequest, OpenRequest, ListRequest


class JSONRPCHandler:
    """Handles JSON-RPC 2.0 requests and routes to MCP tools"""
    
    def __init__(self, app: FastAPI, tools_instance):
        self.app = app
        self.tools = tools_instance
        self.server_info = {
            "name": "localbrain",
            "version": "1.0.0"
        }
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup JSON-RPC endpoint"""
        
        @self.app.post("/mcp")
        async def jsonrpc_endpoint(request: Request):
            """
            JSON-RPC 2.0 endpoint for MCP protocol
            
            Handles:
            - initialize
            - tools/list
            - tools/call
            - resources/list (future)
            - prompts/list (future)
            """
            try:
                body = await request.json()
            except Exception as e:
                return JSONResponse(
                    content=self._error_response(None, -32700, "Parse error"),
                    status_code=400
                )
            
            # Handle batch requests
            is_batch = isinstance(body, list)
            requests = body if is_batch else [body]
            
            # Process each request
            responses = []
            for req in requests:
                resp = await self._handle_request(req)
                if resp:
                    responses.append(resp)
            
            # Return batch or single response
            if not responses:
                return Response(status_code=202)  # All notifications
            
            return JSONResponse(
                content=responses if is_batch else responses[0]
            )
    
    async def _handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a single JSON-RPC request"""
        
        # Validate JSON-RPC
        if request.get("jsonrpc") != "2.0":
            return self._error_response(
                request.get("id"),
                -32600,
                "Invalid Request: jsonrpc must be '2.0'"
            )
        
        method = request.get("method")
        params = request.get("params", {})
        req_id = request.get("id")
        
        # Notification (no response needed)
        if req_id is None:
            return None
        
        try:
            # Route to method handler
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_tools_list(params)
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            elif method == "resources/list":
                result = await self._handle_resources_list(params)
            elif method == "prompts/list":
                result = await self._handle_prompts_list(params)
            else:
                return self._error_response(
                    req_id,
                    -32601,
                    f"Method not found: {method}"
                )
            
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result
            }
        
        except Exception as e:
            logger.error(f"Error handling {method}: {e}")
            return self._error_response(
                req_id,
                -32603,
                f"Internal error: {str(e)}"
            )
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": self.server_info
        }
    
    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {
            "tools": [
                {
                    "name": "search",
                    "description": "Natural language search across your knowledge base",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "open",
                    "description": "Retrieve full contents of a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to file in vault"
                            }
                        },
                        "required": ["file_path"]
                    }
                },
                {
                    "name": "list",
                    "description": "List contents of a directory",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "directory_path": {
                                "type": "string",
                                "description": "Relative path to directory (empty for root)"
                            }
                        },
                        "required": []
                    }
                }
            ]
        }
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            raise ValueError("Tool name required")
        
        # Route to appropriate tool
        if tool_name == "search":
            # Create SearchRequest object
            search_req = SearchRequest(query=arguments.get("query"))
            result = await self.tools.search(search_req)
        elif tool_name == "open":
            # Create OpenRequest object
            open_req = OpenRequest(file_path=arguments.get("file_path"))
            result = await self.tools.open_file(open_req)
        elif tool_name == "list":
            # Create ListRequest object
            list_req = ListRequest(directory_path=arguments.get("directory_path", ""))
            result = await self.tools.list_directory(list_req)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": str(result)
                }
            ]
        }
    
    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request"""
        # Future: Return available resources (files in vault)
        return {"resources": []}
    
    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request"""
        # Future: Return available prompts
        return {"prompts": []}
    
    def _error_response(self, req_id: Optional[Any], code: int, message: str) -> Dict[str, Any]:
        """Create JSON-RPC error response"""
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": code,
                "message": message
            }
        }
