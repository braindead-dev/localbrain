# LocalBrain Extension Server

This is the stdio server component for the LocalBrain Claude Desktop extension.

## Requirements

- Python 3.10+
- LocalBrain FastAPI server running on http://127.0.0.1:8765

## Installation

Dependencies are automatically installed by Claude Desktop when the extension is loaded.

If you need to install manually:

```bash
pip install -r requirements.txt
```

## Usage

This server is launched automatically by Claude Desktop. It acts as a bridge between
Claude's stdio-based MCP protocol and the LocalBrain FastAPI server.

Do not run this directly - it's designed to be launched by Claude Desktop.
