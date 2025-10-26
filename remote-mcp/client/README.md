# MCP Tunnel Client

This client runs on your local machine and creates a secure tunnel to the remote bridge server.

## Quick Start

### 1. Generate credentials

```bash
# Generate unique user ID
python3 -c "import uuid; print(str(uuid.uuid4()))"
# Example output: a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Generate secure API key
python3 -c "import secrets; print('lb_' + secrets.token_urlsafe(32))"
# Example output: lb_abc123xyz789_secure_random_string
```

### 2. Configure client

```bash
cd client
cp .env.example .env
nano .env
```

Add your credentials:
```env
USER_ID=a1b2c3d4-e5f6-7890-abcd-ef1234567890
REMOTE_API_KEY=lb_abc123xyz789_secure_random_string
```

### 3. Install dependencies

```bash
pip install aiohttp python-dotenv
```

### 4. Start your local MCP server

**Terminal 1:**
```bash
cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/electron/backend
python src/core/mcp/extension/start_servers.py
```

Wait for:
```
✅ MCP server started (PID: xxxxx)
```

### 5. Start tunnel client

**Terminal 2:**
```bash
cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/remote-mcp/client
python mcp_tunnel_client.py
```

You should see:
```
✅ Tunnel established successfully!
  User: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Remote MCP Endpoint: http://146.190.120.44:8767/mcp
  Authorization: Bearer lb_abc123xyz789_secure_random_string
```

## Using with MCP Clients

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "localbrain-remote": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "-H", "Authorization: Bearer YOUR_REMOTE_API_KEY",
        "-H", "Content-Type: application/json",
        "-d", "@-",
        "http://146.190.120.44:8767/mcp"
      ]
    }
  }
}
```

### Cursor

Add to your Cursor settings:

```json
{
  "mcp.servers": {
    "localbrain": {
      "endpoint": "http://146.190.120.44:8767/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_REMOTE_API_KEY"
      }
    }
  }
}
```

### Testing

Test your connection:

```bash
curl -X POST http://146.190.120.44:8767/mcp \
  -H "Authorization: Bearer YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Automation

### Start with shell script

Create `start_tunnel.sh`:

```bash
#!/bin/bash

# Start local MCP server in background
cd /path/to/electron/backend
python src/core/mcp/extension/start_servers.py &
MCP_PID=$!

# Wait for MCP server to start
sleep 3

# Start tunnel client
cd /path/to/remote-mcp/client
python mcp_tunnel_client.py

# Cleanup on exit
kill $MCP_PID
```

Make executable:
```bash
chmod +x start_tunnel.sh
./start_tunnel.sh
```

### macOS Launch Agent (Auto-start)

Create `~/Library/LaunchAgents/com.localbrain.tunnel.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.localbrain.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/remote-mcp/client/mcp_tunnel_client.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/remote-mcp/client</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.localbrain.tunnel.plist
```

## Troubleshooting

### Tunnel won't connect

1. **Check local MCP server**:
   ```bash
   curl http://127.0.0.1:8766/health
   ```

2. **Check remote server**:
   ```bash
   curl http://146.190.120.44:8767/health
   ```

3. **Verify credentials** in `.env`

4. **Check network**:
   ```bash
   ping 146.190.120.44
   ```

### Connection drops frequently

- Increase `PING_INTERVAL` in `.env`
- Check network stability
- Review server logs

### "No active tunnel" error

- Ensure tunnel client is running
- Check credentials match server configuration
- Restart both MCP server and tunnel client

## Security Notes

1. **Keep your API key secret** - Never share or commit to git
2. **Use unique USER_ID** - Don't reuse across devices
3. **Rotate keys regularly** - Generate new keys periodically
4. **Monitor access** - Check server logs for unauthorized access
