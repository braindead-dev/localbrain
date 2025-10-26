# LocalBrain Slack Bot

A simple Slack bot that connects Slack to your LocalBrain daemon. When users ask questions in monitored channels, the bot retrieves answers from your LocalBrain knowledge base and responds.

## Architecture

```
Slack Message → Slack Events API → FastAPI Webhook (/slack/events)
                                        ↓
                                LocalBrain Daemon (/protocol/slack/answer)
                                        ↓
                                    Answer Retrieved
                                        ↓
                                Slack SDK posts response
```

## How It Works

1. **Slack Events API** sends message events from monitored channel(s) to your webhook endpoint
2. **FastAPI Server** receives the event and extracts the message
3. **LocalBrain Daemon** is called to search your knowledge base and synthesize an answer
4. **Slack SDK** sends the answer back to the Slack channel

## Prerequisites

- Python 3.8+
- Slack workspace admin access (to create apps and install bots)
- LocalBrain daemon running at `http://127.0.0.1:8765` (or configured URL)

## Quick Setup

### 1. Install Dependencies

```bash
cd electron/backend/composio-slack-bot
pip install -r requirements.txt
```

### 2. Create Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `LocalBrain Assistant`
4. Select your workspace
5. Click **"Create App"**

### 3. Configure Bot Permissions

1. Go to **"OAuth & Permissions"** in the left sidebar
2. Scroll to **"Scopes"** → **"Bot Token Scopes"**
3. Add these scopes:
   - `chat:write` - Send messages
   - `channels:history` - Read channel messages
   - `channels:read` - View channel info
   - `im:history` - Read DM messages
   - `im:write` - Send DM messages
   - `app_mentions:read` - Read mentions (optional, for @mentions)

### 4. Enable Events

1. Go to **"Event Subscriptions"** in the left sidebar
2. Toggle **"Enable Events"** to ON
3. **Request URL**: `https://your-domain.com/slack/events`
   - You'll need to deploy your server first or use ngrok for testing
   - See "Testing Locally" section below for ngrok setup
4. Under **"Subscribe to bot events"**, add:
   - `message.channels` - Listen to messages in public channels
   - `message.im` - Listen to direct messages (DMs)
   - `app_mention` - Listen to @mentions (optional)

### 5. Install App to Workspace

1. Go to **"Install App"** in the left sidebar
2. Click **"Install to Workspace"**
3. Authorize the app
4. Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)

### 6. Get Signing Secret

1. Go to **"Basic Information"**
2. Under **"App Credentials"**, find **"Signing Secret"**
3. Click **"Show"** and copy it

### 7. Get Channel ID

1. Open Slack workspace in browser
2. Navigate to the channel you want to monitor (e.g., `#ask-directors`)
3. Copy the channel ID from URL
   - URL format: `https://app.slack.com/client/TXXXXXX/C01234ABCDE`
   - Channel ID is the last part: `C01234ABCDE`

### 8. Add Bot to Channel

1. In Slack, go to your target channel
2. Type `/invite @LocalBrain Assistant`
3. The bot will join the channel

### 9. Configure Environment Variables

Create a `.env` file:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_CHANNEL_ID=C01234ABCDE

# LocalBrain Daemon Configuration
DAEMON_URL=http://127.0.0.1:8765

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

**Note**: If you leave `SLACK_CHANNEL_ID` empty, the bot will respond to messages in all channels where it's been added.

## Running the Bot

### Testing Locally

1. Start your LocalBrain daemon first:
   ```bash
   cd electron/backend
   python src/daemon.py
   ```

2. In another terminal, start the Slack bot:
   ```bash
   cd electron/backend/composio-slack-bot
   python main.py
   ```

3. In a third terminal, expose it with ngrok:
   ```bash
   ngrok http 8000
   ```

4. Copy the HTTPS URL (e.g., `https://xyz789.ngrok.io`)

5. Update Slack Event Subscription URL:
   - Go to your Slack app settings
   - Navigate to **"Event Subscriptions"**
   - Set **Request URL** to: `https://xyz789.ngrok.io/slack/events`
   - Wait for the green "Verified" checkmark

### Testing the Bot

**In a Channel:**
1. Go to your monitored channel in Slack
2. Send a message: "What are the hackathon rules?"
3. The bot should respond with information from your LocalBrain knowledge base

**In a DM:**
1. Go to Slack and open a DM with the bot (click on the bot name in your workspace)
2. Send a message: "What was my Meta offer?"
3. The bot should respond directly in the DM

## Production Deployment

### Option 1: Railway (Easiest)

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

Update Slack Event Subscription URL to your Railway domain: `https://your-app.railway.app/slack/events`

### Option 2: DigitalOcean App Platform

1. Push code to GitHub
2. Go to DigitalOcean App Platform
3. Create new app from GitHub repo
4. Add environment variables in the dashboard
5. Deploy
6. Copy the app URL
7. Update Slack Event Subscription URL

### Option 3: Docker on VPS

```bash
# Build and run
docker build -t slack-bot .
docker run -d --env-file .env -p 8000:8000 --name slack-bot slack-bot
```

Set up reverse proxy (nginx/caddy) with SSL, then update Slack Event Subscription URL.

