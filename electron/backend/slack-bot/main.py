"""
LocalBrain Slack Bot

A simple Slack bot that:
1. Listens for messages in specified channel(s) via Slack Events API
2. Sends questions to LocalBrain daemon
3. Posts responses back to Slack

No external dependencies like Composio - just direct Slack SDK integration.
"""

import os
import json
import hmac
import hashlib
import time
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")  # Optional: if empty, responds to all channels
DAEMON_URL = os.getenv("DAEMON_URL", "http://127.0.0.1:8765")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Validate required environment variables
required_vars = {
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
    "SLACK_SIGNING_SECRET": SLACK_SIGNING_SECRET,
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize FastAPI app
app = FastAPI(title="LocalBrain Slack Bot")

# Initialize Slack client
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# HTTP client for daemon requests
http_client = httpx.AsyncClient(timeout=30.0)


def verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """
    Verify that the request came from Slack by validating the signature.

    Args:
        request_body: Raw request body
        timestamp: X-Slack-Request-Timestamp header
        signature: X-Slack-Signature header

    Returns:
        True if signature is valid, False otherwise
    """
    # Prevent replay attacks
    if abs(time.time() - int(timestamp)) > 60 * 5:
        logger.warning("Request timestamp too old")
        return False

    # Create signature base string
    sig_basestring = f"v0:{timestamp}:{request_body.decode('utf-8')}"

    # Calculate expected signature
    expected_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # Compare signatures
    return hmac.compare_digest(expected_signature, signature)


async def ask_daemon(question: str, slack_context: dict) -> str:
    """
    Send question to LocalBrain daemon and get answer.

    Args:
        question: The user's question
        slack_context: Dict with server_name, channel_name, asker_name, thread_id

    Returns:
        Answer string from daemon
    """
    try:
        logger.info(f"Asking daemon: {question}")

        response = await http_client.post(
            f"{DAEMON_URL}/protocol/slack/answer",
            json={
                "question": question,
                "slack_context": slack_context
            }
        )

        response.raise_for_status()
        result = response.json()

        answer = result.get("answer", "I couldn't generate an answer.")
        logger.info(f"Daemon responded: {answer[:100]}...")
        return answer

    except httpx.HTTPError as e:
        logger.error(f"Error calling daemon: {e}")
        return "Sorry, I'm having trouble accessing my knowledge base right now."
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "Sorry, something went wrong while processing your question."


async def send_slack_message(channel: str, text: str, thread_ts: Optional[str] = None):
    """
    Send a message to Slack using the Slack SDK.

    Args:
        channel: Channel ID to send to
        text: Message text
        thread_ts: Thread timestamp for replies (optional)
    """
    try:
        logger.info(f"Sending message to Slack channel {channel}")

        # Use Slack SDK to post message
        response = slack_client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts
        )

        logger.info("Message sent successfully")
        return response

    except SlackApiError as e:
        logger.error(f"Error sending Slack message: {e.response['error']}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        raise


async def process_message(
    channel: str,
    text: str,
    user: str,
    thread_ts: Optional[str] = None,
    team_id: Optional[str] = None
):
    """
    Process a message from Slack: send to daemon and post response.

    Args:
        channel: Channel ID
        text: Message text
        user: User ID who sent the message
        thread_ts: Thread timestamp (optional)
        team_id: Slack team/workspace ID
    """
    try:
        logger.info(f"Processing message from user {user}: {text}")

        # Build Slack context for daemon
        slack_context = {
            "server_name": team_id or "Slack Workspace",
            "channel_name": channel,
            "asker_name": user,
            "thread_id": thread_ts or ""
        }

        # Get answer from daemon
        answer = await ask_daemon(text, slack_context)

        # Send response back to Slack
        await send_slack_message(
            channel=channel,
            text=answer,
            thread_ts=thread_ts
        )

        logger.info("Message processed successfully")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # Try to send error message to Slack
        try:
            await send_slack_message(
                channel=channel,
                text=f"Sorry, I encountered an error: {str(e)}",
                thread_ts=thread_ts
            )
        except:
            logger.error("Failed to send error message to Slack")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "LocalBrain Slack Bot",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "daemon_url": DAEMON_URL,
        "slack_channel": SLACK_CHANNEL_ID or "all channels",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack Events API webhook.

    This endpoint receives events from Slack when messages are posted
    in the monitored channel(s).
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify Slack signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not verify_slack_signature(body, timestamp, signature):
        logger.warning("Invalid Slack signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON body
    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle URL verification challenge
    if event_data.get("type") == "url_verification":
        logger.info("Handling URL verification challenge")
        return JSONResponse({"challenge": event_data.get("challenge")})

    # Handle event callbacks
    if event_data.get("type") == "event_callback":
        event = event_data.get("event", {})
        event_type = event.get("type")

        # Process message events (both channels and DMs)
        if event_type == "message":
            channel = event.get("channel")
            channel_type = event.get("channel_type", "")
            text = event.get("text", "")
            user = event.get("user")
            thread_ts = event.get("thread_ts") or event.get("ts")
            team_id = event_data.get("team_id")

            # Ignore bot messages to prevent loops
            if event.get("bot_id"):
                logger.info("Ignoring bot message")
                return JSONResponse({"status": "ok"})

            # Ignore message edits and deletions
            if event.get("subtype") in ["message_changed", "message_deleted"]:
                logger.info(f"Ignoring message subtype: {event.get('subtype')}")
                return JSONResponse({"status": "ok"})

            # Check if this is a DM (channel starts with 'D' or channel_type is 'im')
            is_dm = channel.startswith("D") if channel else False
            if channel_type == "im":
                is_dm = True

            # If SLACK_CHANNEL_ID is set, only process messages from that channel (unless it's a DM)
            if SLACK_CHANNEL_ID and channel != SLACK_CHANNEL_ID and not is_dm:
                logger.info(f"Ignoring message from channel {channel} (not monitoring)")
                return JSONResponse({"status": "ok"})

            # Log message type
            message_type = "DM" if is_dm else "channel"
            logger.info(f"Received {message_type} message from user {user}")

            # Process message in background to avoid timeout
            background_tasks.add_task(
                process_message,
                channel=channel,
                text=text,
                user=user,
                thread_ts=thread_ts,
                team_id=team_id
            )

            logger.info(f"Queued {message_type} message for processing: {text[:50]}...")

        # Handle app mentions (when bot is @mentioned)
        elif event_type == "app_mention":
            channel = event.get("channel")
            text = event.get("text", "")
            user = event.get("user")
            thread_ts = event.get("thread_ts") or event.get("ts")
            team_id = event_data.get("team_id")

            # Remove bot mention from text
            # Slack mentions look like: <@U01234567> rest of message
            import re
            text = re.sub(r'<@[A-Z0-9]+>\s*', '', text).strip()

            # Process message in background
            background_tasks.add_task(
                process_message,
                channel=channel,
                text=text,
                user=user,
                thread_ts=thread_ts,
                team_id=team_id
            )

            logger.info(f"Queued mention for processing: {text[:50]}...")

    return JSONResponse({"status": "ok"})


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await http_client.aclose()
    logger.info("HTTP client closed")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting LocalBrain Slack Bot on {HOST}:{PORT}")
    logger.info(f"Daemon URL: {DAEMON_URL}")
    if SLACK_CHANNEL_ID:
        logger.info(f"Monitoring channel: {SLACK_CHANNEL_ID}")
    else:
        logger.info("Monitoring all channels where bot is added")

    uvicorn.run(app, host=HOST, port=PORT)
