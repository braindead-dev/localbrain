# Deploying Remote MCP Bridge on DigitalOcean

Complete guide for deploying the LocalBrain Remote MCP Bridge on a DigitalOcean droplet for production use.

## Overview

This guide will set up a production-ready bridge server on DigitalOcean that:
- Runs 24/7 with automatic restarts
- Uses HTTPS with automatic SSL certificates
- Has proper security hardening
- Includes monitoring and logging
- Costs approximately **$6-12/month**

## Prerequisites

- DigitalOcean account
- SSH key pair configured
- Domain name (optional but recommended for HTTPS)
- Local machine with:
  - Daemon running (port 8765)
  - MCP server running (port 8766)

---

## Part 1: Create and Configure Droplet

### 1.1 Create Droplet

1. **Log in to DigitalOcean** → Click **"Create"** → **"Droplets"**

2. **Choose Configuration**:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic Shared CPU
   - **Size**: $6/month (1GB RAM, 1 CPU, 25GB SSD)
   - **Datacenter**: Choose closest to your location
   - **Authentication**: SSH Keys (add your public key)
   - **Hostname**: `mcp-bridge` (or your choice)
   - **Enable Monitoring**: ✓ (Free)

3. **Create Droplet** and note the IP address

### 1.2 Initial Server Setup

```bash
# SSH as root
ssh root@YOUR_DROPLET_IP

# Update system
apt update && apt upgrade -y

# Create non-root user
adduser mcpuser
# Set password and fill in details (or skip with Enter)

# Add to sudo group
usermod -aG sudo mcpuser

# Copy SSH key to new user
rsync --archive --chown=mcpuser:mcpuser ~/.ssh /home/mcpuser

# Test new user login (new terminal)
ssh mcpuser@YOUR_DROPLET_IP

# If successful, continue as mcpuser
```

### 1.3 Security Hardening

```bash
# Disable root SSH login
sudo nano /etc/ssh/sshd_config

# Find and change:
PermitRootLogin no
PasswordAuthentication no

# Save and restart SSH
sudo systemctl restart sshd

# Setup firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
# Type 'y' to confirm

# Verify firewall status
sudo ufw status
```

---

## Part 2: Install Dependencies

### 2.1 Install Python and System Packages

```bash
# Install Python 3.10+
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl

# Verify Python version
python3 --version  # Should be 3.10+
```

### 2.2 Clone Repository

```bash
# Clone your repository
cd ~
git clone https://github.com/braindead-dev/localbrain.git
cd localbrain/remote-mcp

# Or if you have the code locally, use scp:
# From your local machine:
# scp -r remote-mcp/ mcpuser@YOUR_DROPLET_IP:~/localbrain/
```

### 2.3 Setup Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python3 -c "import fastapi; import websockets; print('✓ Dependencies installed')"
```

---

## Part 3: Configure Bridge Server

### 3.1 Create Environment Configuration

```bash
cd ~/localbrain/remote-mcp

# Copy template
cp .env.example .env

# Edit configuration
nano .env
```

**Set these values in `.env`**:

```env
# Bridge Server Configuration
BRIDGE_HOST=127.0.0.1  # Localhost - Caddy will handle public access
BRIDGE_PORT=8767
BRIDGE_SECRET=<generate-strong-secret>  # See below

# Tunnel idle timeout
MAX_TUNNEL_IDLE_SECONDS=300
```

**Generate strong BRIDGE_SECRET**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output and paste in .env as BRIDGE_SECRET
```

### 3.2 Test Bridge Server

```bash
# Activate venv if not active
source ~/localbrain/remote-mcp/venv/bin/activate

# Test run
python3 bridge_server.py

# You should see:
# LocalBrain Remote MCP Bridge Starting...
# Uvicorn running on http://127.0.0.1:8767

# Press Ctrl+C to stop
```

---

## Part 4: Setup System Service

### 4.1 Create Systemd Service

```bash
sudo nano /etc/systemd/system/mcp-bridge.service
```

**Add this content** (adjust paths if needed):

```ini
[Unit]
Description=LocalBrain Remote MCP Bridge
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=mcpuser
Group=mcpuser
WorkingDirectory=/home/mcpuser/localbrain/remote-mcp
Environment="PATH=/home/mcpuser/localbrain/remote-mcp/venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/mcpuser/localbrain/remote-mcp/venv/bin/python bridge_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/mcpuser/localbrain/remote-mcp

[Install]
WantedBy=multi-user.target
```

### 4.2 Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable mcp-bridge

# Start service
sudo systemctl start mcp-bridge

# Check status
sudo systemctl status mcp-bridge

# Should show: Active: active (running)

# View logs
sudo journalctl -u mcp-bridge -f
# Press Ctrl+C to exit
```

---

## Part 5: Setup HTTPS with Caddy

### 5.1 Install Caddy

```bash
# Add Caddy repository
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list

sudo apt update
sudo apt install caddy

