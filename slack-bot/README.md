# LocalBrain Slack Bot

A Slack bot that connects Slack to your LocalBrain daemon. When users ask questions in monitored channels, the bot retrieves answers from your LocalBrain knowledge base and responds as you, using first-person responses.

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

### Key Components

1. **FastAPI Server** (`main.py`)
   - Receives Slack events via webhook (`/slack/events`)
   - Validates Slack signatures for security
   - Routes messages to background processing

2. **Slack Synthesizer** (`slack_synthesizer.py`)
   - Poses as the user (first-person responses)
   - Adapts tone based on Slack context (workspace, channel, asker)
   - Protects user reputation with built-in guardrails
   - Returns clean answers without source citations

3. **Slack SDK Client**
   - Posts responses back to Slack
   - Handles threading automatically
   - Manages API rate limits

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

## Prerequisites

- Python 3.10+
- Slack workspace admin access
- LocalBrain daemon running at `http://127.0.0.1:8765` (or configured URL)

## Setup

### 1. Install Dependencies

```bash
cd slack-bot
pip install -r requirements.txt
```

### 2. Create Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `LocalBrain Assistant`
4. Select your workspace
5. Click **"Create App"**

### 3. Configure Bot Permissions

1. Go to **"OAuth & Permissions"**
2. Under **"Bot Token Scopes"**, add:
   - `chat:write` - Send messages
   - `channels:history` - Read channel messages
   - `channels:read` - View channel info
   - `im:history` - Read DM messages
   - `im:write` - Send DM messages
   - `app_mentions:read` - Read mentions

### 4. Enable Event Subscriptions

1. Go to **"Event Subscriptions"**
2. Toggle **"Enable Events"** to ON
3. **Request URL**: `https://your-domain.com/slack/events`
   - You'll need to deploy your server first or use ngrok for testing
4. Under **"Subscribe to bot events"**, add:
   - `message.channels` - Listen to messages in public channels
   - `message.im` - Listen to direct messages
   - `app_mention` - Listen to @mentions

### 5. Install App to Workspace

1. Go to **"Install App"**
2. Click **"Install to Workspace"**
3. Authorize the app
4. Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)

### 6. Get Signing Secret

1. Go to **"Basic Information"**
2. Under **"App Credentials"**, find **"Signing Secret"**
3. Click **"Show"** and copy it

### 7. Get Channel ID

1. Open Slack workspace in browser
2. Navigate to the channel you want to monitor
3. Copy the channel ID from URL
   - URL format: `https://app.slack.com/client/TXXXXXX/C01234ABCDE`
   - Channel ID is the last part: `C01234ABCDE`

### 8. Add Bot to Channel

1. In Slack, go to your target channel
2. Type `/invite @LocalBrain Assistant`

### 9. Configure Environment Variables

Create a `.env` file:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_CHANNEL_ID=C01234ABCDE

# LocalBrain Daemon Configuration
DAEMON_URL=http://127.0.0.1:8765

# Trigger Keywords (optional - comma-separated)
TRIGGER_KEYWORDS=internship,interview,job,offer,resume

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

**Note**: If you leave `SLACK_CHANNEL_ID` empty, the bot will respond to messages in all channels where it's been added.

## Running the Bot

### Local Testing with ngrok

1. Start your LocalBrain daemon:
   ```bash
   cd electron/backend
   python src/daemon.py
   ```

2. Start the Slack bot:
   ```bash
   cd slack-bot
   python main.py
   ```

3. Expose with ngrok:
   ```bash
   ngrok http 8000
   ```

4. Copy the HTTPS URL (e.g., `https://xyz789.ngrok.io`)

5. Update Slack Event Subscription URL:
   - Go to your Slack app settings
   - Navigate to **"Event Subscriptions"**
   - Set **Request URL** to: `https://xyz789.ngrok.io/slack/events`
   - Wait for the green "Verified" checkmark

## Features

### Smart Keyword Triggering
In channels, bot responds only when message contains:
- Bot name variations ("localbrain", "local brain", "lb")
- Question indicators ("?", "help", "what", "how", "where", "why", etc.)
- Custom keywords you configure (e.g., "internship", "job", "interview")
- @mentions of the bot

**Note**: DMs always respond to ALL messages automatically, regardless of keywords.

### Tone Adaptation
The bot analyzes the Slack context to determine appropriate tone:
- **Workspace name** contains "Inc", "Corp", company names → Professional tone
- **Channel name** contains "work", "team", "project" → Professional tone
- **Otherwise** → Friendly, conversational tone
- **Default** → Friendly-professional hybrid

### Conversation Memory
- Maintains last 25 messages in conversation history
- Works across all channels/threads
- Enables follow-up questions

### Other Features
- Thread support for organized conversations
- Signature verification for security
- Background processing to prevent timeouts
- Error handling with user notifications

## API Endpoints

### `/protocol/slack/answer` (Direct API)

Use this endpoint for custom Slack app integrations.

**Request:**
```bash
POST http://localhost:8765/protocol/slack/answer
Content-Type: application/json

{
  "question": "What was my Meta offer?",
  "slack_context": {
    "server_name": "ACME Corp Workspace",
    "channel_name": "engineering",
    "asker_name": "John Doe",
    "thread_id": "optional_thread_id"
  },
  "clear_history": false
}
```

**Response:**
```json
{
  "success": true,
  "question": "What was my Meta offer?",
  "answer": "I received a Senior Engineer offer from Meta with a $200k base salary...",
  "conversation_length": 12
}
```

### `/protocol/slack/webhook` (Slack Events API)

Webhook endpoint for direct integration with Slack's Events API.

## Configuration

### Monitor Multiple Channels

Leave `SLACK_CHANNEL_ID` empty in `.env`:
```env
SLACK_CHANNEL_ID=
```

Then invite the bot to any channels you want it to monitor.

### Only Respond to @Mentions

Remove `message.channels` from Event Subscriptions and only keep `app_mention`.

### Custom Trigger Keywords

Add custom keywords in `.env`:
```env
TRIGGER_KEYWORDS=internship,interview,job,offer,resume,startup,funding
```

### Custom Daemon URL

If your daemon runs on a different machine:
```env
DAEMON_URL=https://your-daemon-server.com:8765
```

## Future Enhancements

- Add agentic capabilities
- Add admin commands (e.g., `/localbrain status`)
- Implement caching for frequent queries
- Add analytics and usage tracking
- Support file attachments
- Add reaction-based feedback