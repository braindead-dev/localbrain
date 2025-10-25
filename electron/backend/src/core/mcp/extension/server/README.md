# LocalBrain Extension Server

This is the stdio server component for the LocalBrain Claude Desktop extension.

## Requirements

- Python 3.10+
- LocalBrain Electron app running (auto-starts both services):
  - Daemon on http://127.0.0.1:8765
  - MCP FastAPI server on http://127.0.0.1:8766
- Vault path configured in ~/.localbrain/config.json

## Installation

Dependencies are automatically installed by Claude Desktop when the extension is loaded.

If you need to install manually:

```bash
pip install -r requirements.txt
```

## Usage

This server is launched automatically by Claude Desktop. It acts as a bridge between
Claude's stdio-based MCP protocol and the LocalBrain MCP FastAPI server (port 8766),
which in turn forwards requests to the daemon (port 8765).

Do not run this directly - it's designed to be launched by Claude Desktop.
