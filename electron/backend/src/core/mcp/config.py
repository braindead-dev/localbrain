"""
Configuration Management for MCP Server

Manages server settings, tool configurations, and environment-based config.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from loguru import logger


class ServerConfig(BaseModel):
    """Configuration for MCP HTTP/WebSocket server."""
    host: str = Field("127.0.0.1", description="Server host address")
    port: int = Field(8765, ge=1024, le=65535, description="Server port")
    cors_origins: list[str] = Field(
        ["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    max_connections: int = Field(100, ge=1, description="Maximum concurrent connections")
    timeout_seconds: int = Field(30, ge=1, description="Request timeout in seconds")
    enable_websocket: bool = Field(True, description="Enable WebSocket support")


class ToolConfig(BaseModel):
    """Configuration for MCP tools."""
    search_top_k_default: int = Field(10, ge=1, le=100, description="Default number of search results")
    search_top_k_max: int = Field(100, ge=1, le=1000, description="Maximum search results allowed")
    min_similarity_threshold: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    max_file_size_mb: int = Field(50, ge=1, description="Maximum file size for open/summarize (MB)")
    cache_enabled: bool = Field(True, description="Enable result caching")
    cache_ttl_seconds: int = Field(300, ge=0, description="Cache TTL in seconds")


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    enabled: bool = Field(True, description="Enable rate limiting")
    default_limit: int = Field(100, ge=1, description="Default requests per hour")
    window_seconds: int = Field(3600, ge=60, description="Rate limit window in seconds")
    burst_multiplier: float = Field(1.5, ge=1.0, description="Burst allowance multiplier")


class AuditConfig(BaseModel):
    """Configuration for audit logging."""
    enabled: bool = Field(True, description="Enable audit logging")
    log_dir: str = Field("~/.localbrain/logs/mcp", description="Audit log directory")
    max_log_days: int = Field(90, ge=1, description="Maximum days to retain logs")
    log_queries: bool = Field(True, description="Log query strings (sanitized)")
    log_results_count: bool = Field(True, description="Log result counts")


class DatabaseConfig(BaseModel):
    """Configuration for database connections."""
    chroma_api_key: str = Field(..., description="ChromaDB API key")
    chroma_tenant: str = Field("default-tenant", description="ChromaDB tenant")
    chroma_database: str = Field("default-database", description="ChromaDB database")
    collection_name: str = Field("localbrain_chunks", description="ChromaDB collection name")
    embedding_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        description="SentenceTransformer model name"
    )


class MCPConfig(BaseModel):
    """Complete MCP server configuration."""
    vault_path: str = Field(..., description="Path to LocalBrain vault")
    server: ServerConfig = Field(default_factory=ServerConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    database: DatabaseConfig
    auth_config_path: Optional[str] = Field(
        "~/.localbrain/mcp/clients.json",
        description="Path to client authentication config"
    )

    @validator('vault_path')
    def validate_vault_path(cls, v):
        """Ensure vault path is absolute and exists."""
        path = Path(v).expanduser().resolve()  # Ensure canonical absolute path
        if not path.exists():
            logger.warning(f"Vault path does not exist: {path}")
        return str(path)

    class Config:
        """Pydantic config."""
        use_enum_values = True


class ConfigLoader:
    """
    Loads MCP configuration from environment variables and config files.

    Priority:
    1. Environment variables (highest)
    2. Config file
    3. Defaults (lowest)
    """

    @staticmethod
    def load_from_env() -> MCPConfig:
        """
        Load configuration from environment variables.

        Environment variables:
        - VAULT_PATH: Path to vault
        - MCP_HOST: Server host
        - MCP_PORT: Server port
        - CHROMA_API_KEY: ChromaDB API key
        - CHROMA_TENANT: ChromaDB tenant
        - CHROMA_DATABASE: ChromaDB database
        - MCP_AUTH_CONFIG: Path to auth config file
        - MCP_LOG_DIR: Audit log directory
        """
        # --- NEW: Path Resolution Logic ---
        # Project root is 6 .parent calls from config.py file
        # config.py is at: electron/backend/src/core/mcp/config.py
        # Path: config.py -> mcp/ -> core/ -> src/ -> backend/ -> electron/ -> project_root/
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent.resolve()

        vault_path_str = os.getenv("VAULT_PATH")
        if not vault_path_str:
            raise ValueError("VAULT_PATH environment variable required")

        # Expand ~ BEFORE checking if path is absolute
        vault_path = Path(vault_path_str).expanduser()
        if not vault_path.is_absolute():
            # If the path is relative, resolve it from the project root
            vault_path = (project_root / vault_path).resolve()
        else:
            # If already absolute, just resolve to canonical form
            vault_path = vault_path.resolve()
        # --- END NEW LOGIC ---

        chroma_api_key = os.getenv("CHROMA_API_KEY")
        if not chroma_api_key:
            raise ValueError("CHROMA_API_KEY environment variable required")

        # Build config
        config = MCPConfig(
            vault_path=str(vault_path), # Use the resolved absolute path
            server=ServerConfig(
                host=os.getenv("MCP_HOST", "127.0.0.1"),
                port=int(os.getenv("MCP_PORT", "8765")),
                cors_origins=os.getenv("MCP_CORS_ORIGINS", "http://localhost:3000").split(","),
                timeout_seconds=int(os.getenv("MCP_TIMEOUT", "30")),
            ),
            tools=ToolConfig(
                search_top_k_default=int(os.getenv("MCP_SEARCH_TOP_K", "10")),
                cache_enabled=os.getenv("MCP_CACHE_ENABLED", "true").lower() == "true",
                cache_ttl_seconds=int(os.getenv("MCP_CACHE_TTL", "300")),
            ),
            rate_limit=RateLimitConfig(
                enabled=os.getenv("MCP_RATE_LIMIT_ENABLED", "true").lower() == "true",
                default_limit=int(os.getenv("MCP_RATE_LIMIT", "100")),
            ),
            audit=AuditConfig(
                enabled=os.getenv("MCP_AUDIT_ENABLED", "true").lower() == "true",
                log_dir=os.getenv("MCP_LOG_DIR", "~/.localbrain/logs/mcp"),
                max_log_days=int(os.getenv("MCP_AUDIT_DAYS", "90")),
            ),
            database=DatabaseConfig(
                chroma_api_key=chroma_api_key,
                chroma_tenant=os.getenv("CHROMA_TENANT", "default-tenant"),
                chroma_database=os.getenv("CHROMA_DATABASE", "default-database"),
                collection_name=os.getenv("CHROMA_COLLECTION", "localbrain_chunks"),
                embedding_model=os.getenv(
                    "EMBEDDING_MODEL",
                    "sentence-transformers/all-MiniLM-L6-v2"
                ),
            ),
            auth_config_path=os.getenv("MCP_AUTH_CONFIG", "~/.localbrain/mcp/clients.json"),
        )

        logger.info("Loaded MCP configuration from environment")
        return config

    @staticmethod
    def load_from_file(config_path: str) -> MCPConfig:
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to config JSON file

        Returns:
            MCPConfig instance
        """
        import json

        path = Path(config_path).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, 'r') as f:
            data = json.load(f)

        config = MCPConfig(**data)
        logger.info(f"Loaded MCP configuration from {config_path}")
        return config

    @staticmethod
    def load(config_path: Optional[str] = None) -> MCPConfig:
        """
        Load configuration with priority: env vars > file > defaults.

        Args:
            config_path: Optional path to config file

        Returns:
            MCPConfig instance
        """
        # Try loading from file first (if provided)
        if config_path:
            try:
                return ConfigLoader.load_from_file(config_path)
            except Exception as e:
                logger.warning(f"Failed to load from file: {e}, falling back to env vars")

        # Fall back to environment variables
        return ConfigLoader.load_from_env()

    @staticmethod
    def save_to_file(config: MCPConfig, config_path: str):
        """
        Save configuration to JSON file.

        Args:
            config: Configuration to save
            config_path: Output file path
        """
        import json

        path = Path(config_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(config.dict(), f, indent=2, default=str)

        logger.info(f"Saved MCP configuration to {config_path}")


def get_default_config() -> MCPConfig:
    """
    Get default configuration for development.

    Requires VAULT_PATH and CHROMA_API_KEY environment variables.

    Returns:
        Default MCPConfig
    """
    return ConfigLoader.load_from_env()
