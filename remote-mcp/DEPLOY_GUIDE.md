# Complete Deployment Guide for Remote MCP Bridge

This guide will help you deploy your LocalBrain MCP server to the cloud so others can access it remotely.

## Overview

The system consists of:
1. **Server** - Runs on 146.190.120.44, accepts MCP connections
2. **Client** - Runs on your Mac, tunnels requests to local MCP server
3. **Local MCP** - Your existing LocalBrain MCP server (port 8766)

## Step 1: Server Setup (On 146.190.120.44)

### Option A: Automated Deployment

From your local machine:

```bash
cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/remote-mcp
./deploy.sh
```

This will upload and configure everything automatically.

### Option B: Manual Deployment

1. **SSH into the server**:
   ```bash
   ssh mcpuser@146.190.120.44
   ```

2. **Install Python dependencies**:
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python and pip
   sudo apt install python3 python3-pip python3-venv -y
   
   # Create project directory
   mkdir -p ~/localbrain/remote-mcp/server
   cd ~/localbrain/remote-mcp
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install required packages
   pip install aiohttp aiohttp-cors python-dotenv
   ```

3. **Upload server files** (from your local machine):
   ```bash
   scp server/mcp_http_server.py mcpuser@146.190.120.44:~/localbrain/remote-mcp/server/
   scp server/.env.example mcpuser@146.190.120.44:~/localbrain/remote-mcp/server/
   ```

4. **Configure API keys** (on server):
   ```bash
   cd ~/localbrain/remote-mcp/server
   cp .env.example .env
   nano .env
   ```
   
   Add your API key configuration:
   ```env
   # Add your user (replace with your actual credentials)
   API_KEY_PRANAV=lb_your_secure_api_key_here
   ```

5. **Setup systemd service** (on server):
   ```bash
   sudo nano /etc/systemd/system/mcp-bridge.service
   ```
   
   Add:
   ```ini
   [Unit]
   Description=LocalBrain MCP Bridge Server
   After=network.target

   [Service]
   Type=simple
   User=mcpuser
   WorkingDirectory=/home/mcpuser/localbrain/remote-mcp/server
   Environment="PATH=/home/mcpuser/localbrain/remote-mcp/venv/bin"
   ExecStart=/home/mcpuser/localbrain/remote-mcp/venv/bin/python /home/mcpuser/localbrain/remote-mcp/server/mcp_http_server.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

6. **Start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable mcp-bridge
   sudo systemctl start mcp-bridge
   sudo systemctl status mcp-bridge
   ```

7. **Configure firewall**:
   ```bash
   sudo ufw allow 8767/tcp
   sudo ufw reload
   ```

8. **Verify server is running**:
   ```bash
   curl http://localhost:8767/health
   ```

## Step 2: Client Setup (On Your Mac)

1. **Generate your credentials**:
   ```bash
   # Generate unique user ID
   python3 -c "import uuid; print(str(uuid.uuid4()))"
   # Save this output, e.g.: pranav-123e4567-e89b-12d3-a456-426614174000
   
   # Generate secure API key  
   python3 -c "import secrets; print('lb_' + secrets.token_urlsafe(32))"
   # Save this output, e.g.: lb_abc123xyz789_very_secure_random_string
   ```

2. **Configure client**:
   ```bash
   cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/remote-mcp/client
   cp .env.example .env
   nano .env
   ```
   
   Add your credentials:
   ```env
   USER_ID=pranav-123e4567-e89b-12d3-a456-426614174000
   REMOTE_API_KEY=lb_abc123xyz789_very_secure_random_string
   REMOTE_SERVER=ws://146.190.120.44:8767/tunnel
   LOCAL_MCP_SERVER=http://127.0.0.1:8766
   ```

3. **Install client dependencies**:
   ```bash
   pip install aiohttp python-dotenv
   ```

## Step 3: Add Your Credentials to Server

**IMPORTANT**: The API key in your client `.env` must match what's configured on the server.

SSH into the server and add your credentials:

```bash
ssh mcpuser@146.190.120.44
cd ~/localbrain/remote-mcp/server
nano .env
```

Add your user (the USER_ID should match, and the API_KEY should be the same):
```env
# Replace 'pranav' with your username (lowercase, no spaces)
# The API key must match what's in your client .env
API_KEY_PRANAV=lb_abc123xyz789_very_secure_random_string
```

Restart the server:
```bash
sudo systemctl restart mcp-bridge
```

## Step 4: Test the Setup

1. **Start your local MCP server** (Terminal 1):
   ```bash
   cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/electron/backend
   python src/core/mcp/extension/start_servers.py
   ```

2. **Start the tunnel client** (Terminal 2):
   ```bash
   cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/remote-mcp/client
   python mcp_tunnel_client.py
   ```
   
   You should see:
   ```
   ✅ Tunnel established successfully!
   Remote MCP Endpoint: http://146.190.120.44:8767/mcp
   ```

3. **Test the connection** (Terminal 3):
   ```bash
   curl -X POST http://146.190.120.44:8767/mcp \
     -H "Authorization: Bearer lb_abc123xyz789_very_secure_random_string" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```
   
   You should get a JSON response with available tools.

## Step 5: Configure MCP Clients

### For Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "localbrain-remote": {
      "command": "sh",
      "args": ["-c", "while read line; do echo \"$line\" | curl -X POST http://146.190.120.44:8767/mcp -H 'Authorization: Bearer YOUR_API_KEY' -H 'Content-Type: application/json' -d @- 2>/dev/null; done"]
    }
  }
}
```

Replace `YOUR_API_KEY` with your actual API key.

### For Other MCP Clients

Use these settings:
- **Endpoint**: `http://146.190.120.44:8767/mcp`
- **Authorization**: `Bearer YOUR_API_KEY`
- **Method**: POST
- **Content-Type**: `application/json`

## Daily Usage

To enable remote access:

1. Start your Electron app (which starts the local MCP server)
2. Run the tunnel client:
   ```bash
   cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/remote-mcp/client
   python mcp_tunnel_client.py
   ```
3. Keep the terminal open while you want remote access
4. Press Ctrl+C to stop remote access

## Troubleshooting

### Server Issues

Check server status:
```bash
ssh mcpuser@146.190.120.44
sudo systemctl status mcp-bridge
sudo journalctl -u mcp-bridge -n 50
```

### Client Issues

1. Verify local MCP server is running:
   ```bash
   curl http://127.0.0.1:8766/health
   ```

2. Check credentials in `client/.env` match server configuration

3. Test network connectivity:
   ```bash
   curl http://146.190.120.44:8767/health
   ```

### Common Errors

- **"No active tunnel"**: Start the tunnel client
- **"Invalid API key"**: Ensure API key matches between client and server
- **"Connection refused"**: Check if server is running and firewall allows port 8767
- **"Local MCP server error"**: Ensure local MCP server is running on port 8766

## Security Best Practices

1. **Generate strong API keys** - Use the provided commands
2. **Keep keys secret** - Never commit to git or share
3. **Use HTTPS in production** - Add SSL certificate to server
4. **Rotate keys regularly** - Generate new keys monthly
5. **Monitor access logs** - Check server logs for unauthorized access
6. **Limit API keys** - One key per user/device

## Support

For issues or questions:
1. Check server logs: `ssh mcpuser@146.190.120.44 && sudo journalctl -u mcp-bridge -f`
2. Check client output for error messages
3. Verify all configuration steps were followed
4. Test each component individually
