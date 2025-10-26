# Quick Start Guide

**Get LocalBrain running in 5 minutes**

---

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/localbrain.git
cd localbrain
```

### 2. Backend Setup

```bash
cd electron/backend

# Install dependencies
pip install -r requirements.txt

# Create config directory
mkdir -p ~/.localbrain

# Set vault path
echo '{
  "vault_path": "/path/to/your/vault",
  "port": 8765,
  "auto_start": false
}' > ~/.localbrain/config.json

# Add API key
export ANTHROPIC_API_KEY="your-key-here"
```

### 3. Create Test Vault

```bash
# Create a test vault
mkdir -p ~/my-vault/notes
echo "# My First Note\nThis is a test note about machine learning." > ~/my-vault/notes/ml.md
echo "# Work Notes\nProject deadline is next Friday." > ~/my-vault/notes/work.md

# Update config to point to it
echo '{
  "vault_path": "'$HOME'/my-vault",
  "port": 8765
}' > ~/.localbrain/config.json
```

### 4. Start Backend

```bash
python src/daemon.py
```

You should see:
```
============================================================
LocalBrain Background Daemon Starting...
============================================================
Vault: /Users/you/my-vault
Port: 8765
```

---

## First Search

Open a new terminal and test search:

```bash
curl -X POST http://localhost:8765/protocol/search \
  -H "Content-Type: application/json" \
  -d '{"q": "machine learning"}'
```

Expected response:
```json
{
  "success": true,
  "contexts": [
    {
      "file": "notes/ml.md",
      "text": "# My First Note\nThis is a test note about machine learning.",
      "citations": []
    }
  ],
  "total_results": 1
}
```

**It works!** 🎉

---

## Frontend Setup (Optional)

### 1. Install Dependencies

```bash
cd ../app
npm install
```

### 2. Start Dev Server

```bash
npm run dev
```

### 3. Open Browser

Navigate to http://localhost:3000

You'll see the LocalBrain web interface!

---

## Claude Desktop Integration

### 1. Build Extension

```bash
cd ../backend/src/core/mcp/extension
bash package.sh
```

### 2. Install in Claude

1. Open Claude Desktop
2. Settings → Extensions
3. Drag `localbrain.mcpb` into window
4. Use API key: `dev-key-local-only`
5. Enable extension

### 3. Test

Ask Claude: "Search my vault for machine learning"

Claude will use the LocalBrain extension to search your vault!

---

## Add More Content

### Method 1: Manual

Just create markdown files in your vault:

```bash
echo "# Meeting Notes\nDiscussed Q4 roadmap." > ~/my-vault/notes/meeting.md
```

### Method 2: Connectors

Connect Gmail to sync emails:

```bash
# Start backend
python src/daemon.py

# In another terminal, trigger Gmail OAuth
curl -X POST http://localhost:8765/connectors/gmail/auth/start

# Follow the auth URL
# Emails will sync automatically every 10 minutes
```

---

## Next Steps

### Explore the Docs
- [Architecture](ARCHITECTURE.md) - How it works
- [Search System](SEARCH.md) - Agentic search details
- [Connectors](CONNECTORS.md) - Add data sources
- [MCP Extension](MCP.md) - Claude Desktop integration

### Try Advanced Features
- Set up Discord connector
- Create custom connector
- Build a React component
- Deploy on a server

### Get Help
- [GitHub Issues](https://github.com/yourusername/localbrain/issues)
- [Discussions](https://github.com/yourusername/localbrain/discussions)
- Email: support@localbrain.dev

---

## Troubleshooting

### "Connection refused"
**Problem**: Backend not running  
**Solution**: Run `python src/daemon.py`

### "No results found"
**Problem**: Vault path incorrect  
**Solution**: Check `~/.localbrain/config.json` has correct path

### "API key missing"
**Problem**: ANTHROPIC_API_KEY not set  
**Solution**: `export ANTHROPIC_API_KEY="your-key"`

### Search is slow
**Normal!** Agentic search makes 2-4 API calls  
Typical time: 2-4 seconds

---

## Configuration Files

### ~/.localbrain/config.json
```json
{
  "vault_path": "/path/to/vault",
  "port": 8765,
  "auto_start": false
}
```

### Environment Variables
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export MCP_API_KEY="dev-key-local-only"
```

---

## What's Next?

You now have:
- ✅ LocalBrain daemon running
- ✅ Test vault with content
- ✅ Successful search
- ✅ (Optional) Web interface
- ✅ (Optional) Claude Desktop extension

**Ready to use!** Start adding your content and searching. 🚀
