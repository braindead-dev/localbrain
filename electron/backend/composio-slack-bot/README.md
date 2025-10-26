# Composio Slack Bot with LocalBrain MCP Integration

A Slack bot that monitors the `#ask-directors` channel in Cal Hacks 12.0 workspace, uses LocalBrain MCP to search for relevant information, and responds automatically using an LLM.

## Architecture

```
Slack Message → Slack Events API → FastAPI Webhook → LLM (OpenAI/Anthropic)
                                                        ↓
                                                   LocalBrain MCP
                                                   (via remote-mcp)
                                                        ↓
                                                   Search Results
                                                        ↓
                                                   Composio Slack API
                                                        ↓
                                                   Post Response
```

## How It Works

1. **Slack Events API** sends message events from `#ask-directors` to your webhook endpoint
2. **FastAPI Server** receives the event and extracts the message
3. **LLM** (GPT-4/Claude) processes the query with access to LocalBrain MCP tools
4. **LocalBrain MCP** searches your knowledge base for relevant information
5. **Composio** sends the LLM's response back to the Slack channel

## Prerequisites

- Python 3.8+
- Slack workspace admin access (to create apps and install bots)
- Composio account
- OpenAI API key or Anthropic API key
- LocalBrain MCP server running (either local or remote)

## Setup Instructions

### 1. Install Dependencies

```bash
cd electron/backend/composio-slack-bot
pip install -r requirements.txt
```

### 2. Set Up Slack App

#### Create Slack App:
1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `LocalBrain Assistant`
4. Workspace: Select your Cal Hacks 12.0 workspace
5. Click **"Create App"**

#### Configure Bot Permissions:
1. Go to **"OAuth & Permissions"** in the left sidebar
2. Scroll to **"Scopes"** → **"Bot Token Scopes"**
3. Add these scopes:
   - `chat:write` - Send messages
   - `channels:history` - Read channel messages
   - `channels:read` - View channel info
   - `app_mentions:read` - Read mentions (optional)

#### Enable Events:
1. Go to **"Event Subscriptions"** in the left sidebar
2. Toggle **"Enable Events"** to ON
3. **Request URL**: `https://your-domain.com/slack/events` (see deployment section)
   - You'll need to deploy your server first or use ngrok for testing
4. Under **"Subscribe to bot events"**, add:
   - `message.channels` - Listen to messages in public channels

#### Get Channel ID:
1. Open Slack workspace in browser
2. Navigate to `#ask-directors` channel
3. Copy the channel ID from URL (e.g., `C01234ABCDE`)
   - URL format: `https://app.slack.com/client/T.../C01234ABCDE`

#### Install App to Workspace:
1. Go to **"Install App"** in the left sidebar
2. Click **"Install to Workspace"**
3. Authorize the app
4. Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)

#### Add Bot to Channel:
1. In Slack, go to `#ask-directors` channel
2. Type `/invite @LocalBrain Assistant`
3. The bot will join the channel

### 3. Set Up Composio

#### Create Composio Account:
1. Go to https://app.composio.dev/
2. Sign up or log in
3. Go to **"API Keys"** section
4. Copy your **Composio API Key**

