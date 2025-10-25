#!/usr/bin/env python3
"""
LocalBrain Menu Tray Application

Runs in the macOS menu bar and manages the background daemon.
Shows status, recent activity, and controls for the service.

Dependencies:
    pip install rumps requests

Usage:
    python src/tray.py
"""

import sys
import subprocess
import requests
import threading
import time
from pathlib import Path

try:
    import rumps
except ImportError:
    print("Error: rumps not installed. Install with: pip install rumps")
    sys.exit(1)

# Configuration
DAEMON_PORT = 8765
DAEMON_URL = f"http://127.0.0.1:{DAEMON_PORT}"


class LocalBrainTray(rumps.App):
    """Menu tray application for LocalBrain."""
    
    def __init__(self):
        super(LocalBrainTray, self).__init__(
            "LocalBrain",
            icon=None,  # You can add an icon path here
            quit_button=None  # Custom quit button
        )
        
        self.daemon_process = None
        self.status_item = rumps.MenuItem("Status: Checking...", callback=None)
        self.separator1 = rumps.separator
        self.start_item = rumps.MenuItem("Start Service", callback=self.start_daemon)
        self.stop_item = rumps.MenuItem("Stop Service", callback=self.stop_daemon)
        self.separator2 = rumps.separator
        self.recent_item = rumps.MenuItem("Recent Ingestions", callback=None)
        self.separator3 = rumps.separator
        self.quit_item = rumps.MenuItem("Quit LocalBrain", callback=self.quit_app)
        
        self.menu = [
            self.status_item,
            self.separator1,
            self.start_item,
            self.stop_item,
            self.separator2,
            self.recent_item,
            self.separator3,
            self.quit_item
        ]
        
        # Start status checker thread
        self.running = True
        self.status_thread = threading.Thread(target=self.check_status_loop, daemon=True)
        self.status_thread.start()
        
        # Auto-start daemon
        self.start_daemon(None)
    
    def check_daemon_status(self):
        """Check if daemon is running."""
        try:
            response = requests.get(f"{DAEMON_URL}/health", timeout=1)
            return response.status_code == 200
        except:
            return False
    
    def check_status_loop(self):
        """Background thread to check daemon status."""
        while self.running:
            is_running = self.check_daemon_status()
            
            if is_running:
                self.status_item.title = "Status: ✅ Running"
                self.start_item.set_callback(None)  # Disable
                self.stop_item.set_callback(self.stop_daemon)  # Enable
            else:
                self.status_item.title = "Status: ⚠️ Stopped"
                self.start_item.set_callback(self.start_daemon)  # Enable
                self.stop_item.set_callback(None)  # Disable
            
            time.sleep(5)  # Check every 5 seconds
    
    def start_daemon(self, sender):
        """Start the background daemon."""
        if self.daemon_process is None or self.daemon_process.poll() is not None:
            backend_dir = Path(__file__).parent.parent
            daemon_script = backend_dir / "src" / "daemon.py"
            
            # Start daemon as subprocess
            self.daemon_process = subprocess.Popen(
                [sys.executable, str(daemon_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(backend_dir)
            )
            
            rumps.notification(
                title="LocalBrain",
                subtitle="Service Started",
                message="Background daemon is now running"
            )
    
    def stop_daemon(self, sender):
        """Stop the background daemon."""
        if self.daemon_process and self.daemon_process.poll() is None:
            self.daemon_process.terminate()
            self.daemon_process.wait(timeout=5)
            self.daemon_process = None
            
            rumps.notification(
                title="LocalBrain",
                subtitle="Service Stopped",
                message="Background daemon has been stopped"
            )
    
    def quit_app(self, sender):
        """Quit the tray application."""
        self.running = False
        if self.daemon_process:
            self.stop_daemon(None)
        rumps.quit_application()


def main():
    """Start the tray application."""
    app = LocalBrainTray()
    app.run()


if __name__ == "__main__":
    main()
