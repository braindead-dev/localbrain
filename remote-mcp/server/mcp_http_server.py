#!/usr/bin/env python3
"""
MCP-Compliant HTTP Bridge Server

This server runs on the cloud (146.190.120.44) and provides:
1. HTTP endpoint for MCP clients (Claude, Cursor, etc.)
2. WebSocket tunnel management for local clients
3. Request routing between MCP clients and local tunnels
4. Authentication and session management

Architecture:
    MCP Client -> HTTP -> This Server -> WebSocket -> Local Client -> Local MCP Server
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

import aiohttp
from aiohttp import web
from aiohttp.web import Request, Response, WebSocketResponse
import aiohttp_cors
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.getenv('PORT', '8767'))
HOST = os.getenv('HOST', '0.0.0.0')
API_KEY_PREFIX = os.getenv('API_KEY_PREFIX', 'lb_')
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1 hour
TUNNEL_TIMEOUT = int(os.getenv('TUNNEL_TIMEOUT', '300'))  # 5 minutes
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))  # 30 seconds

@dataclass
class TunnelClient:
    """Represents a connected tunnel client."""
    user_id: str
    api_key: str
    ws: WebSocketResponse
    connected_at: datetime
    last_ping: datetime
    pending_requests: Dict[str, asyncio.Future] = field(default_factory=dict)
    
    @property
    def is_alive(self) -> bool:
        """Check if tunnel is still alive."""
        return (datetime.now() - self.last_ping).seconds < TUNNEL_TIMEOUT

@dataclass 
class MCPSession:
    """Represents an MCP client session."""
    session_id: str
    api_key: str
    created_at: datetime
    last_request: datetime
    user_id: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if session is still valid."""
        return (datetime.now() - self.last_request).seconds < SESSION_TIMEOUT


