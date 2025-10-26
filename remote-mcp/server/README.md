# MCP Bridge Server

This server runs on your cloud instance (146.190.120.44) and bridges MCP clients to your local vault.

## Installation on Server

### 1. SSH into your server

```bash
ssh mcpuser@146.190.120.44
```

### 2. Install Python and dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.9+
sudo apt install python3 python3-pip python3-venv -y

# Create project directory
mkdir -p ~/localbrain/remote-mcp/server
cd ~/localbrain/remote-mcp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install aiohttp aiohttp-cors python-dotenv
```

### 3. Configure the server

```bash
cd ~/localbrain/remote-mcp/server

# Copy configuration
cp .env.example .env
nano .env

# Add your API keys:
# API_KEY_PRANAV=lb_your_secure_api_key_here
```

### 4. Setup as systemd service

Create service file:

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

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-bridge
sudo systemctl start mcp-bridge
sudo systemctl status mcp-bridge
```

### 5. Configure firewall

```bash
# Allow port 8767
sudo ufw allow 8767/tcp

# Check status
sudo ufw status
```

## Monitoring

### View logs

```bash
sudo journalctl -u mcp-bridge -f
```

### Check status

```bash
sudo systemctl status mcp-bridge
```

### Test endpoints

```bash
# Health check
curl http://146.190.120.44:8767/health

# Status
curl http://146.190.120.44:8767/status
```

## Updating

To update the server:

```bash
# Stop service
sudo systemctl stop mcp-bridge

# Update code
cd ~/localbrain/remote-mcp/server
# (upload new mcp_http_server.py)

# Restart service
sudo systemctl start mcp-bridge
```

## Security

1. **API Keys**: Store API keys in environment variables, never in code
2. **Firewall**: Only expose port 8767, block all other unnecessary ports
3. **Updates**: Keep system and Python packages updated
4. **Monitoring**: Check logs regularly for suspicious activity

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u mcp-bridge -n 50

# Check Python path
which python3

# Test manually
cd ~/localbrain/remote-mcp/server
source ../venv/bin/activate
python mcp_http_server.py
```

### Port already in use

```bash
# Find process using port
sudo lsof -i :8767

# Kill if needed
sudo kill -9 <PID>
```

### Can't connect from client

1. Check firewall: `sudo ufw status`
2. Check service: `sudo systemctl status mcp-bridge`
3. Test locally: `curl http://localhost:8767/health`
4. Check external: `curl http://146.190.120.44:8767/health`
