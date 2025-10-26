# 🚀 Quick Start - Remote MCP Bridge

Get your LocalBrain accessible from anywhere in 5 minutes!

## 1️⃣ Deploy to Server (One-time setup)

```bash
cd /Users/pranavbalaji/Documents/Personal CS Projects/Berkley Hackathon/localbrain/remote-mcp
./deploy.sh
```

SSH into server and configure:
```bash
ssh mcpuser@146.190.120.44
cd ~/localbrain/remote-mcp/server
nano .env
# Add: API_KEY_PRANAV=lb_your_secure_key_here
sudo systemctl restart mcp-bridge
```

## 2️⃣ Configure Client (One-time setup)

Generate credentials:
```bash
cd client

# Generate user ID
python3 -c "import uuid; print(str(uuid.uuid4()))"
# Save output (e.g., pranav-abc123)

# Generate API key
python3 -c "import secrets; print('lb_' + secrets.token_urlsafe(32))"  
# Save output (e.g., lb_xyz789)

# Configure
cp .env.example .env
nano .env
# Add your USER_ID and REMOTE_API_KEY
```

## 3️⃣ Daily Usage

Start remote access:
```bash
cd client
./start_tunnel.sh
```

Your remote endpoint:
```
URL: http://146.190.120.44:8767/mcp
Auth: Bearer <your-api-key>
```

Stop with Ctrl+C.

## 📝 Test It

```bash
curl -X POST http://146.190.120.44:8767/mcp \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

That's it! Your LocalBrain is now accessible from anywhere! 🎉
