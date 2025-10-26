#!/usr/bin/env python3
"""
Remote MCP Tunnel Client

Runs locally to connect your MCP server to the remote bridge via WebSocket tunnel.
Forwards requests from the bridge to your local MCP server.

Usage:
    python tunnel_client.py
"""

import os
import sys
import asyncio
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional

import httpx
import websockets
from loguru import logger
from dotenv import load_dotenv


# Load environment
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


# ============================================================================
# Configuration
# ============================================================================

# Bridge server configuration
BRIDGE_URL = os.getenv("BRIDGE_URL", "ws://localhost:8767/tunnel/connect")

# Local MCP server configuration
LOCAL_MCP_URL = os.getenv("LOCAL_MCP_URL", "http://127.0.0.1:8766")
LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "dev-key-local-only")

# Tunnel configuration
USER_ID = os.getenv("USER_ID", "")
REMOTE_API_KEY = os.getenv("REMOTE_API_KEY", "")
ALLOWED_TOOLS = os.getenv("ALLOWED_TOOLS", "search,search_agentic,open,summarize,list")

# Keepalive configuration
KEEPALIVE_INTERVAL = int(os.getenv("KEEPALIVE_INTERVAL", "30"))  # seconds

# SSL configuration for wss://
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() == "true"

# Validation
if not USER_ID:
    logger.error("USER_ID not set in environment")
    sys.exit(1)

if not REMOTE_API_KEY:
    logger.error("REMOTE_API_KEY not set in environment")
    sys.exit(1)


# ============================================================================
# Tunnel Client
# ============================================================================

