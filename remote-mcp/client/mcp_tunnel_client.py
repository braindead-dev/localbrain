#!/usr/bin/env python3
"""
MCP Tunnel Client

This client runs on your local machine and:
1. Connects to the remote bridge server via WebSocket
2. Authenticates with your credentials
3. Forwards MCP requests to your local MCP server (127.0.0.1:8766)
4. Sends responses back through the tunnel

This allows remote MCP clients to access your local vault securely.
"""

import asyncio
import json
import logging
import os
import sys
import signal
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

import aiohttp
from aiohttp import ClientSession, ClientWebSocketResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
REMOTE_SERVER = os.getenv('REMOTE_SERVER', 'ws://146.190.120.44:8767/tunnel')
LOCAL_MCP_SERVER = os.getenv('LOCAL_MCP_SERVER', 'http://127.0.0.1:8766')
USER_ID = os.getenv('USER_ID')
REMOTE_API_KEY = os.getenv('REMOTE_API_KEY')
PING_INTERVAL = int(os.getenv('PING_INTERVAL', '30'))  # seconds
RECONNECT_DELAY = int(os.getenv('RECONNECT_DELAY', '5'))  # seconds
MAX_RECONNECT_ATTEMPTS = int(os.getenv('MAX_RECONNECT_ATTEMPTS', '10'))


