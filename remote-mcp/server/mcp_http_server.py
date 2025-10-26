#!/usr/bin/env python3
"""
MCP-Compliant HTTP/SSE Server

Implements the Model Context Protocol specification over HTTP with SSE support.
Forwards requests to local MCP servers via WebSocket tunnels.

Spec: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Optional, Any
from collections import defaultdict

from fastapi import FastAPI, Request, Response, Header, HTTPException, status, WebSocket
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from loguru import logger
from pydantic import BaseModel, Field

# ============================================================================
# Models
# ============================================================================

class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request"""
    jsonrpc: str = "2.0"
    id: Optional[int | str] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response"""
    jsonrpc: str = "2.0"
    id: Optional[int | str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class TunnelInfo(BaseModel):
    """Information about an active tunnel"""
    tunnel_id: str
    user_id: str
    websocket: Any  # websockets.WebSocketServerProtocol
    connected_at: datetime
    last_activity: datetime
    session_id: Optional[str] = None


# ============================================================================
# MCP HTTP/SSE Server
# ============================================================================

class MCPHTTPServer:
    """MCP-compliant HTTP server with SSE support"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8767):
        self.host = host
        self.port = port
        self.app = FastAPI(title="LocalBrain MCP Bridge")
        
        # Tunnel registry
        self.tunnels: Dict[str, TunnelInfo] = {}  # tunnel_id -> TunnelInfo
        self.user_tunnels: Dict[str, str] = {}  # user_id -> tunnel_id
        self.pending_responses: Dict[str, Dict[str, asyncio.Future]] = {}  # tunnel_id -> request_id -> Future
        
        # Session management
        self.sessions: Dict[str, str] = {}  # session_id -> user_id
        
        self._setup_middleware()
        self._setup_routes()
        
    def _setup_middleware(self):
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
    def _setup_routes(self):
        """Setup MCP protocol routes"""
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "active_tunnels": len(self.tunnels),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.post("/mcp")
        async def mcp_endpoint(
            request: Request,
            mcp_session_id: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None),
            x_api_key: Optional[str] = Header(None)
        ):
            """
            Main MCP endpoint - accepts JSON-RPC 2.0 messages
            
            Supports:
            - Single requests/responses
            - Batched requests
            - SSE streaming for responses
            """
            # Get user_id from auth
            user_id = self._authenticate(authorization, x_api_key)
            if not user_id:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Check for active tunnel
            tunnel_id = self.user_tunnels.get(user_id)
            if not tunnel_id or tunnel_id not in self.tunnels:
                raise HTTPException(status_code=503, detail="No active tunnel for user")
            
            tunnel = self.tunnels[tunnel_id]
            
            # Handle session management
            if mcp_session_id:
                if mcp_session_id not in self.sessions:
                    raise HTTPException(status_code=404, detail="Session not found")
                if self.sessions[mcp_session_id] != user_id:
                    raise HTTPException(status_code=403, detail="Invalid session")
            
            # Parse request body
            try:
                body = await request.json()
            except Exception as e:
                logger.error(f"Failed to parse request body: {e}")
                raise HTTPException(status_code=400, detail="Invalid JSON")
            
            # Handle batch or single request
            is_batch = isinstance(body, list)
            requests = body if is_batch else [body]
            
            # Check if all are notifications/responses (no result expected)
            has_requests = any(r.get("method") and r.get("id") is not None for r in requests)
            
            if not has_requests:
                # All notifications/responses - forward and return 202
                await self._forward_to_tunnel(tunnel_id, body)
                return Response(status_code=202)
            
            # Has requests - need to return responses
            # Check if client accepts SSE
            accept = request.headers.get("accept", "")
            use_sse = "text/event-stream" in accept
            
            if use_sse:
                # Stream responses via SSE
                return StreamingResponse(
                    self._sse_response_stream(tunnel_id, requests, user_id, mcp_session_id),
                    media_type="text/event-stream",
                    headers=self._get_session_headers(user_id, mcp_session_id)
                )
            else:
                # Return single JSON response
                responses = await self._handle_requests(tunnel_id, requests)
                return JSONResponse(
                    content=responses if is_batch else responses[0],
                    headers=self._get_session_headers(user_id, mcp_session_id)
                )
        
        @self.app.get("/mcp")
        async def mcp_sse_listen(
            request: Request,
            mcp_session_id: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None),
            x_api_key: Optional[str] = Header(None)
        ):
            """
            SSE endpoint for receiving server-initiated messages
            """
            # Get user_id from auth
            user_id = self._authenticate(authorization, x_api_key)
            if not user_id:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Check for active tunnel
            tunnel_id = self.user_tunnels.get(user_id)
            if not tunnel_id or tunnel_id not in self.tunnels:
                raise HTTPException(status_code=503, detail="No active tunnel for user")
            
            # Return SSE stream
            return StreamingResponse(
                self._sse_listen_stream(tunnel_id, user_id),
                media_type="text/event-stream"
            )
        
        @self.app.delete("/mcp")
        async def mcp_session_delete(
            mcp_session_id: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None),
            x_api_key: Optional[str] = Header(None)
        ):
            """Terminate a session"""
            if not mcp_session_id:
                raise HTTPException(status_code=400, detail="Session ID required")
            
            user_id = self._authenticate(authorization, x_api_key)
            if not user_id:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if mcp_session_id in self.sessions:
                if self.sessions[mcp_session_id] == user_id:
                    del self.sessions[mcp_session_id]
                    return Response(status_code=204)
                else:
                    raise HTTPException(status_code=403, detail="Not your session")
            
            raise HTTPException(status_code=404, detail="Session not found")
        
        @self.app.websocket("/tunnel/connect")
        async def tunnel_connect(websocket: WebSocket):
            """WebSocket endpoint for tunnel clients"""
            await self._handle_tunnel_connection(websocket)
    
    def _authenticate(self, authorization: Optional[str], x_api_key: Optional[str]) -> Optional[str]:
        """Extract user_id from auth headers"""
        # Try Bearer token
        if authorization and authorization.startswith("Bearer "):
            api_key = authorization[7:]
        elif x_api_key:
            api_key = x_api_key
        else:
            return None
        
        # In production, validate API key against database
        # For now, extract user_id from API key pattern: lb_<user_id>_<random>
        # Or just use the API key as user_id
        return api_key  # Simplified - in production, look up user_id from API key
    
    def _get_session_headers(self, user_id: str, current_session_id: Optional[str]) -> Dict[str, str]:
        """Generate session headers for response"""
        headers = {}
        
        # Create new session on initialize if not exists
        if not current_session_id:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = user_id
            headers["Mcp-Session-Id"] = session_id
        
        return headers
    
    async def _forward_to_tunnel(self, tunnel_id: str, message: Any) -> None:
        """Forward message to tunnel"""
        if tunnel_id not in self.tunnels:
            return
        
        tunnel = self.tunnels[tunnel_id]
        try:
            await tunnel.websocket.send_json({
                "type": "request",
                "data": message
            })
            logger.info(f"Forwarded request to tunnel {tunnel_id}: {message}")
        except Exception as e:
            logger.error(f"Failed to forward to tunnel {tunnel_id}: {e}")
    
    async def _handle_requests(self, tunnel_id: str, requests: list) -> list:
        """Handle requests and wait for responses"""
        # Create futures for each request
        futures = {}
        for req in requests:
            if req.get("id") is not None:
                request_id = str(req["id"])
                future = asyncio.Future()
                futures[request_id] = future
                
                if tunnel_id not in self.pending_responses:
                    self.pending_responses[tunnel_id] = {}
                self.pending_responses[tunnel_id][request_id] = future
        
        # Forward requests to tunnel
        await self._forward_to_tunnel(tunnel_id, requests)
        
        # Wait for all responses (with timeout)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*futures.values(), return_exceptions=True),
                timeout=30.0
            )
            return list(results)
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for responses from tunnel {tunnel_id}")
            # Return error responses
            return [
                {
                    "jsonrpc": "2.0",
                    "id": req.get("id"),
                    "error": {"code": -32000, "message": "Request timeout"}
                }
                for req in requests if req.get("id") is not None
            ]
    
    async def _sse_response_stream(self, tunnel_id: str, requests: list, user_id: str, session_id: Optional[str]):
        """Generate SSE stream for responses"""
        event_id = 0
        
        # Forward requests
        await self._forward_to_tunnel(tunnel_id, requests)
        
        # Create futures for responses
        futures = {}
        for req in requests:
            if req.get("id") is not None:
                request_id = str(req["id"])
                future = asyncio.Future()
                futures[request_id] = future
                
                if tunnel_id not in self.pending_responses:
                    self.pending_responses[tunnel_id] = {}
                self.pending_responses[tunnel_id][request_id] = future
        
        # Stream responses as they arrive
        try:
            for request_id, future in futures.items():
                result = await asyncio.wait_for(future, timeout=30.0)
                
                # Send as SSE event
                event_id += 1
                yield f"id: {event_id}\n"
                yield f"data: {json.dumps(result)}\n\n"
        except asyncio.TimeoutError:
            logger.error(f"Timeout in SSE stream for tunnel {tunnel_id}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32000, "message": "Stream timeout"}
            }
            event_id += 1
            yield f"id: {event_id}\n"
            yield f"data: {json.dumps(error_response)}\n\n"
    
    async def _sse_listen_stream(self, tunnel_id: str, user_id: str):
        """Generate SSE stream for server-initiated messages"""
        # This would stream notifications/requests from the server
        # For now, just keep connection alive
        try:
            while tunnel_id in self.tunnels:
                # Send keepalive every 30 seconds
                yield ": keepalive\n\n"
                await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Error in SSE listen stream: {e}")
    
    async def _handle_tunnel_connection(self, websocket: WebSocket):
        """Handle WebSocket tunnel connection from local client"""
        await websocket.accept()
        
        tunnel_id = None
        user_id = None
        
        try:
            # Expect authentication message
            auth_msg = await websocket.receive_json()
            
            if auth_msg.get("type") != "auth":
                await websocket.send_json({
                    "type": "error",
                    "message": "Authentication required"
                })
                await websocket.close()
                return
            
            user_id = auth_msg.get("user_id")
            api_key = auth_msg.get("api_key")
            
            if not user_id or not api_key:
                await websocket.send_json({
                    "type": "error",
                    "message": "user_id and api_key required"
                })
                await websocket.close()
                return
            
            # Register tunnel
            tunnel_id = str(uuid.uuid4())
            self.tunnels[tunnel_id] = TunnelInfo(
                tunnel_id=tunnel_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            self.user_tunnels[user_id] = tunnel_id
            self.pending_responses[tunnel_id] = {}
            
            logger.info(f"Tunnel registered: {tunnel_id} for user {user_id}")
            
            # Send confirmation
            await websocket.send_json({
                "type": "connected",
                "tunnel_id": tunnel_id,
                "remote_url": f"http://{self.host}:{self.port}/mcp"
            })
            
            # Handle messages from tunnel
            while True:
                message = await websocket.receive_json()
                
                if message.get("type") == "response":
                    # Response from local MCP server
                    request_id = message.get("request_id")
                    response_data = message.get("data")
                    
                    if request_id and tunnel_id in self.pending_responses:
                        if request_id in self.pending_responses[tunnel_id]:
                            future = self.pending_responses[tunnel_id][request_id]
                            if not future.done():
                                future.set_result(response_data)
                            del self.pending_responses[tunnel_id][request_id]
                
                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                # Update activity
                self.tunnels[tunnel_id].last_activity = datetime.utcnow()
        
        except Exception as e:
            logger.error(f"Error in tunnel connection: {e}")
        
        finally:
            # Cleanup
            if tunnel_id and tunnel_id in self.tunnels:
                del self.tunnels[tunnel_id]
                logger.info(f"Tunnel disconnected: {tunnel_id}")
            
            if user_id and user_id in self.user_tunnels:
                del self.user_tunnels[user_id]
            
            if tunnel_id and tunnel_id in self.pending_responses:
                # Cancel all pending requests
                for future in self.pending_responses[tunnel_id].values():
                    if not future.done():
                        future.cancel()
                del self.pending_responses[tunnel_id]


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    host = os.getenv("BRIDGE_HOST", "0.0.0.0")
    port = int(os.getenv("BRIDGE_PORT", "8767"))
    
    logger.info("=" * 60)
    logger.info("LocalBrain MCP-Compliant HTTP/SSE Bridge Starting...")
    logger.info("=" * 60)
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"MCP Endpoint: http://{host}:{port}/mcp")
    logger.info("=" * 60)
    
    server = MCPHTTPServer(host=host, port=port)
    
    uvicorn.run(
        server.app,
        host=host,
        port=port,
        log_level="info"
    )
