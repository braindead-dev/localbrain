#!/usr/bin/env python3
"""
MCP Tunnel Client

Connects local MCP server to remote MCP-compliant bridge via WebSocket tunnel.
Forwards JSON-RPC 2.0 messages between local MCP server and remote bridge.
"""

import asyncio
import json
import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path

import httpx
import websockets
from loguru import logger
from dotenv import load_dotenv

# Load environment
dotenv_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path)


class MCPTunnelClient:
    """Tunnel client for MCP-compliant bridge"""
    
    def __init__(
        self,
        bridge_url: str,
        local_mcp_url: str,
        user_id: str,
        api_key: str,
        keepalive_interval: int = 30
    ):
        self.bridge_url = bridge_url
        self.local_mcp_url = local_mcp_url
        self.user_id = user_id
        self.api_key = api_key
        self.keepalive_interval = keepalive_interval
        
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.running = False
        self.tunnel_id: Optional[str] = None
        
        logger.info("MCPTunnelClient initialized")
        logger.info(f"  Bridge: {bridge_url}")
        logger.info(f"  Local MCP: {local_mcp_url}")
        logger.info(f"  User ID: {user_id}")
    
    async def connect(self):
        """Connect to bridge server"""
        logger.info("Connecting to MCP bridge...")
        
        # Check local MCP server
        if not await self._check_local_mcp():
            logger.error("❌ Cannot connect to local MCP server")
            logger.error("Please ensure your MCP server is running:")
            logger.error("  cd electron/backend")
            logger.error("  python src/core/mcp/extension/start_servers.py")
            return False
        
        logger.info("✅ Local MCP server is running")
        
        # Connect to bridge
        try:
            self.websocket = await websockets.connect(
                self.bridge_url,
                ping_interval=self.keepalive_interval,
                ping_timeout=10
            )
            
            # Send authentication
            await self.websocket.send(json.dumps({
                "type": "auth",
                "user_id": self.user_id,
                "api_key": self.api_key
            }))
            
            # Wait for confirmation
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "error":
                logger.error(f"❌ Authentication failed: {data.get('message')}")
                return False
            
            if data.get("type") == "connected":
                self.tunnel_id = data.get("tunnel_id")
                remote_url = data.get("remote_url")
                
                logger.info("✅ Tunnel established successfully!")
                logger.info(f"  Tunnel ID: {self.tunnel_id}")
                logger.info(f"  Remote MCP Endpoint: {remote_url}")
                logger.info("")
                logger.info("Your LocalBrain is now accessible via MCP at:")
                logger.info(f"  {remote_url}")
                logger.info("")
                logger.info("Configure MCP clients with:")
                logger.info(f'  "url": "{remote_url}"')
                logger.info(f'  "headers": {{"Authorization": "Bearer {self.api_key}"}}')
                logger.info("")
                
                return True
            
            logger.error(f"❌ Unexpected response: {data}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    async def run(self):
        """Main event loop"""
        if not await self.connect():
            return
        
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        try:
            while self.running:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    logger.info(f"📨 Received from bridge: {data.get('type')}")
                    
                    if data.get("type") == "request":
                        # Forward JSON-RPC request to local MCP server
                        logger.info(f"🔄 Forwarding to local MCP: {data.get('data')}")
                        await self._handle_request(data.get("data"))
                    
                    elif data.get("type") == "ping":
                        await self.websocket.send(json.dumps({"type": "pong"}))
                    
                except websockets.ConnectionClosed:
                    logger.warning("⚠️  Connection closed, reconnecting...")
                    if not await self.connect():
                        break
                
                except Exception as e:
                    logger.error(f"Error in event loop: {e}")
                    await asyncio.sleep(1)
        
        finally:
            await self.cleanup()
    
    async def _handle_request(self, jsonrpc_message: Any):
        """Handle JSON-RPC request from bridge"""
        try:
            # Forward to local MCP server
            # The local server expects JSON-RPC on /mcp endpoint
            response = await self.http_client.post(
                f"{self.local_mcp_url}/mcp",
                json=jsonrpc_message,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": os.getenv("LOCAL_API_KEY", "dev-key-local-only")
                }
            )
            
            # Get response
            if response.status_code == 200:
                result = response.json()
            elif response.status_code == 202:
                # Notification/response only, no result expected
                return
            else:
                # Error - extract ID from first request if batch
                req_id = None
                if isinstance(jsonrpc_message, list) and len(jsonrpc_message) > 0:
                    req_id = jsonrpc_message[0].get("id")
                elif isinstance(jsonrpc_message, dict):
                    req_id = jsonrpc_message.get("id")
                    
                result = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32000,
                        "message": f"Local MCP server error: {response.status_code}"
                    }
                }
            
            # Extract request ID - handle batch vs single
            req_id = None
            if isinstance(jsonrpc_message, list) and len(jsonrpc_message) > 0:
                req_id = jsonrpc_message[0].get("id")
            elif isinstance(jsonrpc_message, dict):
                req_id = jsonrpc_message.get("id")
            
            # Send response back to bridge
            response_msg = {
                "type": "response",
                "request_id": str(req_id) if req_id is not None else None,
                "data": result
            }
            logger.info(f"📤 Sending response to bridge: request_id={response_msg['request_id']}")
            await self.websocket.send(json.dumps(response_msg))
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            
            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "id": jsonrpc_message.get("id") if isinstance(jsonrpc_message, dict) else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            
            try:
                await self.websocket.send(json.dumps({
                    "type": "response",
                    "request_id": str(jsonrpc_message.get("id")) if isinstance(jsonrpc_message, dict) else None,
                    "data": error_response
                }))
            except:
                pass
    
    async def _check_local_mcp(self) -> bool:
        """Check if local MCP server is accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.local_mcp_url}/health")
                return response.status_code == 200
        except:
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up...")
        self.running = False
        
        if self.http_client:
            await self.http_client.aclose()
        
        if self.websocket:
            await self.websocket.close()


async def main():
    """Entry point"""
    # Load config
    bridge_url = os.getenv("BRIDGE_URL", "ws://localhost:8767/tunnel/connect")
    local_mcp_url = os.getenv("LOCAL_MCP_URL", "http://127.0.0.1:8766")
    user_id = os.getenv("USER_ID")
    api_key = os.getenv("REMOTE_API_KEY")
    keepalive = int(os.getenv("KEEPALIVE_INTERVAL", "30"))
    
    if not user_id:
        logger.error("❌ USER_ID not set in .env")
        logger.error("")
        logger.error("Generate one with:")
        logger.error('  python3 -c "import uuid; print(str(uuid.uuid4()))"')
        logger.error("")
        sys.exit(1)
    
    if not api_key:
        logger.error("❌ REMOTE_API_KEY not set in .env")
        logger.error("")
        logger.error("Generate one with:")
        logger.error('  python3 -c "import secrets; print(\'lb_\' + secrets.token_urlsafe(32))"')
        logger.error("")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("LocalBrain MCP Tunnel Client")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Checking local MCP server...")
    
    # Create and run client
    client = MCPTunnelClient(
        bridge_url=bridge_url,
        local_mcp_url=local_mcp_url,
        user_id=user_id,
        api_key=api_key,
        keepalive_interval=keepalive
    )
    
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