class MCPTunnelClient:
    """Tunnel client for forwarding MCP requests."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.ws: Optional[ClientWebSocketResponse] = None
        self.running = False
        self.reconnect_attempts = 0
        self.ping_task = None
        
        # Validate configuration
        if not USER_ID or not REMOTE_API_KEY:
            logger.error("Missing USER_ID or REMOTE_API_KEY in environment")
            logger.error("Please configure your .env file with:")
            logger.error("  USER_ID=<your-unique-user-id>")
            logger.error("  REMOTE_API_KEY=<your-api-key>")
            sys.exit(1)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received, closing tunnel...")
        self.running = False
        asyncio.create_task(self.shutdown())
    
    async def check_local_mcp_server(self) -> bool:
        """Check if local MCP server is running."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{LOCAL_MCP_SERVER}/health"
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"✅ Local MCP server is running: {data.get('status', 'unknown')}")
                        return True
                    else:
                        logger.error(f"Local MCP server returned status {resp.status}")
                        return False
        except aiohttp.ClientError as e:
            logger.error(f"❌ Cannot connect to local MCP server at {LOCAL_MCP_SERVER}")
            logger.error(f"   Error: {e}")
            logger.error("   Please ensure the MCP server is running:")
            logger.error("   cd electron/backend && python src/core/mcp/extension/start_servers.py")
            return False
        except Exception as e:
            logger.error(f"Error checking local MCP server: {e}")
            return False
    
    async def connect(self) -> bool:
        """Connect to remote bridge server."""
        try:
            if self.session is None:
                self.session = ClientSession()
            
            logger.info(f"🔌 Connecting to remote server: {REMOTE_SERVER}")
            
            # Connect WebSocket
            self.ws = await self.session.ws_connect(
                REMOTE_SERVER,
                heartbeat=30,
                autoping=True
            )
            
            # Authenticate
            auth_msg = {
                "type": "auth",
                "user_id": USER_ID,
                "api_key": REMOTE_API_KEY
            }
            
            await self.ws.send_json(auth_msg)
            
            # Wait for authentication response
            auth_response = await asyncio.wait_for(self.ws.receive(), timeout=10)
            if auth_response.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(auth_response.data)
                if data.get('type') == 'auth_success':
                    logger.info(f"✅ Tunnel established successfully!")
                    logger.info(f"   User: {USER_ID}")
                    logger.info(f"   Remote MCP Endpoint: http://146.190.120.44:8767/mcp")
                    logger.info(f"   Authorization: Bearer {REMOTE_API_KEY}")
                    self.reconnect_attempts = 0
                    return True
                else:
                    logger.error(f"Authentication failed: {data.get('error', 'Unknown error')}")
                    return False
            else:
                logger.error("Unexpected response during authentication")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Authentication timeout")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def forward_request_to_local(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Forward MCP request to local server."""
        try:
            async with aiohttp.ClientSession() as session:
                # Forward to local MCP server
                url = f"{LOCAL_MCP_SERVER}/mcp"
                
                # Add timeout for local request
                timeout = aiohttp.ClientTimeout(total=30)
                
                async with session.post(
                    url, 
                    json=request_data,
                    timeout=timeout
                ) as resp:
                    # Check if response has content
                    if resp.status == 202:
                        # Notification (no response expected)
                        return None
                    
                    # Parse JSON response
                    content_type = resp.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        response = await resp.json()
                        return response
                    else:
                        text = await resp.text()
                        logger.error(f"Unexpected content-type: {content_type}, body: {text[:200]}")
                        return {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": f"Invalid response from local server"
                            },
                            "id": request_data.get("id")
                        }
                    
        except aiohttp.ClientError as e:
            logger.error(f"Error forwarding to local MCP server: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Local MCP server error: {str(e)}"
                },
                "id": request_data.get("id")
            }
        except Exception as e:
            logger.error(f"Unexpected error forwarding request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": request_data.get("id")
            }
    
    async def handle_message(self, msg_data: Dict[str, Any]):
        """Handle message from remote server."""
        msg_type = msg_data.get('type')
        
        if msg_type == 'request':
            # Handle MCP request
            request_id = msg_data.get('id')
            request = msg_data.get('request')
            
            logger.debug(f"Received MCP request: {request.get('method', 'unknown')}")
            
            # Forward to local MCP server
            response = await self.forward_request_to_local(request)
            
            # Send response back through tunnel
            await self.ws.send_json({
                "type": "response",
                "id": request_id,
                "response": response
            })
            
            logger.debug(f"Sent response for request {request_id}")
            
        elif msg_type == 'pong':
            logger.debug("Received pong")
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    async def ping_loop(self):
        """Send periodic pings to keep connection alive."""
        while self.running:
            try:
                await asyncio.sleep(PING_INTERVAL)
                if self.ws and not self.ws.closed:
                    await self.ws.send_json({"type": "ping"})
                    logger.debug("Sent ping")
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
    
    async def run(self):
        """Main run loop."""
        self.running = True
        
        # Check local MCP server first
        logger.info("🔍 Checking local MCP server...")
        if not await self.check_local_mcp_server():
            logger.error("Cannot start tunnel without local MCP server")
            return
        
        while self.running:
            try:
                # Connect to remote server
                if not await self.connect():
                    if self.reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                        logger.error(f"Max reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) reached")
                        break
                    
                    self.reconnect_attempts += 1
                    logger.info(f"Reconnecting in {RECONNECT_DELAY} seconds... (attempt {self.reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS})")
                    await asyncio.sleep(RECONNECT_DELAY)
                    continue
                
                # Start ping task
                self.ping_task = asyncio.create_task(self.ping_loop())
                
                # Handle messages
                async for msg in self.ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            await self.handle_message(data)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON received: {msg.data}")
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {self.ws.exception()}")
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logger.warning("WebSocket connection closed")
                        break
                
                # Connection lost
                if self.running:
                    logger.warning("Connection lost, attempting to reconnect...")
                    if self.ping_task:
                        self.ping_task.cancel()
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self.running = False
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if self.running:
                    await asyncio.sleep(RECONNECT_DELAY)
        
        await self.shutdown()
    
    async def shutdown(self):
        """Clean shutdown."""
        logger.info("Shutting down tunnel client...")
        
        self.running = False
        
        if self.ping_task:
            self.ping_task.cancel()
        
        if self.ws:
            await self.ws.close()
        
        if self.session:
            await self.session.close()
        
        logger.info("Tunnel client stopped")


def print_banner():
    """Print startup banner."""
    print("\n" + "="*60)
    print("LocalBrain MCP Tunnel Client")
    print("="*60)
    print(f"User ID: {USER_ID}")
    print(f"Remote Server: {REMOTE_SERVER}")
    print(f"Local MCP Server: {LOCAL_MCP_SERVER}")
    print("="*60 + "\n")


async def main():
    """Main entry point."""
    print_banner()
    
    client = MCPTunnelClient()
    await client.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