class TunnelClient:
    """
    WebSocket client that maintains tunnel connection to bridge server.

    Forwards requests from bridge to local MCP server.
    """

    def __init__(
        self,
        bridge_url: str,
        local_mcp_url: str,
        local_api_key: str,
        user_id: str,
        remote_api_key: str,
        allowed_tools: str
    ):
        self.bridge_url = bridge_url
        self.local_mcp_url = local_mcp_url
        self.local_api_key = local_api_key
        self.user_id = user_id
        self.remote_api_key = remote_api_key
        self.allowed_tools = allowed_tools

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.running = False
        self.tunnel_id: Optional[str] = None
        self.remote_url: Optional[str] = None

        logger.info("TunnelClient initialized")
        logger.info(f"  Bridge: {bridge_url}")
        logger.info(f"  Local MCP: {local_mcp_url}")
        logger.info(f"  User ID: {user_id}")

    async def start(self):
        """Start the tunnel client."""
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)

        while self.running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"Connection error: {e}")
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def stop(self):
        """Stop the tunnel client."""
        logger.info("Stopping tunnel client...")
        self.running = False

        if self.websocket:
            await self.websocket.close()

        if self.http_client:
            await self.http_client.aclose()

        logger.info("Tunnel client stopped")

    async def _connect(self):
        """Establish WebSocket connection to bridge."""
        # Build connection URL with query params
        url = (
            f"{self.bridge_url}"
            f"?user_id={self.user_id}"
            f"&api_key={self.remote_api_key}"
            f"&allowed_tools={self.allowed_tools}"
        )

        logger.info("Connecting to bridge...")

        # Configure SSL context if using wss://
        ssl_context = None
        if self.bridge_url.startswith("wss://"):
            import ssl
            if not SSL_VERIFY:
                # Disable SSL verification for self-signed certificates
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                logger.warning("SSL certificate verification is disabled.")
            else:
                # Use default SSL context (verifies certificates)
                ssl_context = ssl.create_default_context()
                logger.info("SSL certificate verification enabled.")

        async with websockets.connect(url, ssl=ssl_context) as websocket:
            self.websocket = websocket

            # Wait for confirmation
            message = await websocket.recv()
            import json
            data = json.loads(message)

            if data.get("type") == "connected":
                self.tunnel_id = data.get("tunnel_id")
                self.remote_url = data.get("remote_url")
                logger.info("✅ Tunnel established successfully!")
                logger.info(f"  Tunnel ID: {self.tunnel_id}")
                logger.info(f"  Remote URL: {self.remote_url}")
                logger.info("")
                logger.info("Your LocalBrain is now accessible remotely at:")
                logger.info(f"  {self.remote_url}")
                logger.info("")
                logger.info("External tools can now access your vault using:")
                logger.info(f"  URL: {self.remote_url}/{{tool}}")
                logger.info(f"  API Key: {self.remote_api_key}")
                logger.info("")

            # Start keepalive task
            keepalive_task = asyncio.create_task(self._keepalive())

            try:
                # Handle incoming requests
                while self.running:
                    message = await websocket.recv()
                    data = json.loads(message)

                    # Handle request
                    if data.get("tool"):
                        asyncio.create_task(self._handle_request(data))

            finally:
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except asyncio.CancelledError:
                    pass

    async def _keepalive(self):
        """Send periodic keepalive pings to maintain connection."""
        import json
        while self.running:
            try:
                await asyncio.sleep(KEEPALIVE_INTERVAL)
                if self.websocket:
                    await self.websocket.send(json.dumps({"type": "ping"}))
                    logger.debug("Sent keepalive ping")
            except Exception as e:
                logger.warning(f"Keepalive error: {e}")
                break

    async def _handle_request(self, request_data: dict):
        """
        Handle incoming request from bridge.

        Forward to local MCP server and send response back.
        """
        tool = request_data.get("tool")
        params = request_data.get("params", {})
        request_id = request_data.get("request_id")

        logger.info(f"📥 Received request: {tool} (ID: {request_id})")
        start_time = datetime.utcnow()

        try:
            # Map tool to local MCP endpoint
            endpoint = f"{self.local_mcp_url}/mcp/{tool}"

            # Forward request to local MCP server
            response = await self.http_client.post(
                endpoint,
                json=params,
                headers={"X-API-Key": self.local_api_key}
            )

            response.raise_for_status()
            result_data = response.json()

            # Calculate elapsed time
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Build response
            mcp_response = {
                "success": result_data.get("success", True),
                "data": result_data.get("data"),
                "error": result_data.get("error"),
                "took_ms": elapsed_ms,
                "request_id": request_id
            }

            logger.info(f"✅ Request completed: {tool} ({elapsed_ms:.0f}ms)")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error forwarding request: {e}")
            mcp_response = {
                "success": False,
                "data": None,
                "error": f"HTTP error: {str(e)}",
                "took_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                "request_id": request_id
            }
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            mcp_response = {
                "success": False,
                "data": None,
                "error": str(e),
                "took_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                "request_id": request_id
            }

        # Send response back via WebSocket
        try:
            import json
            await self.websocket.send(json.dumps(mcp_response))
            logger.debug(f"📤 Sent response for request {request_id}")
        except Exception as e:
            logger.error(f"Error sending response: {e}")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run the tunnel client."""
    logger.info("="*60)
    logger.info("LocalBrain Remote MCP Tunnel Client")
    logger.info("="*60)
    logger.info("")

    # Check local MCP server is running
    logger.info("Checking local MCP server...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{LOCAL_MCP_URL}/health", timeout=5.0)
            if response.status_code == 200:
                logger.info("✅ Local MCP server is running")
            else:
                logger.error(f"❌ Local MCP server returned status {response.status_code}")
                logger.error("Please ensure your MCP server is running:")
                logger.error("  cd electron/backend")
                logger.error("  python -m src.core.mcp.server")
                sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Cannot connect to local MCP server: {e}")
        logger.error("Please ensure your MCP server is running:")
        logger.error("  cd electron/backend")
        logger.error("  python -m src.core.mcp.server")
        sys.exit(1)

    logger.info("")
    logger.info("Starting tunnel connection...")
    logger.info("")

    # Create tunnel client
    client = TunnelClient(
        bridge_url=BRIDGE_URL,
        local_mcp_url=LOCAL_MCP_URL,
        local_api_key=LOCAL_API_KEY,
        user_id=USER_ID,
        remote_api_key=REMOTE_API_KEY,
        allowed_tools=ALLOWED_TOOLS
    )

    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        logger.info("\nShutdown signal received...")
        asyncio.create_task(client.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start client
    try:
        await client.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await client.stop()


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    asyncio.run(main())
