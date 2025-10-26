# Quick Setup Guide

Follow these steps to get your LocalBrain Slack bot running.

## Prerequisites

- Python 3.8+
- LocalBrain daemon installed and configured
- Slack workspace admin access

## Step 1: Install Dependencies

```bash
cd electron/backend/slack-bot
pip install -r requirements.txt
```

## Step 2: Create Slack App

### 2.1 Create New App
1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `LocalBrain Assistant`
4. Select your workspace
5. Click **"Create App"**

### 2.2 Add Bot Permissions
1. In your app settings, go to **"OAuth & Permissions"**
2. Under **"Bot Token Scopes"**, add:
   - `chat:write`
   - `channels:history`
   - `channels:read`
   - `im:history` (for reading DMs)
   - `im:write` (for sending DMs)
   - `app_mentions:read` (optional, for @mentions)

### 2.3 Enable Event Subscriptions
1. Go to **"Event Subscriptions"**
2. Toggle **"Enable Events"** to ON
3. **Request URL**: Leave blank for now (we'll add this after deployment)
4. Under **"Subscribe to bot events"**, add:
   - `message.channels` (for channel messages)
   - `message.im` (for direct messages)
   - `app_mention` (optional, for @mentions)
5. Click **"Save Changes"**

### 2.4 Install App to Workspace
1. Go to **"Install App"**
2. Click **"Install to Workspace"**
3. Authorize the app
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`)

### 2.5 Get Signing Secret
1. Go to **"Basic Information"**
2. Under **"App Credentials"**, find **"Signing Secret"**
3. Click **"Show"** and copy it

### 2.6 Get Channel ID
1. Open Slack in browser
2. Navigate to the channel you want to monitor (e.g., `#ask-directors`)
3. Copy the channel ID from the URL
   - URL format: `https://app.slack.com/client/TXXXXXX/C01234ABCDE`
   - Channel ID is the last part: `C01234ABCDE`

### 2.7 Add Bot to Channel
1. In Slack, go to your target channel
2. Type: `/invite @LocalBrain Assistant`

## Step 3: Configure Environment Variables

Create a `.env` file in the `composio-slack-bot` directory:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_CHANNEL_ID=C01234ABCDE

# LocalBrain Daemon Configuration
DAEMON_URL=http://127.0.0.1:8765

# Trigger Keywords (optional - comma-separated)
# Bot responds in channels when messages contain these keywords
# Default: "localbrain", "lb", "?", "help", "what", "how", etc.
TRIGGER_KEYWORDS=internship,interview,job,offer,resume

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

**Notes**:
- If you leave `SLACK_CHANNEL_ID` empty, the bot will respond in all channels where it's added
- `DAEMON_URL` should point to your running LocalBrain daemon
- `TRIGGER_KEYWORDS`: Add custom keywords to trigger bot responses in channels
- **DMs always respond** to all messages, regardless of keywords

## Step 4: Start LocalBrain Daemon

In a terminal, start your LocalBrain daemon:

```bash
cd electron/backend
python src/daemon.py
```

You should see:
```
LocalBrain Background Service starting...
Service running on http://127.0.0.1:8765
```

## Step 5: Test Locally with ngrok

### 5.1 Start the Bot

In another terminal:

```bash
cd electron/backend/composio-slack-bot
python main.py
```

You should see:
```
Starting LocalBrain Slack Bot on 0.0.0.0:8000
Daemon URL: http://127.0.0.1:8765
```

### 5.2 Expose with ngrok

In a third terminal:

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://xyz789.ngrok.io`)

### 5.3 Update Slack Event URL

1. Go to your Slack app settings at https://api.slack.com/apps
2. Navigate to **"Event Subscriptions"**
3. Set **Request URL** to: `https://xyz789.ngrok.io/slack/events`
4. Wait for the green **"Verified"** checkmark

## Step 6: Test the Bot

**Test in a Channel:**
1. Go to your monitored channel in Slack
2. Send a message: "What are the hackathon rules?"
3. The bot should respond with information from your LocalBrain knowledge base

**Test with @Mentions:**
```
@LocalBrain Assistant what was my Meta offer?
```

**Test in a DM:**

⚠️ **IMPORTANT**: You **cannot test by DMing yourself**! Slack does not send events when you message yourself or a bot you own. This is a Slack platform limitation.

To test DMs:
1. Ask a coworker/friend to DM the bot
2. Or create a test Slack account and message the bot from that account
3. Send a message: "What projects am I working on?"
4. The bot should respond directly in the DM

Self-messaging will never work in Slack!

## Step 7: Deploy to Production (Optional)

For production use, deploy the bot to a server with a permanent URL.

### Option A: Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and initialize
railway login
railway init

# Add environment variables
railway variables set SLACK_BOT_TOKEN=xoxb-...
railway variables set SLACK_SIGNING_SECRET=...
railway variables set SLACK_CHANNEL_ID=...
railway variables set DAEMON_URL=...

# Deploy
railway up

# Get your production URL
railway domain
```

Update Slack Event Subscription URL to: `https://your-app.railway.app/slack/events`

### Option B: DigitalOcean App Platform

1. Push code to GitHub
2. Create new app from your repo in DigitalOcean
3. Add environment variables in the dashboard
4. Deploy and copy the app URL
5. Update Slack Event Subscription URL

### Option C: Docker on VPS

```bash
# Build image
docker build -t localbrain-slack-bot .

# Run container
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  --name localbrain-slack-bot \
  localbrain-slack-bot
```

Set up nginx/caddy with SSL, then update Slack Event Subscription URL.

## Troubleshooting

### Bot not responding

**⚠️ Are you trying to DM yourself?**
Slack does NOT send events when you message yourself or your own bot. This is a Slack platform limitation, not a bug. You must test with another user or a separate test account.

**Check these things:**
1. Test with another user (not yourself!)
2. Bot is invited to the channel: `/invite @LocalBrain Assistant`
3. Webhook URL is correct in Slack app settings
4. LocalBrain daemon is running: `curl http://127.0.0.1:8765/`
5. Check logs: `tail -f bot.log`
6. Event Subscriptions include `message.im`, `message.channels`, `app_mention`

### Slack signature verification failed

- Verify `SLACK_SIGNING_SECRET` matches Slack app settings
- Ensure your server time is synchronized
- Check that webhook URL uses HTTPS (required by Slack)

### Daemon connection errors

Test daemon manually:
```bash
curl -X POST http://127.0.0.1:8765/protocol/slack/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "test",
    "slack_context": {
      "server_name": "test",
      "channel_name": "test",
      "asker_name": "test",
      "thread_id": ""
    }
  }'
```

### ngrok URL keeps changing

Free ngrok URLs change every time you restart. For a permanent URL, either:
- Upgrade to ngrok Pro for a static domain
- Deploy to production (Railway, DigitalOcean, etc.)

### Bot replies to its own messages

This should be prevented automatically by checking for `bot_id` in events. If it's still happening:
1. Check `bot.log` for the actual events being received
2. Verify the bot token is correct
3. Make sure you're not running multiple instances of the bot

## Advanced Configuration

### Monitor Multiple Channels

Leave `SLACK_CHANNEL_ID` empty in `.env`:
```env
SLACK_CHANNEL_ID=
```

Then invite the bot to any channels you want it to monitor.

### Only Respond to @Mentions

In Slack Event Subscriptions, remove `message.channels` and only keep `app_mention`.

### Custom Daemon URL

If your daemon runs on a different machine:
```env
DAEMON_URL=https://your-daemon-server.com:8765
```

## Next Steps

- Test with various questions to see how it performs
- Monitor logs for any errors
- Adjust daemon settings if needed
- Consider adding more channels
- Set up proper production hosting

## Support

For more details, see the main [README.md](README.md).

For issues:
1. Check troubleshooting section
2. Review logs (`bot.log`)
3. Test daemon endpoint directly
4. Check Slack app event logs
