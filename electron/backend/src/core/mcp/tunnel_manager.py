"""
MCP Tunnel Manager

Auto-starts and manages the remote MCP tunnel connection.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional
from loguru import logger


class TunnelManager:
    """Manages the remote MCP tunnel connection"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.tunnel_client_path = self._find_tunnel_client()
    
    def _find_tunnel_client(self) -> Optional[Path]:
        """Find the tunnel client script"""
        # This file is: electron/backend/src/core/mcp/tunnel_manager.py
        # Backend is:   electron/backend/
        # Repo root is: localbrain/
        # Tunnel path:  localbrain/remote-mcp/client/mcp_tunnel_client.py
        
        # Go up to backend dir (3 levels: mcp -> core -> src -> backend)
        backend_dir = Path(__file__).parent.parent.parent.parent
        # Go up to repo root (2 levels: backend -> electron -> localbrain)
        repo_root = backend_dir.parent.parent
        tunnel_path = repo_root / "remote-mcp" / "client" / "mcp_tunnel_client.py"
        
        if tunnel_path.exists():
            return tunnel_path
        
        logger.warning(f"Tunnel client not found at {tunnel_path}")
        return None
    
    def start(self) -> bool:
        """Start the tunnel connection"""
        if self.process and self.process.poll() is None:
            logger.info("Tunnel already running")
            return True
        
        if not self.tunnel_client_path:
            logger.error("Tunnel client not found, cannot start tunnel")
            return False
        
        try:
            logger.info("Starting remote MCP tunnel...")
            
            # Start tunnel client as subprocess
            self.process = subprocess.Popen(
                [sys.executable, str(self.tunnel_client_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=self.tunnel_client_path.parent
            )
            
            logger.info(f"✅ Tunnel started (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start tunnel: {e}")
            return False
    
    def stop(self):
        """Stop the tunnel connection"""
        if not self.process:
            return
        
        logger.info("Stopping remote MCP tunnel...")
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
            logger.info("✅ Tunnel stopped")
        except subprocess.TimeoutExpired:
            logger.warning("Tunnel didn't stop gracefully, forcing...")
            self.process.kill()
        except Exception as e:
            logger.error(f"Error stopping tunnel: {e}")
        finally:
            self.process = None
    
    def is_running(self) -> bool:
        """Check if tunnel is running"""
        return self.process is not None and self.process.poll() is None
    
    def restart(self) -> bool:
        """Restart the tunnel"""
        self.stop()
        return self.start()
