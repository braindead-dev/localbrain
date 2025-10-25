"""
MCP Server Implementation using FastAPI

Provides HTTP and WebSocket endpoints for MCP tools with authentication,
rate limiting, and audit logging.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .models import (
    MCPResponse,
    SearchRequest, SearchAgenticRequest, OpenRequest,
    SummarizeRequest, ListRequest
)
from .tools import MCPTools
from .auth import MCPAuthManager, MCPClientAuth
from .audit import AuditLogger
from .config import MCPConfig


class MCPServer:
    """
    FastAPI-based MCP server.

    Provides endpoints for all MCP tools with authentication,
    authorization, rate limiting, and audit logging.
    """

    def __init__(self, config: MCPConfig):
        """
        Initialize MCP server.

        Args:
            config: Server configuration
        """
        self.config = config
        self.tools: Optional[MCPTools] = None
        self.auth_manager: Optional[MCPAuthManager] = None
        self.audit_logger: Optional[AuditLogger] = None

        # Create FastAPI app with lifespan
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Lifespan context manager for startup/shutdown."""
            # Startup
            await self.startup()
            yield
            # Shutdown
            await self.shutdown()

        self.app = FastAPI(
            title="LocalBrain MCP Server",
            description="Model Context Protocol server for LocalBrain",
            version="1.0.0",
            lifespan=lifespan
        )

        # Setup middleware and routes
        self._setup_middleware()
        self._setup_routes()
        self._setup_exception_handlers()

    async def startup(self):
        """Initialize server components on startup."""
        logger.info("Starting MCP server...")

        # Initialize auth manager
        self.auth_manager = MCPAuthManager(
            config_path=self.config.auth_config_path
        )

        # Initialize audit logger
        if self.config.audit.enabled:
            self.audit_logger = AuditLogger(
                log_dir=self.config.audit.log_dir,
                max_log_days=self.config.audit.max_log_days
            )
        else:
            logger.warning("Audit logging is disabled")

        # Initialize retrieval engine
        from ..retrieval.retrieval import RetrievalEngine

        # If this fails, the server should crash with the real error.
        retrieval_engine = RetrievalEngine(
            vault_path=self.config.vault_path,
            chroma_api_key=self.config.database.chroma_api_key,
            chroma_tenant=self.config.database.chroma_tenant,
            chroma_database=self.config.database.chroma_database,
            embedding_model=self.config.database.embedding_model,
            collection_name=self.config.database.collection_name
        )
        logger.info("Retrieval engine initialized")

        # Initialize MCP tools
        self.tools = MCPTools(
            vault_path=self.config.vault_path,
            retrieval_engine=retrieval_engine,
            llm_client=None  # TODO: Initialize LLM client if needed
        )

        logger.info(f"MCP server ready on {self.config.server.host}:{self.config.server.port}")

    async def shutdown(self):
        """Cleanup on server shutdown."""
        logger.info("Shutting down MCP server...")

        # Cleanup audit logs
        if self.audit_logger:
            self.audit_logger.cleanup_old_logs()

        logger.info("MCP server shutdown complete")

    def _setup_middleware(self):
        """Setup FastAPI middleware."""
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.server.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_exception_handlers(self):
        """Setup global exception handlers."""
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request, exc):
            logger.error(f"Unhandled exception: {exc}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )

    def _setup_routes(self):
        """Setup API routes."""

        # ====================================================================
        # Health Check
        # ====================================================================

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0"
            }

        # ====================================================================
        # MCP Tool Endpoints
        # ====================================================================

        @self.app.post("/mcp/search", response_model=MCPResponse)
        async def search_endpoint(
            request: SearchRequest,
            client: MCPClientAuth = Depends(self._get_current_client),
            request_id: Optional[str] = None
        ):
            """Semantic search tool endpoint."""
            return await self._execute_tool(
                client=client,
                tool="search",
                request=request,
                request_id=request_id
            )

        @self.app.post("/mcp/search_agentic", response_model=MCPResponse)
        async def search_agentic_endpoint(
            request: SearchAgenticRequest,
            client: MCPClientAuth = Depends(self._get_current_client),
            request_id: Optional[str] = None
        ):
            """Agentic search tool endpoint."""
            return await self._execute_tool(
                client=client,
                tool="search_agentic",
                request=request,
                request_id=request_id
            )

        @self.app.post("/mcp/open", response_model=MCPResponse)
        async def open_endpoint(
            request: OpenRequest,
            client: MCPClientAuth = Depends(self._get_current_client),
            request_id: Optional[str] = None
        ):
            """File open tool endpoint."""
            return await self._execute_tool(
                client=client,
                tool="open",
                request=request,
                request_id=request_id
            )

        @self.app.post("/mcp/summarize", response_model=MCPResponse)
        async def summarize_endpoint(
            request: SummarizeRequest,
            client: MCPClientAuth = Depends(self._get_current_client),
            request_id: Optional[str] = None
        ):
            """Summarization tool endpoint."""
            return await self._execute_tool(
                client=client,
                tool="summarize",
                request=request,
                request_id=request_id
            )

        @self.app.post("/mcp/list", response_model=MCPResponse)
        async def list_endpoint(
            request: ListRequest,
            client: MCPClientAuth = Depends(self._get_current_client),
            request_id: Optional[str] = None
        ):
            """Directory listing tool endpoint."""
            return await self._execute_tool(
                client=client,
                tool="list",
                request=request,
                request_id=request_id
            )

        # ====================================================================
        # Admin Endpoints
        # ====================================================================

        @self.app.get("/mcp/stats")
        async def stats_endpoint(
            client: MCPClientAuth = Depends(self._get_current_client)
        ):
            """Get server statistics."""
            if not self.audit_logger:
                return {"error": "Audit logging disabled"}

            return {
                "statistics": self.audit_logger.get_statistics(),
                "performance": self.audit_logger.get_performance_metrics()
            }

        @self.app.get("/mcp/tools")
        async def tools_endpoint():
            """List available MCP tools."""
            return {
                "tools": [
                    {
                        "name": "search",
                        "description": "Natural language search across knowledge base",
                        "input_schema": SearchRequest.schema()
                    },
                    {
                        "name": "search_agentic",
                        "description": "Structured search with filters",
                        "input_schema": SearchAgenticRequest.schema()
                    },
                    {
                        "name": "open",
                        "description": "Retrieve full file contents",
                        "input_schema": OpenRequest.schema()
                    },
                    {
                        "name": "summarize",
                        "description": "Generate file or content summary",
                        "input_schema": SummarizeRequest.schema()
                    },
                    {
                        "name": "list",
                        "description": "List directory contents",
                        "input_schema": ListRequest.schema()
                    }
                ]
            }

    def _get_current_client(
        self,
        x_api_key: Optional[str] = Header(None)
    ) -> MCPClientAuth:
        """
        Dependency to authenticate client and check permissions.

        Args:
            x_api_key: API key from header

        Returns:
            Authenticated client

        Raises:
            HTTPException if authentication fails
        """
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required in X-API-Key header"
            )

        client = self.auth_manager.authenticate(x_api_key)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

        # Check rate limit
        allowed, error = self.auth_manager.check_rate_limit(client)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error
            )

        return client

    async def _execute_tool(
        self,
        client: MCPClientAuth,
        tool: str,
        request: Any,
        request_id: Optional[str]
    ) -> MCPResponse:
        """
        Execute MCP tool with authorization and audit logging.

        Args:
            client: Authenticated client
            tool: Tool name
            request: Tool request object
            request_id: Optional request ID

        Returns:
            MCPResponse with results or error
        """
        start_time = datetime.utcnow()

        # Check permission for this tool
        allowed, error = self.auth_manager.check_permission(client, tool)
        if not allowed:
            # Log denied request
            if self.audit_logger:
                self.audit_logger.log_request(
                    client_id=client.client_id,
                    tool=tool,
                    request_id=request_id,
                    query=None,
                    success=False,
                    error=error,
                    took_ms=0,
                    results_count=0
                )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error
            )

        # Check scope restrictions
        request_params = request.dict()
        allowed, error = self.auth_manager.check_scope_restriction(
            client, tool, request_params
        )
        if not allowed:
            # Log denied request
            if self.audit_logger:
                self.audit_logger.log_request(
                    client_id=client.client_id,
                    tool=tool,
                    request_id=request_id,
                    query=None,
                    success=False,
                    error=error,
                    took_ms=0,
                    results_count=0
                )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error
            )

        # Execute tool
        try:
            # Route to appropriate tool method
            if tool == "search":
                result = await self.tools.search(request)
            elif tool == "search_agentic":
                result = await self.tools.search_agentic(request)
            elif tool == "open":
                result = await self.tools.open(request)
            elif tool == "summarize":
                result = await self.tools.summarize(request)
            elif tool == "list":
                result = await self.tools.list(request)
            else:
                raise ValueError(f"Unknown tool: {tool}")

            # Calculate execution time
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Extract query and result count for logging
            query = getattr(request, 'query', None)
            results_count = getattr(result, 'total', None) or len(getattr(result, 'items', []))

            # Log successful request
            if self.audit_logger:
                self.audit_logger.log_request(
                    client_id=client.client_id,
                    tool=tool,
                    request_id=request_id,
                    query=str(query) if query else None,
                    success=True,
                    error=None,
                    took_ms=elapsed_ms,
                    results_count=results_count
                )

            # Return success response
            return MCPResponse(
                success=True,
                data=result.dict(),
                error=None,
                took_ms=elapsed_ms,
                request_id=request_id
            )

        except Exception as e:
            # Calculate execution time
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Log failed request
            if self.audit_logger:
                self.audit_logger.log_request(
                    client_id=client.client_id,
                    tool=tool,
                    request_id=request_id,
                    query=None,
                    success=False,
                    error=str(e),
                    took_ms=elapsed_ms,
                    results_count=0
                )

            logger.error(f"Tool execution failed: {tool} - {e}")

            return MCPResponse(
                success=False,
                data=None,
                error=str(e),
                took_ms=elapsed_ms,
                request_id=request_id
            )

    def run(self):
        """Run the server using uvicorn."""
        import uvicorn

        uvicorn.run(
            self.app,
            host=self.config.server.host,
            port=self.config.server.port,
            log_level="info",
            timeout_keep_alive=self.config.server.timeout_seconds
        )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from .config import ConfigLoader

    # Path to the .env file in the `electron/backend` directory
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
    
    # Load environment variables from .env file
    # This MUST be done before loading the config
    print(f"Loading environment variables from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)

    # Load configuration
    config = ConfigLoader.load_from_env()

    # Create and run server
    server = MCPServer(config)
    server.run()