## Environment Variables Reference

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SLACK_BOT_TOKEN` | Bot User OAuth Token from Slack | Yes | `xoxb-...` |
| `SLACK_SIGNING_SECRET` | Signing secret from Slack app settings | Yes | `abc123...` |
| `SLACK_CHANNEL_ID` | Channel ID to monitor (empty = all channels) | No | `C01234ABCDE` |
| `DAEMON_URL` | LocalBrain daemon endpoint URL | No (default: `http://127.0.0.1:8765`) | `http://...` |
| `HOST` | Server host | No (default: `0.0.0.0`) | `0.0.0.0` |
| `PORT` | Server port | No (default: `8000`) | `8000` |

## Features

- **Smart Keyword Triggering**: In channels, bot responds only when message contains:
  - Bot name variations ("localbrain", "local brain", "lb")
  - Question indicators ("?", "help", "what", "how", "where", "why", etc.)
  - Custom keywords you configure (e.g., "internship", "job", "interview")
  - @mentions of the bot
- **Direct Messages (DMs)**: Responds to ALL DM messages automatically
- **Message Monitoring**: Listens to messages in specified channel(s)
- **Thread Support**: Replies in threads to keep conversations organized
- **Signature Verification**: Validates all requests come from Slack
- **Background Processing**: Handles messages asynchronously to prevent timeouts
- **Error Handling**: Gracefully handles errors and notifies users

## Troubleshooting

### Bot not responding

**IMPORTANT: You cannot DM yourself!** Slack does not send events when you message yourself or a bot you own. This is a Slack limitation, not a bot issue.

To test the bot:
- Have another person DM the bot or message in a channel
- Or create a test Slack account
- Self-messaging will never work in Slack

Other checks:
- Check that the bot is invited to the channel: `/invite @LocalBrain Assistant`
- Verify webhook URL is correct in Slack app settings
- Check server logs: `tail -f bot.log`
- Ensure LocalBrain daemon is running: `curl http://127.0.0.1:8765/`
- Verify Event Subscriptions include `message.im`, `message.channels`, and `app_mention`

### Daemon connection errors

- Verify daemon is running on the correct port
- Check `DAEMON_URL` in `.env` file
- Test daemon endpoint manually:
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

### Slack verification failed

- Check that `SLACK_SIGNING_SECRET` matches the one in Slack app settings
- Ensure server time is synchronized (for signature verification)
- Verify ngrok/production URL is accessible and uses HTTPS

### Bot responds to its own messages

- This should be automatically prevented by checking for `bot_id` in events
- If still occurring, check the logs for unexpected event subtypes

## Architecture Details

### Components

1. **FastAPI Server** (`main.py`)
   - Receives Slack events via webhook (`/slack/events`)
   - Validates Slack signatures for security
   - Routes messages to background processing

2. **Slack SDK Client**
   - Posts responses back to Slack
   - Handles threading automatically
   - Manages API rate limits

3. **LocalBrain Daemon Client**
   - Calls `/protocol/slack/answer` endpoint
   - Passes question and Slack context
   - Returns synthesized answer

### Event Flow

```
User posts message in Slack
    ↓
Slack Events API sends webhook
    ↓
POST /slack/events (FastAPI)
    ↓
Verify Slack signature
    ↓
Extract message & channel
    ↓
Check if channel is monitored
    ↓
Queue background task
    ↓
Call daemon: POST /protocol/slack/answer
    ↓
Daemon searches knowledge base & synthesizes answer
    ↓
Return answer to bot
    ↓
Post response via Slack SDK
    ↓
Message appears in Slack thread
```

## Security Considerations

- **Never commit `.env` file** - Contains sensitive credentials
- **Use HTTPS** - Required for Slack webhooks (use ngrok for testing)
- **Verify Slack signatures** - Prevents unauthorized webhook calls
- **Scope restrictions** - Only request necessary Slack permissions
- **Channel filtering** - Optionally restrict to specific channel(s)

## Advanced Configuration

### Configuring Trigger Keywords

By default, the bot responds in channels when messages contain:
- Bot names: "localbrain", "local brain", "lb"
- Questions: "?", "help", "explain", "what", "how", "where", "why", "when", "who"
- @mentions

Add custom keywords in `.env`:

```env
TRIGGER_KEYWORDS=internship,interview,job,offer,resume,startup,funding
```

**Examples:**

```
"Where are you getting internships?" → ✅ Responds ("where" + "internship")
"I like pizza" → ❌ Ignores (no keywords)
"localbrain what's your opinion?" → ✅ Responds ("localbrain")
"How does this work?" → ✅ Responds ("how" + "?")
"Tell me about your job search" → ✅ Responds ("job")
```

**Note**: DMs always respond to ALL messages, regardless of keywords.

### Monitoring Multiple Channels

Leave `SLACK_CHANNEL_ID` empty in `.env`:

```env
SLACK_CHANNEL_ID=
```

Then invite the bot to multiple channels. It will respond in all of them.

### Only Responding to @Mentions

Remove `message.channels` from Event Subscriptions and only keep `app_mention`. The bot will only respond when explicitly mentioned.

### Custom Daemon Endpoint

If your daemon runs on a different machine:

```env
DAEMON_URL=https://your-daemon-server.com:8765
```

## Future Enhancements

- [ ] Add conversation memory across threads
- [ ] Support private channels and DMs
- [ ] Add admin commands (e.g., `/localbrain status`)
- [ ] Implement caching for frequent queries
- [ ] Add analytics and usage tracking
- [ ] Support file attachments
- [ ] Add reaction-based feedback

## License

MIT

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review server logs (`bot.log`)
3. Test each component individually
4. Check Slack app event logs in the Slack API dashboard
