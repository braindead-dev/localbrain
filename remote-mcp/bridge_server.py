#!/usr/bin/env python3
"""
Remote MCP Bridge Server

Public-facing relay server that forwards requests to local MCP servers via WebSocket tunnels.
Designed to be deployed on a VPS or cloud service.

Architecture:
    External Tool → Bridge Server → WebSocket Tunnel → Local MCP Server → LocalBrain
"""

import os
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
from loguru import logger
import uvicorn


# ============================================================================
# Configuration
# ============================================================================

BRIDGE_HOST = os.getenv("BRIDGE_HOST", "0.0.0.0")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "8767"))
BRIDGE_SECRET = os.getenv("BRIDGE_SECRET", "change-me-in-production")
MAX_TUNNEL_IDLE_SECONDS = int(os.getenv("MAX_TUNNEL_IDLE_SECONDS", "300"))  # 5 minutes


# ============================================================================
# Models
# ============================================================================

class TunnelRegistration(BaseModel):
    """Request to register a new tunnel."""
    user_id: str = Field(..., description="Unique user identifier")
    api_key: str = Field(..., description="API key for external access")
    allowed_tools: Set[str] = Field(default={"search", "search_agentic", "open", "summarize", "list"})


class TunnelInfo(BaseModel):
    """Information about an active tunnel."""
    tunnel_id: str
    user_id: str
    remote_url: str
    connected_at: datetime
    last_activity: datetime
    requests_count: int


class MCPRequest(BaseModel):
    """Generic MCP request."""
    tool: str
    params: Dict
    request_id: Optional[str] = None


class MCPResponse(BaseModel):
    """Generic MCP response."""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    took_ms: Optional[float] = None
    request_id: Optional[str] = None


# ============================================================================
# Tunnel Manager
# ============================================================================

