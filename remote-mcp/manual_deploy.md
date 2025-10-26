# Manual Server Deployment

The automated deploy script has sudo authentication issues. Use this manual process instead:

## Step 1: SSH into Server

```bash
ssh mcpuser@146.190.120.44
# Password: CalHacks12Group
```

## Step 2: Create Directories (on server)

```bash
mkdir -p ~/localbrain/remote-mcp/server
cd ~/localbrain/remote-mcp
```

## Step 3: Upload Files (from your Mac in a NEW terminal)

```bash
cd /Users/pranavbalaji/Documents/Personal\ CS\ Projects/Berkley\ Hackathon/localbrain/remote-mcp

scp server/mcp_http_server.py mcpuser@146.190.120.44:~/localbrain/remote-mcp/server/
scp server/.env.example mcpuser@146.190.120.44:~/localbrain/remote-mcp/server/
scp server/README.md mcpuser@146.190.120.44:~/localbrain/remote-mcp/server/
```

## Step 4: Setup Python Environment (back on server)

```bash
cd ~/localbrain/remote-mcp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install aiohttp aiohttp-cors python-dotenv
```

## Step 5: Configure API Keys (on server)

```bash
cd ~/localbrain/remote-mcp/server
cp .env.example .env
nano .env
```

Add your API key:
```env
API_KEY_PRANAV=lb_your_secure_key_here
```

Press Ctrl+X, then Y, then Enter to save.

## Step 6: Create Systemd Service (on server)

```bash
sudo nano /etc/systemd/system/mcp-bridge.service
```

Paste this:
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

Save with Ctrl+X, Y, Enter.

## Step 7: Start Service (on server)

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-bridge
sudo systemctl start mcp-bridge
sudo systemctl status mcp-bridge
```

## Step 8: Configure Firewall (on server)

```bash
sudo ufw allow 8767/tcp
sudo ufw reload
```

## Step 9: Test It (on server)

```bash
curl http://localhost:8767/health
```

You should see:
```json
{"status": "healthy", "active_tunnels": 0, ...}
```

## Step 10: Test from Your Mac

```bash
curl http://146.190.120.44:8767/health
```

Done! Server is now deployed.
