# LocalBrain Extension - Quick Installation Guide

Get Claude Desktop connected to your LocalBrain vault in 5 minutes.

## Prerequisites

- Python 3.10+
- Claude Desktop installed
- LocalBrain vault set up
- ChromaDB Cloud account (free tier works)

---

## Step 1: Install Dependencies

```bash
cd electron/backend
pip install -r requirements.txt
```

This installs the MCP SDK and all required packages.

---

## Step 2: Configure Environment

Create your `.env` file:

```bash
cp src/core/mcp/examples/.env.example .env
```

Edit `.env` and set:

```env
VAULT_PATH=my-vault                    # Or absolute path
CHROMA_API_KEY=your_chroma_api_key_here
CHROMA_TENANT=default-tenant
CHROMA_DATABASE=default-database
```

---

## Step 3: Start FastAPI Server

Open a terminal and keep it running:

```bash
python -m src.core.mcp.server
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8765
MCP server ready on 127.0.0.1:8765
```

**Keep this terminal open!** The server must run in the background.

---

## Step 4: Build Extension

In a new terminal:

```bash
cd electron/backend/src/core/mcp/extension
./package.sh
```

This creates `localbrain.mcpb` (~15 KB).

---

## Step 5: Install in Claude Desktop

1. Open Claude Desktop
2. **Drag `localbrain.mcpb`** into the Claude Desktop window
3. Click **"Install"** when prompted
4. Configure the extension:
   - **Vault Directory:** Browse to your vault (e.g., `/Users/you/Projects/localbrain/my-vault`)
   - **ChromaDB API Key:** Enter your ChromaDB Cloud API key
   - Leave other fields at default
5. Click **"Save"**

---

## Step 6: Verify

Look for the **🔨 hammer icon** in the bottom-right corner of Claude Desktop.

Try this in Claude:

```
Search my vault for "test"
```

If Claude responds with results, you're all set! 🎉

---

## Troubleshooting

### "Cannot connect to FastAPI server"

- Ensure the FastAPI server is running (Step 3)
- Check: `curl http://localhost:8765/health`

### "No hammer icon appears"

- Restart Claude Desktop completely
- Check **Settings** → **Developer** → **View Logs**

### "Vault path not found"

- Use absolute path (not `~` or relative)
- Example: `/Users/yourname/Projects/localbrain/my-vault`

---

## Next Steps

See [Extension.md](../Extension.md) for:
- Detailed configuration options
- All available tools
- Development and debugging tips
- Manifest customization

---

**Need help?** Check the [troubleshooting section](../Extension.md#troubleshooting) in Extension.md.