class TunnelManager:
    """
    Manages WebSocket tunnels to local MCP servers.

    Each tunnel represents a connection from a local MCP instance to this bridge.
    """

    def __init__(self):
        # tunnel_id -> WebSocket connection
        self.tunnels: Dict[str, WebSocket] = {}

        # tunnel_id -> TunnelInfo
        self.tunnel_info: Dict[str, TunnelInfo] = {}

        # user_id -> tunnel_id
        self.user_tunnels: Dict[str, str] = {}

        # api_key -> user_id
        self.api_keys: Dict[str, str] = {}

        # user_id -> allowed_tools
        self.user_permissions: Dict[str, Set[str]] = {}

        # Rate limiting: user_id -> list of request timestamps
        self.rate_limit_buckets: Dict[str, list] = defaultdict(list)

        logger.info("TunnelManager initialized")

    def register_tunnel(
        self,
        websocket: WebSocket,
        user_id: str,
        api_key: str,
        allowed_tools: Set[str]
    ) -> str:
        """Register a new tunnel connection."""
        tunnel_id = str(uuid.uuid4())

        # Close existing tunnel for this user if any
        if user_id in self.user_tunnels:
            old_tunnel_id = self.user_tunnels[user_id]
            if old_tunnel_id in self.tunnels:
                logger.info(f"Closing existing tunnel for user {user_id}")
                # Note: We don't await close here as it might block
                asyncio.create_task(self.tunnels[old_tunnel_id].close())
                del self.tunnels[old_tunnel_id]
                del self.tunnel_info[old_tunnel_id]

        # Register new tunnel
        self.tunnels[tunnel_id] = websocket
        self.user_tunnels[user_id] = tunnel_id
        self.api_keys[api_key] = user_id
        self.user_permissions[user_id] = allowed_tools

        remote_url = f"https://mcp.localbrain.app/u/{user_id}"

        self.tunnel_info[tunnel_id] = TunnelInfo(
            tunnel_id=tunnel_id,
            user_id=user_id,
            remote_url=remote_url,
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            requests_count=0
        )

        logger.info(f"Tunnel registered: {tunnel_id} for user {user_id}")
        return tunnel_id

    def unregister_tunnel(self, tunnel_id: str):
        """Unregister a tunnel connection."""
        if tunnel_id not in self.tunnel_info:
            return

        info = self.tunnel_info[tunnel_id]
        user_id = info.user_id

        # Remove tunnel
        if tunnel_id in self.tunnels:
            del self.tunnels[tunnel_id]

        if tunnel_id in self.tunnel_info:
            del self.tunnel_info[tunnel_id]

        if user_id in self.user_tunnels and self.user_tunnels[user_id] == tunnel_id:
            del self.user_tunnels[user_id]

        # Note: We keep api_keys and user_permissions for reconnection

        logger.info(f"Tunnel unregistered: {tunnel_id}")

    def get_tunnel_by_user(self, user_id: str) -> Optional[WebSocket]:
        """Get active tunnel for a user."""
        tunnel_id = self.user_tunnels.get(user_id)
        if not tunnel_id:
            return None
        return self.tunnels.get(tunnel_id)

    def authenticate_request(self, api_key: str, tool: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Authenticate external request.

        Returns:
            (allowed, user_id, error_message)
        """
        # Verify API key
        user_id = self.api_keys.get(api_key)
        if not user_id:
            return False, None, "Invalid API key"

        # Check if tunnel is active
        if user_id not in self.user_tunnels:
            return False, user_id, "No active tunnel for this user"

        # Check tool permission
        allowed_tools = self.user_permissions.get(user_id, set())
        if tool not in allowed_tools:
            return False, user_id, f"Tool '{tool}' not allowed for this user"

        # Check rate limit (simple: max 60 requests per minute)
        now = datetime.utcnow()
        bucket = self.rate_limit_buckets[user_id]

        # Remove old timestamps (older than 1 minute)
        bucket[:] = [ts for ts in bucket if (now - ts).total_seconds() < 60]

        if len(bucket) >= 60:
            return False, user_id, "Rate limit exceeded (60 requests/minute)"

        # Add current request
        bucket.append(now)

        # Update activity
        tunnel_id = self.user_tunnels[user_id]
        if tunnel_id in self.tunnel_info:
            self.tunnel_info[tunnel_id].last_activity = now
            self.tunnel_info[tunnel_id].requests_count += 1

        return True, user_id, None

    async def forward_request(
        self,
        user_id: str,
        tool: str,
        params: Dict,
        request_id: Optional[str] = None
    ) -> MCPResponse:
        """Forward request to local MCP server via tunnel."""
        tunnel = self.get_tunnel_by_user(user_id)
        if not tunnel:
            return MCPResponse(
                success=False,
                error="No active tunnel",
                request_id=request_id
            )

        try:
            # Send request via WebSocket
            request = MCPRequest(
                tool=tool,
                params=params,
                request_id=request_id or str(uuid.uuid4())
            )

            await tunnel.send_json(request.dict())
            logger.debug(f"Forwarded request to tunnel for user {user_id}: {tool}")

            # Wait for response
            response_data = await tunnel.receive_json()
            response = MCPResponse(**response_data)

            logger.debug(f"Received response from tunnel for user {user_id}")
            return response

        except WebSocketDisconnect:
            logger.warning(f"Tunnel disconnected for user {user_id}")
            self.unregister_tunnel(self.user_tunnels.get(user_id))
            return MCPResponse(
                success=False,
                error="Tunnel disconnected",
                request_id=request_id
            )
        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            return MCPResponse(
                success=False,
                error=str(e),
                request_id=request_id
            )

    def get_all_tunnels(self) -> list[TunnelInfo]:
        """Get info about all active tunnels."""
        return list(self.tunnel_info.values())

    async def cleanup_idle_tunnels(self):
        """Close tunnels that have been idle too long."""
        now = datetime.utcnow()
        max_idle = timedelta(seconds=MAX_TUNNEL_IDLE_SECONDS)

        to_remove = []
        for tunnel_id, info in self.tunnel_info.items():
            if now - info.last_activity > max_idle:
                logger.info(f"Closing idle tunnel: {tunnel_id}")
                to_remove.append(tunnel_id)

        for tunnel_id in to_remove:
            if tunnel_id in self.tunnels:
                await self.tunnels[tunnel_id].close()
            self.unregister_tunnel(tunnel_id)


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="LocalBrain Remote MCP Bridge",
    description="Public relay for LocalBrain MCP servers",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global tunnel manager
tunnel_manager = TunnelManager()


# ============================================================================
# Background Tasks
# ============================================================================

async def cleanup_task():
    """Background task to cleanup idle tunnels."""
    while True:
        await asyncio.sleep(60)  # Run every minute
        await tunnel_manager.cleanup_idle_tunnels()


@app.on_event("startup")
async def startup_event():
    """Start background tasks."""
    asyncio.create_task(cleanup_task())
    logger.info("Bridge server started")


# ============================================================================
# Admin Endpoints (Protected by BRIDGE_SECRET)
# ============================================================================

def verify_admin(x_admin_secret: Optional[str] = Header(None)) -> bool:
    """Verify admin access."""
    if x_admin_secret != BRIDGE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin secret"
        )
    return True


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_tunnels": len(tunnel_manager.tunnels)
    }


@app.get("/admin/tunnels", dependencies=[Depends(verify_admin)])
async def list_tunnels():
    """List all active tunnels (admin only)."""
    return {
        "tunnels": [info.dict() for info in tunnel_manager.get_all_tunnels()]
    }


@app.post("/admin/tunnel/{user_id}/revoke", dependencies=[Depends(verify_admin)])
async def revoke_tunnel(user_id: str):
    """Revoke a user's tunnel (admin only)."""
    tunnel_id = tunnel_manager.user_tunnels.get(user_id)
    if not tunnel_id:
        raise HTTPException(status_code=404, detail="Tunnel not found")

    if tunnel_id in tunnel_manager.tunnels:
        await tunnel_manager.tunnels[tunnel_id].close()

    tunnel_manager.unregister_tunnel(tunnel_id)

    return {"success": True, "message": f"Tunnel revoked for user {user_id}"}


# ============================================================================
# Tunnel WebSocket Endpoint
# ============================================================================

@app.websocket("/tunnel/connect")
async def tunnel_connect(
    websocket: WebSocket,
    user_id: str,
    api_key: str,
    allowed_tools: str = "search,search_agentic,open,summarize,list"
):
    """
    WebSocket endpoint for local MCP servers to connect.

    Query params:
        user_id: Unique user identifier
        api_key: API key for external access
        allowed_tools: Comma-separated list of allowed tools
    """
    await websocket.accept()

    try:
        # Parse allowed tools
        tools_set = set(tool.strip() for tool in allowed_tools.split(","))

        # Register tunnel
        tunnel_id = tunnel_manager.register_tunnel(
            websocket=websocket,
            user_id=user_id,
            api_key=api_key,
            allowed_tools=tools_set
        )

        info = tunnel_manager.tunnel_info[tunnel_id]

        # Send confirmation
        await websocket.send_json({
            "type": "connected",
            "tunnel_id": tunnel_id,
            "remote_url": info.remote_url,
            "message": "Tunnel established successfully"
        })

        logger.info(f"Tunnel connected: {tunnel_id} for user {user_id}")

        # Keep connection alive and handle keepalive pings
        while True:
            try:
                # Wait for messages (mostly keepalive pings from client)
                message = await websocket.receive_json()

                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    # Update last activity
                    if tunnel_id in tunnel_manager.tunnel_info:
                        tunnel_manager.tunnel_info[tunnel_id].last_activity = datetime.utcnow()

            except WebSocketDisconnect:
                logger.info(f"Tunnel disconnected: {tunnel_id}")
                break
            except Exception as e:
                logger.error(f"Error in tunnel connection: {e}")
                break

    finally:
        tunnel_manager.unregister_tunnel(tunnel_id)


# ============================================================================
# Public MCP Endpoints (for external tools)
# ============================================================================

@app.post("/u/{user_id}/search")
async def public_search(
    user_id: str,
    request: Dict,
    x_api_key: Optional[str] = Header(None)
):
    """Public search endpoint."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    allowed, auth_user_id, error = tunnel_manager.authenticate_request(x_api_key, "search")
    if not allowed or auth_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error or "Unauthorized"
        )

    response = await tunnel_manager.forward_request(
        user_id=user_id,
        tool="search",
        params=request,
        request_id=request.get("request_id")
    )

    return response.dict()


@app.post("/u/{user_id}/search_agentic")
async def public_search_agentic(
    user_id: str,
    request: Dict,
    x_api_key: Optional[str] = Header(None)
):
    """Public agentic search endpoint."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    allowed, auth_user_id, error = tunnel_manager.authenticate_request(x_api_key, "search_agentic")
    if not allowed or auth_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error or "Unauthorized"
        )

    response = await tunnel_manager.forward_request(
        user_id=user_id,
        tool="search_agentic",
        params=request,
        request_id=request.get("request_id")
    )

    return response.dict()


