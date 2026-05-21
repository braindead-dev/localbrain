#!/usr/bin/env python3
"""
LocalBrain Server Launcher

Starts both the daemon backend and MCP server, and gracefully shuts down both when stopped.

Usage:
    python start_servers.py              # Interactive mode
    python start_servers.py --stdio      # Claude Desktop mode (auto-starts servers + stdio bridge)

Stop with Ctrl+C to cleanly shut down both servers.

Claude Desktop config (~/.config/claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "localbrain": {
          "command": "python",
          "args": ["/absolute/path/to/localbrain/electron/backend/src/core/mcp/extension/start_servers.py", "--stdio"]
        }
      }
    }
"""

import sys
import signal
import subprocess
import time
import argparse
from pathlib import Path


class ServerLauncher:
    """Manages starting and stopping daemon and MCP server."""

    def __init__(self, stdio_mode=False):
        self.daemon_process = None
        self.mcp_process = None
        self.stdio_process = None
        self.stdio_mode = stdio_mode
        self.running = True

        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle interrupt signals (Ctrl+C, etc.)."""
        print("\n\n🛑 Shutdown signal received, stopping servers...")
        self.running = False
        self.stop_servers()
        sys.exit(0)

    def start_daemon(self):
        """Start the daemon backend server."""
        print("🚀 Starting daemon backend on port 8765...")
        try:
            self.daemon_process = subprocess.Popen(
                [sys.executable, "src/daemon.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            print("✅ Daemon started (PID: {})".format(self.daemon_process.pid))
            return True
        except Exception as e:
            print(f"❌ Failed to start daemon: {e}")
            return False

    def start_mcp_server(self):
        """Start the MCP server."""
        print("🚀 Starting MCP server on port 8766...")
        try:
            self.mcp_process = subprocess.Popen(
                [sys.executable, "-m", "src.core.mcp.server"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            print("✅ MCP server started (PID: {})".format(self.mcp_process.pid))
            return True
        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}")
            return False

    def start_stdio_server(self):
        """Start the stdio bridge (foreground process for Claude Desktop)."""
        print("🚀 Starting stdio bridge for Claude Desktop...", file=sys.stderr)
        try:
            # Run stdio server in foreground - it will handle stdin/stdout communication
            self.stdio_process = subprocess.Popen(
                [sys.executable, "src/core/mcp/stdio_server.py"],
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            print("✅ Stdio bridge started (PID: {})".format(self.stdio_process.pid), file=sys.stderr)
            return True
        except Exception as e:
            print(f"❌ Failed to start stdio bridge: {e}", file=sys.stderr)
            return False

    def stop_servers(self):
        """Stop all servers gracefully."""
        # Stop stdio bridge (if running)
        if self.stdio_process:
            print("🛑 Stopping stdio bridge...", file=sys.stderr)
            try:
                self.stdio_process.terminate()
                self.stdio_process.wait(timeout=5)
                print("✅ Stdio bridge stopped", file=sys.stderr)
            except subprocess.TimeoutExpired:
                print("⚠️  Stdio bridge didn't stop gracefully, forcing...", file=sys.stderr)
                self.stdio_process.kill()
            except Exception as e:
                print(f"❌ Error stopping stdio bridge: {e}", file=sys.stderr)

        # Stop MCP server
        if self.mcp_process:
            print("🛑 Stopping MCP server...", file=sys.stderr)
            try:
                self.mcp_process.terminate()
                self.mcp_process.wait(timeout=5)
                print("✅ MCP server stopped", file=sys.stderr)
            except subprocess.TimeoutExpired:
                print("⚠️  MCP server didn't stop gracefully, forcing...", file=sys.stderr)
                self.mcp_process.kill()
            except Exception as e:
                print(f"❌ Error stopping MCP server: {e}", file=sys.stderr)

        # Stop daemon
        if self.daemon_process:
            print("🛑 Stopping daemon...", file=sys.stderr)
            try:
                self.daemon_process.terminate()
                self.daemon_process.wait(timeout=5)
                print("✅ Daemon stopped", file=sys.stderr)
            except subprocess.TimeoutExpired:
                print("⚠️  Daemon didn't stop gracefully, forcing...", file=sys.stderr)
                self.daemon_process.kill()
            except Exception as e:
                print(f"❌ Error stopping daemon: {e}", file=sys.stderr)

    def monitor_processes(self):
        """Monitor both processes and restart if they crash."""
        while self.running:
            # Check daemon
            if self.daemon_process and self.daemon_process.poll() is not None:
                print("\n❌ Daemon process died unexpectedly!")
                # Show stderr if available
                if self.daemon_process.stderr:
                    stderr = self.daemon_process.stderr.read()
                    if stderr:
                        print(f"Daemon error output:\n{stderr}")
                self.stop_servers()
                sys.exit(1)

            # Check MCP server
            if self.mcp_process and self.mcp_process.poll() is not None:
                print("\n❌ MCP server process died unexpectedly!")
                # Show stderr if available
                if self.mcp_process.stderr:
                    stderr = self.mcp_process.stderr.read()
                    if stderr:
                        print(f"MCP server error output:\n{stderr}")
                if self.mcp_process.stdout:
                    stdout = self.mcp_process.stdout.read()
                    if stdout:
                        print(f"MCP server stdout:\n{stdout}")
                self.stop_servers()
                sys.exit(1)

            time.sleep(1)

    def run(self):
        """Start servers and monitor them."""
        if self.stdio_mode:
            return self._run_stdio_mode()
        else:
            return self._run_interactive_mode()

    def _run_interactive_mode(self):
        """Run in interactive mode (terminal output)."""
        print("=" * 70)
        print("LocalBrain Server Launcher")
        print("=" * 70)
        print()

        # Start daemon first (MCP depends on it)
        if not self.start_daemon():
            print("\n❌ Failed to start daemon. Exiting.")
            return False

        # Wait a moment for daemon to initialize
        print("⏳ Waiting for daemon to initialize...")
        time.sleep(2)

        # Start MCP server
        if not self.start_mcp_server():
            print("\n❌ Failed to start MCP server. Stopping daemon...")
            self.stop_servers()
            return False

        # Wait a moment for MCP server to initialize
        print("⏳ Waiting for MCP server to initialize...")
        time.sleep(2)

        print()
        print("=" * 70)
        print("✅ LocalBrain MCP Ready!")
        print("=" * 70)
        print()
        print("🌐 Daemon:       http://127.0.0.1:8765")
        print("🌐 MCP Server:   http://127.0.0.1:8766")
        print()
        print("📝 Press Ctrl+C to stop all servers")
        print("=" * 70)
        print()

        # Monitor processes
        try:
            self.monitor_processes()
        except KeyboardInterrupt:
            # This is caught by signal handler, but just in case
            pass

        return True

    def _run_stdio_mode(self):
        """Run in stdio mode for Claude Desktop integration."""
        # Start background servers silently
        print("🚀 LocalBrain starting in stdio mode...", file=sys.stderr)

        # Start daemon
        if not self.start_daemon():
            print("❌ Failed to start daemon", file=sys.stderr)
            return False

        print("⏳ Waiting for daemon to initialize...", file=sys.stderr)
        time.sleep(2)

        # Start MCP HTTP server
        if not self.start_mcp_server():
            print("❌ Failed to start MCP server", file=sys.stderr)
            self.stop_servers()
            return False

        print("⏳ Waiting for MCP server to initialize...", file=sys.stderr)
        time.sleep(2)

        # Start stdio bridge (foreground)
        print("✅ Background servers ready, starting stdio bridge...", file=sys.stderr)
        if not self.start_stdio_server():
            print("❌ Failed to start stdio bridge", file=sys.stderr)
            self.stop_servers()
            return False

        # Wait for stdio process to complete
        try:
            self.stdio_process.wait()
        except KeyboardInterrupt:
            pass
        finally:
            # Clean up background servers
            print("🛑 Cleaning up background servers...", file=sys.stderr)
            self.stop_servers()

        return True


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="LocalBrain Server Launcher - Starts daemon and MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_servers.py              # Interactive mode for terminal use
  python start_servers.py --stdio      # Stdio mode for Claude Desktop integration

For Claude Desktop integration, add to claude_desktop_config.json:
  {
    "mcpServers": {
      "localbrain": {
        "command": "python",
        "args": ["/absolute/path/to/extension/start_servers.py", "--stdio"],
        "env": {
          "VAULT_PATH": "/path/to/your/vault"
        }
      }
    }
  }
        """
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run in stdio mode for Claude Desktop (auto-starts all servers)"
    )

    args = parser.parse_args()

    # Determine backend directory based on script location
    # Script is in: electron/backend/src/core/mcp/extension/start_servers.py
    # Backend is:   electron/backend/
    script_path = Path(__file__).resolve()
    backend_dir = script_path.parent.parent.parent.parent.parent

    # Change to backend directory
    import os
    original_dir = Path.cwd()
    os.chdir(backend_dir)

    # Verify we're in the right place
    if not Path("src/daemon.py").exists():
        print("❌ Error: Cannot locate daemon.py", file=sys.stderr)
        print(f"   Script location: {script_path}", file=sys.stderr)
        print(f"   Expected backend: {backend_dir}", file=sys.stderr)
        print(f"   Current directory: {Path.cwd()}", file=sys.stderr)
        sys.exit(1)

    launcher = ServerLauncher(stdio_mode=args.stdio)
    success = launcher.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
