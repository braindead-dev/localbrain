# Quick Setup Guide

Follow these steps to get your Slack bot running quickly.

## Step 1: Get Slack Credentials

### 1.1 Create Slack App
1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `LocalBrain Assistant`
4. Select your Cal Hacks 12.0 workspace
5. Click **"Create App"**

### 1.2 Add Bot Permissions
1. In your app settings, go to **"OAuth & Permissions"**
2. Under **"Bot Token Scopes"**, add:
   - `chat:write`
   - `channels:history`
   - `channels:read`

### 1.3 Enable Events
1. Go to **"Event Subscriptions"**
2. Toggle **"Enable Events"** to ON
3. **Request URL**: Leave blank for now (we'll add this after deployment)
4. Under **"Subscribe to bot events"**, add:
   - `message.channels`
5. Click **"Save Changes"**

### 1.4 Install App
1. Go to **"Install App"**
2. Click **"Install to Workspace"**
3. Authorize the app
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`)

### 1.5 Get Signing Secret
1. Go to **"Basic Information"**
2. Under **"App Credentials"**, find **"Signing Secret"**
3. Click **"Show"** and copy it

### 1.6 Get Channel ID
1. Open Slack in browser
2. Navigate to `#ask-directors` channel
3. Copy the channel ID from the URL
   - URL format: `https://app.slack.com/client/TXXXXXX/C01234ABCDE`
   - Channel ID is the last part: `C01234ABCDE`

### 1.7 Add Bot to Channel
1. In Slack, go to `#ask-directors`
2. Type: `/invite @LocalBrain Assistant`

## Step 2: Get Composio API Key

1. Go to https://app.composio.dev/
2. Sign up or log in
3. Go to **"API Keys"** section
4. Copy your API key

### Connect Slack to Composio
1. In Composio dashboard, go to **"Integrations"**
2. Search for **"Slack"**
3. Click **"Connect"**
4. Authorize Composio to access your Slack workspace

## Step 3: Get LLM API Key

Choose one:

### Option A: OpenAI
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy it (starts with `sk-`)

### Option B: Anthropic Claude
1. Go to https://console.anthropic.com/
2. Create an API key
3. Copy it (starts with `sk-ant-`)

## Step 4: Set Up LocalBrain MCP

### Option A: Use Remote MCP (Recommended)

If you already have a remote MCP bridge running:

1. Navigate to the remote-mcp directory:
   ```bash
   cd ../../../remote-mcp
   ```

2. Check your `.env` file for:
   - `USER_ID` - Your unique user ID
   - `REMOTE_API_KEY` - Your remote API key

3. Your MCP URL will be:
   ```
   https://localbrain.henr.ee/u/YOUR_USER_ID
   ```

4. If you don't have a remote MCP set up, follow the guide in `remote-mcp/README.md`

### Option B: Use Local MCP (Development Only)

1. Start the local MCP server:
   ```bash
   cd ../../../../
   python electron/backend/src/core/mcp/extension/start_servers.py
   ```

2. In another terminal, expose it with ngrok:
   ```bash
   ngrok http 8766
   ```

3. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

## Step 5: Configure Environment Variables

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your credentials:
   ```env
   # From Step 1
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_SIGNING_SECRET=your-signing-secret-here
   SLACK_CHANNEL_ID=C01234ABCDE
   
   # From Step 2
   COMPOSIO_API_KEY=your-composio-api-key-here
   
   # From Step 3 (choose one)
   OPENAI_API_KEY=sk-your-openai-key-here
   # OR
   ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
   
   # Choose provider
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4-turbo-preview
   
   # From Step 4
   MCP_URL=https://localbrain.henr.ee/u/YOUR_USER_ID
   MCP_API_KEY=lb_your-remote-api-key-here
   
   # Server config (leave as is)
   HOST=0.0.0.0
   PORT=8000
   ```

## Step 6: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 7: Test Locally

1. Run the bot:
   ```bash
   python main.py
   ```

2. In another terminal, expose it with ngrok:
   ```bash
   ngrok http 8000
   ```

3. Copy the HTTPS URL (e.g., `https://xyz789.ngrok.io`)

4. Update Slack Event Subscription URL:
   - Go to your Slack app settings
   - Navigate to **"Event Subscriptions"**
   - Set **Request URL** to: `https://xyz789.ngrok.io/slack/events`
   - Wait for the green "Verified" checkmark

## Step 8: Test the Bot

1. Go to `#ask-directors` in Slack
2. Send a message: "What are the hackathon rules?"
3. The bot should respond with information from LocalBrain

## Step 9: Deploy to Production

### Option A: Railway (Easiest)

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login and initialize:
   ```bash
   railway login
   railway init
   ```

3. Add environment variables:
   ```bash
   railway variables set SLACK_BOT_TOKEN=xoxb-...
   railway variables set SLACK_SIGNING_SECRET=...
   railway variables set SLACK_CHANNEL_ID=...
   railway variables set COMPOSIO_API_KEY=...
   railway variables set OPENAI_API_KEY=...
   railway variables set LLM_PROVIDER=openai
   railway variables set LLM_MODEL=gpt-4-turbo-preview
   railway variables set MCP_URL=...
   railway variables set MCP_API_KEY=...
   ```

4. Deploy:
   ```bash
   railway up
   ```

5. Get your production URL:
   ```bash
   railway domain
   ```

6. Update Slack Event Subscription URL to your Railway domain:
   ```
   https://your-app.railway.app/slack/events
   ```

### Option B: DigitalOcean App Platform

1. Push code to GitHub
2. Go to DigitalOcean App Platform
3. Create new app from GitHub repo
4. Add environment variables in the dashboard
5. Deploy
6. Copy the app URL
7. Update Slack Event Subscription URL

### Option C: Docker on VPS

1. Build and run:
   ```bash
   docker build -t slack-bot .
   docker run -d --env-file .env -p 8000:8000 slack-bot
   ```

2. Set up reverse proxy (nginx/caddy) with SSL
3. Update Slack Event Subscription URL

## Troubleshooting

### Bot not responding
- Check logs: `tail -f bot.log`
- Verify bot is in the channel: `/invite @LocalBrain Assistant`
- Check webhook URL is correct in Slack app settings

### Slack verification failed
- Ensure `SLACK_SIGNING_SECRET` is correct
- Check server time is synchronized

### MCP connection errors
- Test MCP endpoint:
  ```bash
  curl -X POST $MCP_URL/search \
    -H "X-API-Key: $MCP_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"query": "test", "top_k": 3}'
  ```

### Composio errors
- Verify API key is valid
- Check Slack integration is connected in Composio dashboard

## Next Steps

- Monitor logs for errors
- Test with various questions
- Adjust LLM prompts in `main.py` if needed
- Set up monitoring and alerts
- Add rate limiting if needed

## Support

If you encounter issues:
1. Check the main README.md
2. Review server logs
3. Test each component individually
4. Check Slack app event logs
