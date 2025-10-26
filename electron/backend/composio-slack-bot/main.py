"""
Composio Slack Bot with LocalBrain MCP Integration

Monitors #ask-directors channel, uses LocalBrain MCP to search for information,
and responds using an LLM via Composio.
"""

import os
import json
import hmac
import hashlib
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx
from composio_openai import ComposioToolSet, App
from openai import OpenAI
from anthropic import Anthropic

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
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
MCP_URL = os.getenv("MCP_URL")
MCP_API_KEY = os.getenv("MCP_API_KEY")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Validate required environment variables
required_vars = {
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
    "SLACK_SIGNING_SECRET": SLACK_SIGNING_SECRET,
    "SLACK_CHANNEL_ID": SLACK_CHANNEL_ID,
    "COMPOSIO_API_KEY": COMPOSIO_API_KEY,
    "MCP_URL": MCP_URL,
    "MCP_API_KEY": MCP_API_KEY,
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'")
elif LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER is 'anthropic'")

# Initialize FastAPI app
app = FastAPI(title="LocalBrain Slack Bot")

# Initialize LLM client
if LLM_PROVIDER == "openai":
    llm_client = OpenAI(api_key=OPENAI_API_KEY)
elif LLM_PROVIDER == "anthropic":
    llm_client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    raise ValueError(f"Invalid LLM_PROVIDER: {LLM_PROVIDER}")

# Initialize Composio
composio_toolset = ComposioToolSet(api_key=COMPOSIO_API_KEY)

# HTTP client for MCP requests
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


async def search_localbrain(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Search LocalBrain MCP for relevant information.
    
    Args:
        query: Search query
        top_k: Number of results to return
    
    Returns:
        Search results from LocalBrain
    """
    try:
        logger.info(f"Searching LocalBrain for: {query}")
        
        response = await http_client.post(
            f"{MCP_URL}/search",
            headers={
                "X-API-Key": MCP_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "query": query,
                "top_k": top_k
            }
        )
        
        response.raise_for_status()
        results = response.json()
        
        logger.info(f"LocalBrain returned {len(results.get('results', []))} results")
        return results
        
    except httpx.HTTPError as e:
        logger.error(f"Error searching LocalBrain: {e}")
        return {"results": [], "error": str(e)}


def format_search_results(results: Dict[str, Any]) -> str:
    """
    Format LocalBrain search results for LLM context.
    
    Args:
        results: Search results from LocalBrain
    
    Returns:
        Formatted string for LLM context
    """
    if not results.get("results"):
        return "No relevant information found in LocalBrain."
    
    formatted = "Relevant information from LocalBrain:\n\n"
    
    for i, result in enumerate(results["results"], 1):
        formatted += f"{i}. **{result.get('file', 'Unknown file')}**\n"
        formatted += f"   Score: {result.get('score', 0):.2f}\n"
        formatted += f"   Content: {result.get('content', 'No content')}\n\n"
    
    return formatted


async def generate_response_openai(query: str, context: str) -> str:
    """
    Generate response using OpenAI GPT.
    
    Args:
        query: User's question
        context: Context from LocalBrain search
    
    Returns:
        Generated response
    """
    try:
        system_prompt = """You are a helpful assistant for Cal Hacks 12.0 hackathon directors. 
You have access to LocalBrain, a knowledge base with information about the hackathon.
Use the provided context to answer questions accurately and concisely.
If the context doesn't contain relevant information, say so clearly."""
        
        user_prompt = f"""Question: {query}

Context from LocalBrain:
{context}

Please provide a helpful answer based on the context above. If the context doesn't contain relevant information, let the user know."""
        
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating OpenAI response: {e}")
        return f"Sorry, I encountered an error generating a response: {str(e)}"


async def generate_response_anthropic(query: str, context: str) -> str:
    """
    Generate response using Anthropic Claude.
    
    Args:
        query: User's question
        context: Context from LocalBrain search
    
    Returns:
        Generated response
    """
    try:
        system_prompt = """You are a helpful assistant for Cal Hacks 12.0 hackathon directors. 
You have access to LocalBrain, a knowledge base with information about the hackathon.
Use the provided context to answer questions accurately and concisely.
If the context doesn't contain relevant information, say so clearly."""
        
        user_prompt = f"""Question: {query}

Context from LocalBrain:
{context}

Please provide a helpful answer based on the context above. If the context doesn't contain relevant information, let the user know."""
        
        response = llm_client.messages.create(
            model=LLM_MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return response.content[0].text
        
    except Exception as e:
        logger.error(f"Error generating Anthropic response: {e}")
        return f"Sorry, I encountered an error generating a response: {str(e)}"


async def send_slack_message(channel: str, text: str, thread_ts: Optional[str] = None):
    """
    Send a message to Slack using Composio.
    
    Args:
        channel: Channel ID to send to
        text: Message text
        thread_ts: Thread timestamp for replies (optional)
    """
    try:
        logger.info(f"Sending message to Slack channel {channel}")
        
        # Use Composio to send Slack message
        action = composio_toolset.execute_action(
            action=App.SLACK_CHAT_POST_MESSAGE,
            params={
                "channel": channel,
                "text": text,
                "thread_ts": thread_ts
            }
        )
        
        logger.info("Message sent successfully via Composio")
        return action
        
    except Exception as e:
        logger.error(f"Error sending Slack message via Composio: {e}")
        # Fallback: Try direct Slack API
        try:
            response = await http_client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": channel,
                    "text": text,
                    "thread_ts": thread_ts
                }
            )
            response.raise_for_status()
            logger.info("Message sent successfully via direct Slack API")
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")


async def process_message(channel: str, text: str, user: str, thread_ts: Optional[str] = None):
    """
    Process a message from Slack: search LocalBrain and generate response.
    
    Args:
        channel: Channel ID
        text: Message text
        user: User ID who sent the message
        thread_ts: Thread timestamp (optional)
    """
    try:
        logger.info(f"Processing message from user {user}: {text}")
        
        # Search LocalBrain for relevant information
        search_results = await search_localbrain(text)
        
        # Format search results for LLM
        context = format_search_results(search_results)
        
        # Generate response using LLM
        if LLM_PROVIDER == "openai":
            response_text = await generate_response_openai(text, context)
        else:
            response_text = await generate_response_anthropic(text, context)
        
        # Send response back to Slack
        await send_slack_message(
            channel=channel,
            text=response_text,
            thread_ts=thread_ts or None
        )
        
        logger.info("Message processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # Send error message to Slack
        await send_slack_message(
            channel=channel,
            text=f"Sorry, I encountered an error: {str(e)}",
            thread_ts=thread_ts
        )


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
        "mcp_url": MCP_URL,
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "slack_channel": SLACK_CHANNEL_ID
    }


@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack Events API webhook.
    
    This endpoint receives events from Slack when messages are posted
    in the monitored channel.
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
        
        # Only process message events
        if event_type == "message":
            channel = event.get("channel")
            text = event.get("text", "")
            user = event.get("user")
            thread_ts = event.get("thread_ts") or event.get("ts")
            
            # Ignore bot messages to prevent loops
            if event.get("bot_id"):
                logger.info("Ignoring bot message")
                return JSONResponse({"status": "ok"})
            
            # Only process messages from the target channel
            if channel != SLACK_CHANNEL_ID:
                logger.info(f"Ignoring message from channel {channel}")
                return JSONResponse({"status": "ok"})
            
            # Process message in background to avoid timeout
            background_tasks.add_task(
                process_message,
                channel=channel,
                text=text,
                user=user,
                thread_ts=thread_ts
            )
            
            logger.info(f"Queued message for processing: {text[:50]}...")
    
    return JSONResponse({"status": "ok"})


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await http_client.aclose()
    logger.info("HTTP client closed")


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting LocalBrain Slack Bot on {HOST}:{PORT}")
    logger.info(f"LLM Provider: {LLM_PROVIDER} ({LLM_MODEL})")
    logger.info(f"MCP URL: {MCP_URL}")
    logger.info(f"Monitoring channel: {SLACK_CHANNEL_ID}")
    
    uvicorn.run(app, host=HOST, port=PORT)