# Verify installation
caddy version
```

### 5.2 Configure Caddy

**If you have a domain name:**
Note: I don't have a domain, but do MCP's require a domain for HTTPS?

```bash
sudo nano /etc/caddy/Caddyfile
```

**Add this configuration** (replace `mcp.yourdomain.com` with your domain):

```caddy
mcp.yourdomain.com {
    # Handle MCP endpoints
    handle /u/* {
        reverse_proxy localhost:8767
    }

    # Health check
    handle /health {
        reverse_proxy localhost:8767
    }

    # Admin endpoints (optional - only if you need them)
    handle /admin/* {
        reverse_proxy localhost:8767

        # Optional: Restrict to specific IPs
        # @allowed {
        #     remote_ip YOUR_IP_HERE
        # }
        # handle @allowed {
        #     reverse_proxy localhost:8767
        # }
    }

    # WebSocket tunnel endpoint
    handle /tunnel/* {
        reverse_proxy localhost:8767 {
            header_up Upgrade {http.request.header.Upgrade}
            header_up Connection {http.request.header.Connection}
        }
    }

    # Logs
    log {
        output file /var/log/caddy/mcp-bridge.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}
```

**If you DON'T have a domain (using IP only):**

```caddy
:443 {
    tls internal  # Self-signed cert (not recommended for production)

    reverse_proxy localhost:8767
}

:80 {
    redir https://{host}{uri}
}
```

### 5.3 Enable and Start Caddy

```bash
# Test configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Reload Caddy
sudo systemctl reload caddy

# Check status
sudo systemctl status caddy

# View logs
sudo journalctl -u caddy -f
```

**Caddy will automatically:**
- Obtain SSL certificates from Let's Encrypt
- Renew certificates automatically
- Handle HTTPS redirects

---

## Part 6: Configure Local Tunnel Client

### 6.1 Generate Credentials

On your **local machine**:

```bash
cd localbrain/remote-mcp

# Generate USER_ID
python3 -c "import uuid; print('USER_ID=' + str(uuid.uuid4()))"

# Generate REMOTE_API_KEY
python3 -c "import secrets; print('REMOTE_API_KEY=lb_' + secrets.token_urlsafe(32))"

# Save these values!
```

### 6.2 Configure Local .env

```bash
# On local machine
cd localbrain/remote-mcp
cp .env.example .env
nano .env
```

**Set these values**:

```env
# Bridge URL (use your domain or droplet IP)
BRIDGE_URL=wss://mcp.yourdomain.com/tunnel/connect
# Or with IP: wss://YOUR_DROPLET_IP/tunnel/connect

# Local MCP server (no changes)
LOCAL_MCP_URL=http://127.0.0.1:8766
LOCAL_API_KEY=dev-key-local-only

# Generated credentials (paste from step 6.1)
USER_ID=your-generated-uuid
REMOTE_API_KEY=your-generated-api-key

# Allowed tools
ALLOWED_TOOLS=search,search_agentic,open,summarize,list

# Keepalive
KEEPALIVE_INTERVAL=30
```

### 6.3 Start Local Services and Tunnel

```bash
# Terminal 1: Start daemon + MCP server
cd localbrain/electron/backend
python src/core/mcp/extension/start_servers.py

# Terminal 2: Start tunnel client
cd localbrain/remote-mcp
./start_tunnel.sh

# Should see:
# ✅ Tunnel established successfully!
# Remote URL: https://mcp.yourdomain.com/u/YOUR_USER_ID
```

---

## Part 7: Testing

### 7.1 Test Bridge Health

```bash
# From anywhere
curl https://mcp.yourdomain.com/health

# Should return:
# {"status":"healthy","timestamp":"...","active_tunnels":1}
```

### 7.2 Test End-to-End

```bash
# On local machine
cd localbrain/remote-mcp
python3 test_bridge.py

# All 6 tests should pass
```

### 7.3 Test External Access

```bash
# From anywhere (use your credentials)
curl -X POST https://mcp.yourdomain.com/u/YOUR_USER_ID/search \
  -H "X-API-Key: YOUR_REMOTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "test search", "top_k": 5}'

# Should return search results
```

---

## Part 8: Monitoring and Maintenance

### 8.1 View Logs

```bash
# Bridge server logs
sudo journalctl -u mcp-bridge -f

# Caddy logs
sudo journalctl -u caddy -f

# Or view Caddy access logs
sudo tail -f /var/log/caddy/mcp-bridge.log
```

### 8.2 Monitor Service Status

```bash
# Check if services are running
sudo systemctl status mcp-bridge
sudo systemctl status caddy

# Check active tunnels
curl https://mcp.yourdomain.com/admin/tunnels \
  -H "X-Admin-Secret: YOUR_BRIDGE_SECRET"
```

### 8.3 Restart Services

```bash
# Restart bridge
sudo systemctl restart mcp-bridge

# Restart Caddy
sudo systemctl restart caddy

# View startup logs
sudo journalctl -u mcp-bridge -n 50
```

### 8.4 Update Code

```bash
# On droplet
cd ~/localbrain/remote-mcp

# Pull latest changes
git pull

# Restart service
sudo systemctl restart mcp-bridge
```

### 8.5 Backup Configuration

```bash
# Backup .env file (contains secrets!)
# On droplet
cp ~/.localbrain/remote-mcp/.env ~/.env.backup

# Or copy to local machine
scp mcpuser@YOUR_DROPLET_IP:~/localbrain/remote-mcp/.env ~/mcp-bridge-backup.env
```

---

## Part 9: Optional Enhancements

### 9.1 Setup Monitoring with UptimeRobot

1. Sign up at [UptimeRobot](https://uptimerobot.com) (free)
2. Add monitor:
   - Type: HTTP(S)
   - URL: `https://mcp.yourdomain.com/health`
   - Interval: 5 minutes
3. Get email alerts if bridge goes down

### 9.2 Setup Log Rotation

```bash
sudo nano /etc/logrotate.d/mcp-bridge
```

Add:
```
/var/log/caddy/mcp-bridge.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

### 9.3 Automatic Security Updates

```bash
# Install unattended-upgrades
sudo apt install unattended-upgrades

# Enable automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 9.4 Add Fail2Ban (Brute Force Protection)

```bash
# Install fail2ban
sudo apt install fail2ban

# It will automatically protect SSH
# Check status
sudo fail2ban-client status
```

---

## Troubleshooting

### Issue: Bridge service won't start

```bash
# Check logs for errors
sudo journalctl -u mcp-bridge -n 100 --no-pager

# Common fixes:
# 1. Check Python path in service file
which python3
# Update ExecStart in /etc/systemd/system/mcp-bridge.service

# 2. Check permissions
ls -la ~/localbrain/remote-mcp/
sudo chown -R mcpuser:mcpuser ~/localbrain/

# 3. Test manually
cd ~/localbrain/remote-mcp
source venv/bin/activate
python3 bridge_server.py
```

### Issue: Caddy SSL certificate fails

```bash
# Check Caddy logs
sudo journalctl -u caddy -n 50

# Ensure:
# 1. Domain DNS is pointing to droplet IP
dig mcp.yourdomain.com

# 2. Port 80/443 are open
sudo ufw status

# 3. No other service using port 80/443
sudo netstat -tlnp | grep ':80\|:443'
```

### Issue: Tunnel connects but requests fail

```bash
# Check bridge is receiving requests
sudo journalctl -u mcp-bridge -f

# Check local MCP server is running
curl http://localhost:8766/health

# Check local daemon is running
curl http://localhost:8765/health

# Verify API keys match
# In local .env: LOCAL_API_KEY
# In MCP clients.json: should match
```

### Issue: High memory usage

```bash
# Check memory
free -h

# Check bridge memory usage
ps aux | grep bridge_server

# If needed, upgrade droplet to $12/month (2GB RAM)
# DigitalOcean Console → Droplet → Resize
```

---

## Cost Breakdown

### Monthly Costs

| Item | Cost |
|------|------|
| Droplet (1GB RAM) | $6.00 |
| Bandwidth (1TB included) | $0.00 |
| Snapshots (optional) | ~$1.00 |
| Domain (yearly ÷ 12) | ~$1.00 |
| **Total** | **~$8/month** |

### Bandwidth Usage Estimates

- Typical search request: ~5-50KB
- 10,000 requests/month ≈ 500MB
- Well within 1TB limit

### When to Upgrade

Upgrade to $12/month (2GB RAM) droplet if:
- Supporting multiple users (5+)
- High request volume (>50,000/month)
- Running additional services

---

## Security Checklist

Before going live, verify:

- [ ] Root SSH login disabled
- [ ] Password authentication disabled
- [ ] UFW firewall enabled and configured
- [ ] Strong BRIDGE_SECRET set
- [ ] Strong REMOTE_API_KEY set
- [ ] HTTPS enabled with valid certificate
- [ ] Automatic security updates enabled
- [ ] Service running as non-root user
- [ ] Admin endpoints restricted (if exposed)
- [ ] Regular backups of .env configuration
- [ ] Monitoring/alerts configured
- [ ] fail2ban installed and active

---

## Quick Reference Commands

```bash
# Service management
sudo systemctl status mcp-bridge
sudo systemctl restart mcp-bridge
sudo systemctl stop mcp-bridge
sudo systemctl start mcp-bridge

# Logs
sudo journalctl -u mcp-bridge -f
sudo journalctl -u caddy -f

# Health checks
curl https://mcp.yourdomain.com/health
curl https://mcp.yourdomain.com/admin/tunnels \
  -H "X-Admin-Secret: YOUR_SECRET"

# Update code
cd ~/localbrain/remote-mcp
git pull
sudo systemctl restart mcp-bridge
```

---

## Support

For issues:
1. Check logs: `sudo journalctl -u mcp-bridge -n 100`
2. Verify services: `sudo systemctl status mcp-bridge caddy`
3. Test connectivity: `curl https://mcp.yourdomain.com/health`
4. Review troubleshooting section in [README.md](./README.md)
5. File issue on GitHub with relevant logs

---

**Deployment Version:** 1.0.0
**Last Updated:** 2025-01-25
**Tested On:** Ubuntu 22.04 LTS, DigitalOcean $6/month droplet