class MCPBridgeServer:
    """MCP-compliant HTTP bridge server."""
    
    def __init__(self):
        self.app = web.Application()
        self.tunnels: Dict[str, TunnelClient] = {}  # user_id -> TunnelClient
        self.sessions: Dict[str, MCPSession] = {}  # session_id -> MCPSession
        self.api_keys: Dict[str, str] = {}  # api_key -> user_id
        
        # Load API keys from environment or file
        self._load_api_keys()
        
        # Setup routes
        self._setup_routes()
        
        # Setup CORS
        self._setup_cors()
        
        # Background tasks
        self.cleanup_task = None
        
    def _load_api_keys(self):
        """Load API keys from configuration."""
        # Load from environment variables or a config file
        # Format: API_KEY_USER1=lb_xxxxx
        for key, value in os.environ.items():
            if key.startswith('API_KEY_'):
                user_id = key.replace('API_KEY_', '').lower()
                self.api_keys[value] = user_id
                logger.info(f"Loaded API key for user: {user_id}")
        
        # For development/testing
        if not self.api_keys:
            test_key = "lb_test_key_123"
            self.api_keys[test_key] = "test_user"
            logger.warning(f"No API keys configured, using test key: {test_key}")
    
    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.status)
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/tunnel', self.handle_tunnel_connect)
        
    def _setup_cors(self):
        """Setup CORS for browser-based MCP clients."""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def health_check(self, request: Request) -> Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "active_tunnels": len(self.tunnels),
            "active_sessions": len(self.sessions)
        })
    
    async def status(self, request: Request) -> Response:
        """Detailed status endpoint."""
        return web.json_response({
            "status": "operational",
            "server": {
                "version": "1.0.0",
                "uptime": time.process_time(),
                "host": HOST,
                "port": PORT
            },
            "tunnels": {
                "active": len(self.tunnels),
                "users": list(self.tunnels.keys())
            },
            "sessions": {
                "active": len(self.sessions),
                "timeout": SESSION_TIMEOUT
            },
            "timestamp": datetime.now().isoformat()
        })
    
    async def handle_tunnel_connect(self, request: Request) -> WebSocketResponse:
        """Handle WebSocket tunnel connection from local client."""
        ws = WebSocketResponse(heartbeat=30, autoping=True)
        await ws.prepare(request)
        
        user_id = None
        api_key = None
        
        try:
            # Wait for authentication message
            auth_msg = await asyncio.wait_for(ws.receive(), timeout=10)
            if auth_msg.type == aiohttp.WSMsgType.TEXT:
                auth_data = json.loads(auth_msg.data)
                
                # Validate authentication
                if auth_data.get('type') != 'auth':
                    await ws.send_json({"type": "error", "error": "First message must be auth"})
                    await ws.close()
                    return ws
                
                user_id = auth_data.get('user_id')
                api_key = auth_data.get('api_key')
                
                if not user_id or not api_key:
                    await ws.send_json({"type": "error", "error": "Missing credentials"})
                    await ws.close()
                    return ws
                
                # Validate API key
                if api_key not in self.api_keys or self.api_keys[api_key] != user_id:
                    await ws.send_json({"type": "error", "error": "Invalid credentials"})
                    await ws.close()
                    return ws
                
                # Close existing tunnel if any
                if user_id in self.tunnels:
                    old_tunnel = self.tunnels[user_id]
                    await old_tunnel.ws.close()
                    logger.info(f"Closed existing tunnel for user: {user_id}")
                
                # Register new tunnel
                tunnel = TunnelClient(
                    user_id=user_id,
                    api_key=api_key,
                    ws=ws,
                    connected_at=datetime.now(),
                    last_ping=datetime.now()
                )
                self.tunnels[user_id] = tunnel
                
                await ws.send_json({
                    "type": "auth_success",
                    "message": "Tunnel established",
                    "user_id": user_id
                })
                
                logger.info(f"Tunnel established for user: {user_id}")
                
                # Start a background task to send periodic pings
                async def send_pings():
                    try:
                        while not ws.closed:
                            await asyncio.sleep(15)
                            if not ws.closed:
                                await ws.ping()
                    except Exception as e:
                        logger.debug(f"Ping task ended: {e}")
                
                ping_task = asyncio.create_task(send_pings())
                
                # Handle tunnel messages
                try:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                await self._handle_tunnel_message(tunnel, data)
                            except json.JSONDecodeError:
                                logger.error(f"Invalid JSON from tunnel {user_id}: {msg.data}")
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error for {user_id}: {ws.exception()}")
                            break
                finally:
                    ping_task.cancel()
                    try:
                        await ping_task
                    except asyncio.CancelledError:
                        pass
                        
        except asyncio.TimeoutError:
            logger.error("Tunnel authentication timeout")
            await ws.send_json({"type": "error", "error": "Authentication timeout"})
        except Exception as e:
            logger.error(f"Tunnel error: {e}")
        finally:
            # Cleanup tunnel
            if user_id and user_id in self.tunnels:
                del self.tunnels[user_id]
                logger.info(f"Tunnel closed for user: {user_id}")
            await ws.close()
            
        return ws
    
    async def _handle_tunnel_message(self, tunnel: TunnelClient, data: Dict[str, Any]):
        """Handle message from tunnel client."""
        msg_type = data.get('type')
        
        if msg_type == 'ping':
            tunnel.last_ping = datetime.now()
            await tunnel.ws.send_json({"type": "pong"})
            
        elif msg_type == 'response':
            # Response to an MCP request
            request_id = data.get('id')
            if request_id in tunnel.pending_requests:
                future = tunnel.pending_requests[request_id]
                if not future.done():
                    future.set_result(data.get('response'))
                del tunnel.pending_requests[request_id]
            else:
                logger.warning(f"Received response for unknown request: {request_id}")
                
        elif msg_type == 'error':
            # Error response
            request_id = data.get('id')
            if request_id in tunnel.pending_requests:
                future = tunnel.pending_requests[request_id]
                if not future.done():
                    future.set_exception(Exception(data.get('error', 'Unknown error')))
                del tunnel.pending_requests[request_id]
    
    async def handle_mcp_request(self, request: Request) -> Response:
        """Handle MCP JSON-RPC request from client."""
        try:
            # Validate authentication
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return web.json_response(
                    {"error": "Missing or invalid authorization"},
                    status=401
                )
            
            api_key = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Validate API key
            if api_key not in self.api_keys:
                return web.json_response(
                    {"error": "Invalid API key"},
                    status=401
                )
            
            user_id = self.api_keys[api_key]
            
            # Check if tunnel is available
            if user_id not in self.tunnels:
                return web.json_response(
                    {"error": "No active tunnel for this user. Please connect your local client."},
                    status=503
                )
            
            tunnel = self.tunnels[user_id]
            
            if not tunnel.is_alive:
                # Remove stale tunnel
                del self.tunnels[user_id]
                return web.json_response(
                    {"error": "Tunnel timeout. Please reconnect your local client."},
                    status=503
                )
            
            # Parse MCP request
            try:
                mcp_request = await request.json()
            except json.JSONDecodeError:
                return web.json_response(
                    {"error": "Invalid JSON"},
                    status=400
                )
            
            # Generate request ID
            request_id = str(uuid.uuid4())
            
            # Create future for response
            response_future = asyncio.Future()
            tunnel.pending_requests[request_id] = response_future
            
            # Forward request through tunnel
            await tunnel.ws.send_json({
                "type": "request",
                "id": request_id,
                "request": mcp_request
            })
            
            # Wait for response
            try:
                response = await asyncio.wait_for(
                    response_future,
                    timeout=REQUEST_TIMEOUT
                )
                
                # Handle streaming responses
                if request.headers.get('Accept') == 'text/event-stream':
                    # SSE response for streaming
                    response_stream = web.StreamResponse(
                        headers={'Content-Type': 'text/event-stream'}
                    )
                    await response_stream.prepare(request)
                    
                    # Send response as SSE
                    await response_stream.write(f"data: {json.dumps(response)}\n\n".encode())
                    await response_stream.write_eof()
                    return response_stream
                else:
                    # Regular JSON response
                    return web.json_response(response)
                    
            except asyncio.TimeoutError:
                # Cleanup pending request
                if request_id in tunnel.pending_requests:
                    del tunnel.pending_requests[request_id]
                return web.json_response(
                    {"error": "Request timeout"},
                    status=504
                )
            except Exception as e:
                # Cleanup pending request
                if request_id in tunnel.pending_requests:
                    del tunnel.pending_requests[request_id]
                return web.json_response(
                    {"error": str(e)},
                    status=500
                )
                
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return web.json_response(
                {"error": "Internal server error"},
                status=500
            )
    
    async def cleanup_loop(self):
        """Background task to cleanup stale sessions and tunnels."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Cleanup stale sessions
                stale_sessions = [
                    sid for sid, session in self.sessions.items()
                    if not session.is_valid
                ]
                for sid in stale_sessions:
                    del self.sessions[sid]
                
                if stale_sessions:
                    logger.info(f"Cleaned up {len(stale_sessions)} stale sessions")
                
                # Check tunnel health
                for user_id, tunnel in list(self.tunnels.items()):
                    if not tunnel.is_alive:
                        logger.warning(f"Tunnel timeout for user: {user_id}")
                        await tunnel.ws.close()
                        del self.tunnels[user_id]
                        
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def start_background_tasks(self, app):
        """Start background tasks."""
        self.cleanup_task = asyncio.create_task(self.cleanup_loop())
        
    async def cleanup_background_tasks(self, app):
        """Cleanup background tasks on shutdown."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            await self.cleanup_task
    
    def run(self):
        """Run the server."""
        self.app.on_startup.append(self.start_background_tasks)
        self.app.on_cleanup.append(self.cleanup_background_tasks)
        
        logger.info(f"Starting MCP Bridge Server on {HOST}:{PORT}")
        logger.info(f"Configured API keys: {len(self.api_keys)}")
        
        web.run_app(
            self.app,
            host=HOST,
            port=PORT,
            access_log=logger
        )


if __name__ == '__main__':
    server = MCPBridgeServer()
    server.run()