@app.post("/u/{user_id}/open")
async def public_open(
    user_id: str,
    request: Dict,
    x_api_key: Optional[str] = Header(None)
):
    """Public file open endpoint."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    allowed, auth_user_id, error = tunnel_manager.authenticate_request(x_api_key, "open")
    if not allowed or auth_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error or "Unauthorized"
        )

    response = await tunnel_manager.forward_request(
        user_id=user_id,
        tool="open",
        params=request,
        request_id=request.get("request_id")
    )

    return response.dict()


@app.post("/u/{user_id}/summarize")
async def public_summarize(
    user_id: str,
    request: Dict,
    x_api_key: Optional[str] = Header(None)
):
    """Public summarize endpoint."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    allowed, auth_user_id, error = tunnel_manager.authenticate_request(x_api_key, "summarize")
    if not allowed or auth_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error or "Unauthorized"
        )

    response = await tunnel_manager.forward_request(
        user_id=user_id,
        tool="summarize",
        params=request,
        request_id=request.get("request_id")
    )

    return response.dict()


@app.post("/u/{user_id}/list")
async def public_list(
    user_id: str,
    request: Dict,
    x_api_key: Optional[str] = Header(None)
):
    """Public list endpoint."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    allowed, auth_user_id, error = tunnel_manager.authenticate_request(x_api_key, "list")
    if not allowed or auth_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error or "Unauthorized"
        )

    response = await tunnel_manager.forward_request(
        user_id=user_id,
        tool="list",
        params=request,
        request_id=request.get("request_id")
    )

    return response.dict()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Start the bridge server."""
    logger.info("="*60)
    logger.info("LocalBrain Remote MCP Bridge Starting...")
    logger.info("="*60)
    logger.info(f"Host: {BRIDGE_HOST}")
    logger.info(f"Port: {BRIDGE_PORT}")
    logger.info("")
    logger.info("Tunnel endpoint: ws://<host>:<port>/tunnel/connect")
    logger.info("Public endpoints: /u/{user_id}/{tool}")
    logger.info("="*60)

    uvicorn.run(
        app,
        host=BRIDGE_HOST,
        port=BRIDGE_PORT,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
