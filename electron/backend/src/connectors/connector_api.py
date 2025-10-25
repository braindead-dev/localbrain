"""
Generic Connector API Routes

Provides unified REST API endpoints for all connectors.
No more hardcoded routes per connector!

All routes follow the pattern: /connectors/{connector_id}/{action}
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional
from pathlib import Path

from .connector_manager import get_connector_manager


def create_connector_router(vault_path: Optional[Path] = None) -> APIRouter:
    """
    Create FastAPI router with generic connector endpoints.
    
    Args:
        vault_path: Path to LocalBrain vault
    
    Returns:
        APIRouter with all connector endpoints
    """
    router = APIRouter(prefix="/connectors", tags=["connectors"])
    manager = get_connector_manager(vault_path=vault_path)
    
    # ========================================================================
    # Discovery & Status
    # ========================================================================
    
    @router.get("")
    async def list_connectors():
        """List all available connectors."""
        try:
            connectors = manager.list_connectors()
            return {
                "success": True,
                "connectors": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "description": c.description,
                        "version": c.version,
                        "auth_type": c.auth_type,
                        "requires_config": c.requires_config,
                        "capabilities": c.capabilities
                    }
                    for c in connectors
                ]
            }
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": str(e)}
            )
    
    @router.get("/{connector_id}/status")
    async def get_connector_status(connector_id: str):
        """Get status of a specific connector."""
        try:
            status = manager.get_status(connector_id)
            
            if not status:
                raise HTTPException(
                    status_code=404,
                    detail=f"Connector {connector_id} not found"
                )
            
            return {
                "success": True,
                "status": {
                    "connected": status.connected,
                    "authenticated": status.authenticated,
                    "last_sync": status.last_sync.isoformat() if status.last_sync else None,
                    "last_error": status.last_error,
                    "total_items_synced": status.total_items_synced,
                    "config_valid": status.config_valid,
                    "metadata": status.metadata
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": str(e)}
            )
    
    # ========================================================================
    # Authentication
    # ========================================================================
    
    @router.post("/{connector_id}/auth")
    async def authenticate_connector(connector_id: str, request: Request):
        """
        Authenticate a connector.
        
        Request body varies by connector auth_type:
        - oauth: {code: string, state: string}
        - api_key: {api_key: string}
        - token: {token: string}
        """
        try:
            data = await request.json()
            success, error = manager.authenticate(connector_id, data)
            
            if success:
                return {"success": True, "message": "Authentication successful"}
            else:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": error}
                )
                
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": str(e)}
            )
    
    @router.post("/{connector_id}/auth/revoke")
    async def revoke_connector_access(connector_id: str):
        """Revoke access and disconnect connector."""
        try:
            success = manager.revoke_access(connector_id)
            
            if success:
                return {"success": True, "message": f"{connector_id} disconnected"}
            else:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "Failed to revoke access"}
                )
                
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": str(e)}
            )
    
    # ========================================================================
    # Sync Operations
    # ========================================================================
    
    @router.post("/{connector_id}/sync")
    async def sync_connector(
        connector_id: str,
        auto_ingest: bool = True,
        limit: Optional[int] = None
    ):
        """
        Trigger sync for a specific connector.
        
        Query parameters:
        - auto_ingest: Whether to automatically ingest fetched data (default: true)
        - limit: Maximum number of items to sync (optional)
        """
        try:
            result = manager.sync_connector(
                connector_id=connector_id,
                auto_ingest=auto_ingest,
                limit=limit
            )
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Connector {connector_id} not found"
                )
            
            return {
                "success": result.success,
                "items_fetched": result.items_fetched,
                "items_ingested": result.items_ingested,
                "errors": result.errors,
                "last_sync": result.last_sync_timestamp.isoformat() if result.last_sync_timestamp else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": str(e)}
            )
    
    @router.post("/sync-all")
    async def sync_all_connectors(auto_ingest: bool = True):
        """Sync all connected connectors."""
        try:
            results = manager.sync_all(auto_ingest=auto_ingest)
            
            return {
                "success": True,
                "results": {
                    connector_id: {
                        "success": result.success,
                        "items_fetched": result.items_fetched,
                        "items_ingested": result.items_ingested,
                        "errors": result.errors
                    }
                    for connector_id, result in results.items()
                }
            }
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": str(e)}
            )
    
    # ========================================================================
    # Connector-Specific Actions (passthrough)
    # ========================================================================
    
    @router.post("/{connector_id}/action/{action_name}")
    async def connector_action(
        connector_id: str,
        action_name: str,
        request: Request
    ):
        """
        Generic passthrough for connector-specific actions.
        
        Allows connectors to expose custom endpoints without hardcoding.
        Example: /connectors/gmail/action/send-email
        """
        try:
            connector = manager.get_connector(connector_id)
            
            if not connector:
                raise HTTPException(
                    status_code=404,
                    detail=f"Connector {connector_id} not found"
                )
            
            # Check if connector has the action method
            if not hasattr(connector, f"action_{action_name}"):
                raise HTTPException(
                    status_code=404,
                    detail=f"Action {action_name} not supported by {connector_id}"
                )
            
            # Get action method
            action_method = getattr(connector, f"action_{action_name}")
            
            # Parse request data
            data = await request.json() if request.headers.get("content-type") == "application/json" else {}
            
            # Execute action
            result = action_method(**data)
            
            return {"success": True, "result": result}
            
        except HTTPException:
            raise
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": str(e)}
            )
    
    return router