#### Connect Slack Integration:
1. In Composio dashboard, go to **"Integrations"**
2. Search for **"Slack"**
3. Click **"Connect"**
4. Authorize Composio to access your Slack workspace
5. Copy the **Integration ID** (you'll need this)

### 4. Set Up LocalBrain MCP

You have two options:

#### Option A: Use Remote MCP (Recommended for Production)

If you have a remote MCP bridge running:

```bash
# Navigate to remote-mcp directory
cd ../../../remote-mcp

# Follow the setup in remote-mcp/README.md
# You'll get a URL like: https://localbrain.henr.ee/u/YOUR_USER_ID
```

Use this URL in your `.env` file.

#### Option B: Use Local MCP (Development Only)

Start the local MCP server:

```bash
# From project root
python electron/backend/src/core/mcp/extension/start_servers.py
```

Then use ngrok to expose it:

```bash
ngrok http 8766
# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

### 5. Configure Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_CHANNEL_ID=C01234ABCDE

# Composio Configuration
COMPOSIO_API_KEY=your-composio-api-key-here

# LLM Configuration (choose one)
OPENAI_API_KEY=sk-your-openai-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Choose LLM provider: "openai" or "anthropic"
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview

# LocalBrain MCP Configuration
MCP_URL=https://localbrain.henr.ee/u/YOUR_USER_ID
MCP_API_KEY=lb_your-remote-api-key-here

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### 6. Run the Bot

#### For Development (Local):

```bash
python main.py
```

Then use ngrok to expose the webhook:

```bash
ngrok http 8000
```

Copy the HTTPS URL and update your Slack app's **Event Subscriptions** → **Request URL** to:
```
https://your-ngrok-url.ngrok.io/slack/events
```

#### For Production:

Deploy to a server with a public domain (see Deployment section below).

## Testing

1. Go to `#ask-directors` channel in Slack
2. Send a message: "What are the hackathon rules?"
3. The bot should:
   - Receive the message via webhook
   - Search LocalBrain for relevant info
   - Respond with an answer in the thread

## Deployment

### Option 1: Railway

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Add environment variables: `railway variables set KEY=value`
5. Deploy: `railway up`
6. Get URL: `railway domain`

### Option 2: DigitalOcean App Platform

1. Create a new app from GitHub repo
2. Set environment variables in the dashboard
3. Deploy
4. Copy the app URL

### Option 3: Docker + VPS

```bash
# Build Docker image
docker build -t slack-bot .

# Run container
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  --name slack-bot \
  slack-bot
```

## Environment Variables Reference

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SLACK_BOT_TOKEN` | Bot User OAuth Token from Slack | Yes | `xoxb-...` |
| `SLACK_SIGNING_SECRET` | Signing secret from Slack app settings | Yes | `abc123...` |
| `SLACK_CHANNEL_ID` | Channel ID for #ask-directors | Yes | `C01234ABCDE` |
| `COMPOSIO_API_KEY` | API key from Composio dashboard | Yes | `comp_...` |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI) | Conditional | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Claude) | Conditional | `sk-ant-...` |
| `LLM_PROVIDER` | LLM provider to use | Yes | `openai` or `anthropic` |
| `LLM_MODEL` | Model name | Yes | `gpt-4-turbo-preview` |
| `MCP_URL` | LocalBrain MCP endpoint URL | Yes | `https://...` |
| `MCP_API_KEY` | API key for MCP authentication | Yes | `lb_...` |
| `HOST` | Server host | No | `0.0.0.0` |
| `PORT` | Server port | No | `8000` |

## Troubleshooting

### Bot not responding:
- Check that the bot is invited to `#ask-directors` channel
- Verify webhook URL is correct in Slack app settings
- Check server logs for errors: `tail -f bot.log`

### MCP connection errors:
- Ensure LocalBrain MCP server is running
- Verify MCP_URL and MCP_API_KEY are correct
- Test MCP endpoint manually:
  ```bash
  curl -X POST $MCP_URL/search \
    -H "X-API-Key: $MCP_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"query": "test", "top_k": 3}'
  ```

### Slack verification failed:
- Check that `SLACK_SIGNING_SECRET` matches the one in Slack app settings
- Ensure server time is synchronized (for signature verification)

### Composio errors:
- Verify Composio API key is valid
- Check that Slack integration is connected in Composio dashboard
- Ensure bot has `chat:write` permission

## Architecture Details

### Components

1. **FastAPI Server** (`main.py`)
   - Receives Slack events via webhook
   - Validates Slack signatures
   - Routes messages to LLM handler

2. **LLM Handler**
   - Processes user queries
   - Calls LocalBrain MCP for context
   - Generates responses

3. **LocalBrain MCP Client**
   - Searches knowledge base
   - Returns relevant documents
   - Formats results for LLM

4. **Composio Slack Client**
   - Posts responses back to Slack
   - Handles threading
   - Manages rate limits

### Data Flow

```
User Message
    ↓
Slack Events API
    ↓
POST /slack/events (FastAPI)
    ↓
Verify Slack Signature
    ↓
Extract message & channel
    ↓
Check if channel == ask-directors
    ↓
Call LLM with query
    ↓
LLM calls LocalBrain MCP search tool
    ↓
MCP returns relevant documents
    ↓
LLM generates response
    ↓
Post response via Composio
    ↓
Message appears in Slack thread
```

## Security Considerations

- **Never commit `.env` file** - It contains sensitive credentials
- **Use HTTPS** - Required for Slack webhooks
- **Verify Slack signatures** - Prevents unauthorized webhook calls
- **Rate limiting** - Prevent abuse and API quota exhaustion
- **Scope restrictions** - Only listen to specific channels

## Future Enhancements

- [ ] Add conversation memory for follow-up questions
- [ ] Support multiple channels
- [ ] Add admin commands (e.g., `/localbrain status`)
- [ ] Implement caching for frequent queries
- [ ] Add analytics and usage tracking
- [ ] Support file uploads and attachments
- [ ] Add reaction-based feedback system

## License

MIT

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review server logs
3. Test each component individually
4. Open an issue on GitHub
