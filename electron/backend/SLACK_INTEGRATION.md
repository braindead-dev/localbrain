# Slack Bot Integration Guide

## Overview

LocalBrain now supports Slack bot integration! The bot can answer questions by posing as you, using your personal knowledge vault. It automatically adapts its tone based on the Slack workspace/channel context and includes guardrails to protect your reputation.

## Architecture

### Key Components

1. **`slack_synthesizer.py`** - Specialized answer synthesizer that:
   - Poses as the user (first-person responses)
   - Adapts tone based on Slack context (workspace, channel, asker)
   - Protects user reputation with built-in guardrails
   - Returns clean answers without source citations

2. **`/protocol/slack/answer`** - Direct API endpoint for custom integrations
3. **`/protocol/slack/webhook`** - Slack Events API webhook handler

## Endpoints

### 1. `/protocol/slack/answer` (Direct API)

Use this endpoint for custom Slack app integrations where you control the message handling.

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
  "clear_history": false  // optional
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

### 2. `/protocol/slack/webhook` (Slack Events API)

Use this endpoint to integrate directly with Slack's Events API.

**Setup:**
1. Create a Slack App at https://api.slack.com/apps
2. Enable Event Subscriptions
3. Set Request URL to: `http://your-domain:8765/protocol/slack/webhook`
   - For local dev, use ngrok: `ngrok http 8765`
4. Subscribe to bot events:
   - `app_mention` (when someone @mentions the bot)
   - `message.im` (for direct messages)
5. Install the app to your workspace

**How it works:**
1. User mentions bot in Slack: `@LocalBrain what was my Meta offer?`
2. Slack sends event to webhook endpoint
3. LocalBrain searches vault, synthesizes answer
4. Response returned (you'll need to POST back to Slack via `chat.postMessage`)

## Features

### Tone Adaptation
The bot analyzes the Slack context to determine appropriate tone:
- **Workspace name** contains "Inc", "Corp", company names → Professional tone
- **Channel name** contains "work", "team", "project" → Professional tone
- **Otherwise** → Friendly, conversational tone
- **Default** → Friendly-professional hybrid

### Conversation Memory
- Maintains last 25 messages in conversation history
- Works across all channels/threads (like the main app)
- Enables follow-up questions: "What about the benefits?" after "What was my offer?"

### Reputation Protection
Built-in guardrails prevent the bot from:
- Saying anything offensive, discriminatory, or inappropriate
- Sharing confidential information in wrong contexts
- Making claims not supported by your knowledge vault
- Harming your professional reputation

### User Impersonation
The bot responds **as you**, using first-person:
- ✅ "I received an offer from Meta..."
- ❌ "The user received an offer from Meta..."

## Example Slack App (Node.js)

```javascript
const { App } = require('@slack/bolt');

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET
});

// Handle app mentions
app.event('app_mention', async ({ event, say }) => {
  try {
    // Extract question (remove bot mention)
    const question = event.text.replace(/<@\w+>/, '').trim();

    // Call LocalBrain API
    const response = await fetch('http://localhost:8765/protocol/slack/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        slack_context: {
          server_name: 'My Workspace',  // Fetch from Slack API
          channel_name: event.channel,
          asker_name: event.user,
          thread_id: event.thread_ts || event.ts
        }
      })
    });

    const data = await response.json();

    // Reply in thread
    await say({
      text: data.answer,
      thread_ts: event.ts
    });

  } catch (error) {
    console.error(error);
    await say('Sorry, I had trouble processing that.');
  }
});

(async () => {
  await app.start(3000);
  console.log('⚡️ Slack bot is running!');
})();
```

## Example Python Slack App

```python
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests

app = App(token="xoxb-your-token")

@app.event("app_mention")
def handle_mention(event, say):
    # Extract question
    question = event['text'].split('>', 1)[1].strip()

    # Call LocalBrain
    response = requests.post('http://localhost:8765/protocol/slack/answer', json={
        'question': question,
        'slack_context': {
            'server_name': 'My Workspace',
            'channel_name': event['channel'],
            'asker_name': event['user'],
            'thread_id': event.get('thread_ts', event['ts'])
        }
    })

    data = response.json()

    # Reply
    say(text=data['answer'], thread_ts=event['ts'])

if __name__ == "__main__":
    handler = SocketModeHandler(app, "xapp-your-app-token")
    handler.start()
```

## Testing

### 1. Test Direct Endpoint
```bash
curl -X POST http://localhost:8765/protocol/slack/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What technologies do I know?",
    "slack_context": {
      "server_name": "Tech Corp",
      "channel_name": "engineering",
      "asker_name": "Jane"
    }
  }'
```

### 2. Test Webhook Challenge
```bash
curl -X POST http://localhost:8765/protocol/slack/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "url_verification",
    "challenge": "test_challenge_123"
  }'
```

Should return: `{"challenge": "test_challenge_123"}`

### 3. Test Event Callback
```bash
curl -X POST http://localhost:8765/protocol/slack/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "event_callback",
    "team_id": "T123456",
    "event": {
      "type": "app_mention",
      "text": "<@U987654> What was my Meta offer?",
      "user": "U123456",
      "channel": "C123456",
      "ts": "1234567890.123456"
    }
  }'
```

## Production Considerations

### Security
1. **Verify Slack requests** - Check the `X-Slack-Signature` header
2. **Rate limiting** - Implement rate limits per user/channel
3. **Access control** - Restrict which workspaces can use the bot

### Performance
1. **Async processing** - Use background jobs for slow searches
2. **Caching** - Cache frequent queries
3. **Timeouts** - Slack expects responses within 3 seconds

### Privacy
1. **Audit logs** - Track what information is shared where
2. **Channel permissions** - Consider implementing channel-specific access rules
3. **Sensitive data** - Add filters to prevent sharing passwords, API keys, etc.

## Troubleshooting

### Bot not responding
- Check daemon logs: `tail -f /tmp/localbrain-daemon.log`
- Verify port 8765 is accessible
- Check Slack app configuration

### Wrong tone
- The tone is determined by LLM based on context
- Update prompts in `slack_synthesizer.py` if needed

### Memory issues
- Conversation history limited to 25 messages
- Shared across all channels (by design)
- Use `clear_history: true` to reset

## Next Steps

1. **Create Slack App** at https://api.slack.com/apps
2. **Set up ngrok** for local testing: `ngrok http 8765`
3. **Configure Event Subscriptions** with your webhook URL
4. **Write integration code** (see examples above)
5. **Test in private channel** first
6. **Deploy to production** when ready

## Support

For issues or questions:
- Check daemon logs: `/tmp/localbrain-daemon.log`
- File issues on GitHub
- Review Slack API documentation: https://api.slack.com/docs
