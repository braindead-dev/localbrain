#!/usr/bin/env python3
"""
LocalBrain Background Daemon

Runs as a background service (even when Electron app is closed) and handles:
- localbrain:// protocol requests
- Background ingestion tasks
- System tray menu

Usage:
    python src/daemon.py
"""

import sys
import json
import logging
import asyncio
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime
from typing import Dict, Optional, List

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Load environment
dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from agentic_ingest import AgenticIngestionPipeline
from agentic_search import Search
from agentic_synthesis import AnswerSynthesizer
from slack_synthesizer import SlackAnswerSynthesizer
from bulk_ingest import BulkIngestionPipeline
from utils.file_ops import read_file
from config import load_config, update_config, get_vault_path
from connectors.browser.ingest import ingest_browser_data

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/localbrain-daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('localbrain-daemon')

# Load config first
CONFIG = load_config()
VAULT_PATH = get_vault_path()
PORT = CONFIG.get('port', 8765)

# FastAPI app
app = FastAPI(title="LocalBrain Background Service")

# MCP process tracking
mcp_process: Optional[subprocess.Popen] = None

# Conversation history storage (simple in-memory, last 25 messages)
conversation_history: List[Dict] = []
MAX_CONVERSATION_HISTORY = 25

# Include connector plugin routes
from connectors.connector_api import create_connector_router
app.include_router(create_connector_router(vault_path=VAULT_PATH))

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Background task for auto-syncing all connectors
async def auto_sync_connectors():
    """Background task that syncs all connected connectors every 10 minutes."""
    await asyncio.sleep(60)  # Wait 1 minute after startup before first sync
    
    while True:
        try:
            logger.info("🔄 Auto-sync: Checking all connectors...")
            from connectors.connector_manager import get_connector_manager
            
            manager = get_connector_manager(vault_path=VAULT_PATH)
            results = manager.sync_all(auto_ingest=True)
            
            # Log results
            for connector_id, result in results.items():
                if result.success:
                    logger.info(f"✅ {connector_id}: {result.items_fetched} fetched, {result.items_ingested} ingested")
                else:
                    logger.error(f"❌ {connector_id}: {', '.join(result.errors)}")
                
        except Exception as e:
            logger.error(f"Auto-sync error: {e}")
        
        # Wait 10 minutes before next sync
        await asyncio.sleep(600)  # 600 seconds = 10 minutes


# Background task for auto-syncing Google Calendar
async def auto_sync_calendar():
    """Background task that syncs Google Calendar every 1 hour."""
    await asyncio.sleep(120)  # Wait 2 minutes after startup before first sync
    
    while True:
        try:
            logger.info("📅 Auto-sync: Checking Google Calendar...")
            from connectors.calendar.calendar_connector import CalendarConnector
            
            connector = CalendarConnector(vault_path=VAULT_PATH)
            
            if connector.is_authenticated():
                # Check if initial sync is needed (first connection)
                if connector.needs_initial_sync():
                    logger.info("📅 Auto-sync: First connection detected, performing initial sync (30 days)...")
                    result = connector.initial_sync(max_results=500)
                    logger.info(f"📅 Auto-sync: Initial sync completed - fetched {result.get('events_processed', 0)} events from past 30 days")
                else:
                    logger.info("📅 Auto-sync: Syncing Calendar...")
                    result = connector.sync(max_results=100, days=7)
                
                if result['success'] and result['events']:
                    logger.info(f"📅 Auto-sync: Found {len(result['events'])} calendar events, ingesting...")
                    pipeline = AgenticIngestionPipeline(VAULT_PATH)
                    
                    ingested = 0
                    for event_data in result['events']:
                        try:
                            pipeline.ingest(
                                context=event_data['text'],
                                source_metadata=event_data['metadata']
                            )
                            ingested += 1
                        except Exception as e:
                            logger.error(f"Failed to ingest calendar event: {e}")
                    
                    logger.info(f"✅ Auto-sync: Successfully ingested {ingested}/{len(result['events'])} calendar events")
                else:
                    logger.info("📅 Auto-sync: No new calendar events found")
            else:
                logger.debug("Auto-sync: Google Calendar not connected, skipping")
                
        except Exception as e:
            logger.error(f"Calendar auto-sync error: {e}")
        
        # Wait 1 hour before next sync
        await asyncio.sleep(3600)  # 3600 seconds = 1 hour

@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    # DISABLED: Auto-sync removed - all syncing is now manual only
    # asyncio.create_task(auto_sync_connectors())
    logger.info("⚠️  Auto-sync DISABLED - all syncing is manual only")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "localbrain-daemon"}


@app.post("/mcp/start")
async def start_mcp():
    """Start the MCP server with remote tunnel."""
    global mcp_process
    
    if mcp_process and mcp_process.poll() is None:
        return {"success": True, "message": "MCP already running", "pid": mcp_process.pid}
    
    try:
        # Start the MCP server launcher (includes tunnel)
        backend_dir = Path(__file__).parent.parent
        launcher_path = backend_dir / "src" / "core" / "mcp" / "extension" / "start_servers.py"
        
        mcp_process = subprocess.Popen(
            [sys.executable, str(launcher_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=backend_dir
        )
        
        logger.info(f"✅ MCP server started (PID: {mcp_process.pid})")
        return {
            "success": True,
            "message": "MCP server starting",
            "pid": mcp_process.pid
        }
    except Exception as e:
        logger.error(f"Failed to start MCP: {e}")
        return {"success": False, "error": str(e)}


@app.post("/mcp/stop")
async def stop_mcp():
    """Stop the MCP server."""
    global mcp_process
    
    if not mcp_process or mcp_process.poll() is not None:
        return {"success": True, "message": "MCP not running"}
    
    try:
        mcp_process.terminate()
        mcp_process.wait(timeout=5)
        logger.info("✅ MCP server stopped")
        mcp_process = None
        return {"success": True, "message": "MCP server stopped"}
    except subprocess.TimeoutExpired:
        mcp_process.kill()
        logger.warning("⚠️ MCP server force killed")
        mcp_process = None
        return {"success": True, "message": "MCP server force stopped"}
    except Exception as e:
        logger.error(f"Failed to stop MCP: {e}")
        return {"success": False, "error": str(e)}


@app.get("/mcp/status")
async def mcp_status():
    """Get MCP server status."""
    if mcp_process and mcp_process.poll() is None:
        return {"running": True, "pid": mcp_process.pid}
    return {"running": False}


@app.get("/config")
async def get_config():
    """
    Get current configuration.
    
    Returns:
        Current config including vault_path, port, etc.
    """
    config = load_config()
    return JSONResponse(content={
        'vault_path': config['vault_path'],
        'port': config['port'],
        'auto_start': config.get('auto_start', True)
    })


@app.put("/config")
async def update_config_endpoint(request: Request):
    """
    Update configuration.
    
    Body:
        {
            "vault_path": "/path/to/vault",  # optional
            "port": 8765,                     # optional
            "auto_start": true                # optional
        }
    
    Note: Changing vault_path or port requires restart.
    """
    try:
        body = await request.json()
        
        # Validate vault_path if provided
        if 'vault_path' in body:
            vault_path = Path(body['vault_path']).expanduser()
            if not vault_path.exists():
                return JSONResponse(
                    status_code=400,
                    content={'error': f'Path does not exist: {body["vault_path"]}'}
                )
            if not vault_path.is_dir():
                return JSONResponse(
                    status_code=400,
                    content={'error': f'Path is not a directory: {body["vault_path"]}'}
                )
            # Store absolute path
            body['vault_path'] = str(vault_path)
        
        # Update config
        updated_config = update_config(body)
        
        # Check if restart needed
        restart_needed = 'vault_path' in body or 'port' in body
        
        return JSONResponse(content={
            'success': True,
            'config': updated_config,
            'restart_required': restart_needed,
            'message': 'Config updated. Restart daemon to apply changes.' if restart_needed else 'Config updated.'
        })
        
    except Exception as e:
        logger.exception("Error updating config")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


@app.post("/protocol/ingest")
async def handle_ingest(request: Request):
    """
    Handle localbrain://ingest protocol requests.
    
    Expected format:
        localbrain://ingest?text=...&platform=...&timestamp=...&url=...
    
    Query parameters:
        - text (required): Content to ingest
        - platform (optional): Source platform (e.g., "Gmail", "Calendar")
        - timestamp (optional): ISO 8601 timestamp
        - url (optional): Source URL
    """
    try:
        # Parse request body
        body = await request.json()
        text = body.get('text', '')
        platform = body.get('platform', 'Manual')
        timestamp = body.get('timestamp', datetime.utcnow().isoformat() + 'Z')
        url = body.get('url')
        
        if not text:
            return JSONResponse(
                status_code=400,
                content={'error': 'Missing required parameter: text'}
            )
        
        logger.info(f"Ingesting content from {platform}")
        logger.info(f"Text preview: {text[:100]}...")
        
        # Build metadata
        # Note: 'quote' is LLM-generated during ingestion
        metadata = {
            'platform': platform,
            'timestamp': timestamp,
            'url': url,
            'quote': None  # Will be auto-generated by ContentAnalyzer
        }
        
        # Run ingestion
        pipeline = AgenticIngestionPipeline(VAULT_PATH)
        result = pipeline.ingest(text, metadata, max_retries=3)
        
        if result['success']:
            logger.info("Ingestion successful")
            return JSONResponse(content={
                'success': True,
                'files_created': result.get('files_created', []),
                'files_modified': result.get('files_modified', []),
                'message': 'Content ingested successfully'
            })
        else:
            logger.error(f"Ingestion failed: {result.get('errors', [])}")
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'errors': result.get('errors', []),
                    'message': 'Ingestion failed'
                }
            )
    
    except Exception as e:
        logger.exception("Error handling ingest request")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


@app.post("/browser/ingest")
async def handle_browser_ingest(request: Request):
    """
    Ingest data from the browser connector.
    
    Follows the same pattern as Gmail and Calendar connectors:
    - Accepts raw JSON data from browser
    - Preprocesses into structured format (text + metadata)
    - Uses AgenticIngestionPipeline for intelligent ingestion
    
    Body:
        {
            "items": [
                {
                    "title": "Page Title",
                    "url": "https://example.com",
                    "content": "Page content...",
                    "timestamp": "2025-01-26T10:00:00Z",  // optional
                    "metadata": {...}  // optional additional metadata
                }
            ]
        }
    
    Response:
        {
            "success": true,
            "items_processed": 10,
            "items_ingested": 10,
            "errors": []
        }
    """
    try:
        body = await request.json()
        items = body.get('items', [])
        
        if not items:
            return JSONResponse(
                status_code=400,
                content={'error': 'Missing required parameter: items'}
            )
        
        result = ingest_browser_data(items, VAULT_PATH)
        
        return JSONResponse(content=result)
            
    except Exception as e:
        logger.exception("Error handling browser ingest request")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


@app.post("/protocol/bulk-ingest")
async def handle_bulk_ingest(request: Request):
    """
    Bulk ingestion endpoint for large datasets.
    
    Much faster than individual ingestion - batches items and processes them together.
    Ideal for:
    - Initializing vault with large dataset
    - Importing chat history
    - Evaluation/testing
    
    Body:
        {
            "items": [
                {"text": "...", "metadata": {...}},
                {"text": "...", "metadata": {...}}
            ],
            "batch_size": 10  // optional
        }
    """
    try:
        body = await request.json()
        
        items = body.get('items', [])
        batch_size = body.get('batch_size', 10)
        
        if not items:
            return JSONResponse(
                status_code=400,
                content={'error': 'Missing required parameter: items'}
            )
        
        logger.info(f"📦 Bulk ingest: {len(items)} items (batch_size={batch_size})")
        
        # Run bulk ingestion
        pipeline = BulkIngestionPipeline(VAULT_PATH)
        result = pipeline.bulk_ingest(items, batch_size=batch_size)
        
        if result.get('success'):
            stats = result['stats']
            logger.info(f"✅ Bulk ingest complete: {stats['successful']}/{stats['total_items']} successful")
            return JSONResponse(content={
                'success': True,
                **result['stats']
            })
        else:
            logger.error(f"❌ Bulk ingest failed")
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'error': result.get('error', 'Bulk ingestion failed')
                }
            )
    
    except Exception as e:
        logger.exception("Error handling bulk ingest request")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


@app.post("/protocol/search")
async def handle_search(request: Request):
    """
    Handle localbrain://search protocol requests.

    Natural language search - input any question, get relevant context + answer.
    Uses agentic retrieval (ripgrep + LLM with tools) under the hood.

    Expected format:
        localbrain://search?q=What was my Meta offer?

    Query parameters:
        - q (required): Natural language search query
    """
    try:
        # Parse request body
        body = await request.json()
        query = body.get('q', body.get('query', ''))  # Support both q and query

        if not query:
            return JSONResponse(
                status_code=400,
                content={'error': 'Missing required parameter: q'}
            )

        logger.info(f"🔍 Search: {query}")

        # Run search
        searcher = Search(VAULT_PATH)
        result = searcher.search(query)

        if result.get('success'):
            logger.info(f"✅ Search complete: {result.get('total_results', 0)} contexts found")
            return JSONResponse(content={
                'success': True,
                'query': result['query'],
                'contexts': result['contexts'],
                'total_results': result['total_results']
            })
        else:
            logger.error(f"❌ Search failed: {result.get('error', 'Unknown error')}")
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'error': result.get('error', 'Search failed'),
                    'query': query
                }
            )

    except Exception as e:
        logger.exception("Error handling search")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


@app.post("/protocol/ask")
async def handle_ask(request: Request):
    """
    Handle conversational queries with answer synthesis.

    Like /protocol/search but returns a synthesized natural language answer
    instead of just raw contexts. Supports multi-turn conversations.

    Expected format:
        localbrain://ask?q=What was my Meta offer?

    Query parameters:
        - q (required): Natural language query
        - clear_history (optional): Clear conversation history before processing

    Response:
        {
            "success": true,
            "query": "...",
            "answer": "Natural language answer",
            "contexts": [...],
            "total_results": N,
            "conversation_length": N
        }
    """
    global conversation_history

    try:
        # Parse request body
        body = await request.json()
        query = body.get('q', body.get('query', ''))
        clear_history = body.get('clear_history', False)

        if not query:
            return JSONResponse(
                status_code=400,
                content={'error': 'Missing required parameter: q'}
            )

        # Clear history if requested
        if clear_history:
            conversation_history = []
            logger.info("🗑️  Conversation history cleared")

        logger.info(f"🧠 Ask: {query}")

        # 1. Run agentic search to get contexts
        searcher = Search(VAULT_PATH)
        search_result = searcher.search(query)

        if not search_result.get('success'):
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'error': search_result.get('error', 'Search failed'),
                    'query': query
                }
            )

        contexts = search_result.get('contexts', [])
        logger.info(f"📚 Found {len(contexts)} contexts")

        # 2. Synthesize conversational answer
        synthesizer = AnswerSynthesizer()
        answer = synthesizer.synthesize(
            query=query,
            contexts=contexts,
            conversation_history=conversation_history
        )
        logger.info("✅ Answer synthesis complete")

        # 3. Update conversation history
        conversation_history.append({"role": "user", "content": query})
        conversation_history.append({"role": "assistant", "content": answer})

        # Trim to last 25 messages
        if len(conversation_history) > MAX_CONVERSATION_HISTORY:
            conversation_history = conversation_history[-MAX_CONVERSATION_HISTORY:]

        # 4. Return response
        return JSONResponse(content={
            'success': True,
            'query': query,
            'answer': answer,
            'contexts': contexts,
            'total_results': len(contexts),
            'conversation_length': len(conversation_history)
        })

    except Exception as e:
        logger.exception("Error handling ask request")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


def _should_respond_to_message(
    question: str,
    contexts: list,
    slack_context: dict,
    triggered_topics: list = None
) -> tuple[bool, str]:
    """
    Determine if the user would be interested in responding to this message.

    Args:
        question: The question asked
        contexts: Retrieved contexts from knowledge base
        slack_context: Slack context (channel, server, asker)
        triggered_topics: Topics that hit the mention threshold (3+ mentions)

    Returns:
        (should_respond: bool, reason: str)
    """
    # Always respond to DMs (channel_name starts with 'D')
    channel = slack_context.get('channel_name', '')
    if channel.startswith('D'):
        return True, "dm_always_respond"

    # If topic was mentioned 3+ times, definitely respond
    if triggered_topics and len(triggered_topics) > 0:
        topics_str = ",".join(triggered_topics)
        return True, f"trending_topic:{topics_str}"

    # If we found relevant contexts with good scores, user likely has knowledge about this
    if contexts and len(contexts) > 0:
        # Check if any context has a good relevance score
        top_score = max(ctx.get('score', 0) for ctx in contexts)
        if top_score > 0.7:  # High relevance threshold
            return True, f"high_relevance:{top_score:.2f}"
        elif top_score > 0.5:  # Medium relevance
            return True, f"medium_relevance:{top_score:.2f}"

    # If no good contexts found, user probably doesn't have relevant info
    return False, "no_relevant_knowledge"


@app.post("/protocol/slack/answer")
async def handle_slack_answer(request: Request):
    """
    Handle Slack bot queries with user impersonation.

    Like /protocol/ask but specialized for Slack bot use case where the bot
    poses as the user. Adapts tone based on Slack context and protects reputation.

    Expected format:
        POST /protocol/slack/answer
        {
            "question": "What was your Meta offer?",
            "slack_context": {
                "server_name": "ACME Corp Workspace",
                "channel_name": "engineering",
                "asker_name": "John Doe",
                "thread_id": "optional_thread_id"
            },
            "clear_history": false  // optional
        }

    Response:
        {
            "success": true,
            "should_respond": true,
            "reason": "high_relevance:0.85",
            "question": "...",
            "answer": "Natural language answer (no citations)",
            "conversation_length": N
        }
    """
    global conversation_history

    try:
        # Parse request body
        body = await request.json()
        question = body.get('question', '')
        slack_context = body.get('slack_context', {})
        channel_history = body.get('channel_history', [])
        triggered_topics = body.get('triggered_topics', [])
        clear_history = body.get('clear_history', False)

        if not question:
            return JSONResponse(
                status_code=400,
                content={'error': 'Missing required parameter: question'}
            )

        if not slack_context:
            return JSONResponse(
                status_code=400,
                content={'error': 'Missing required parameter: slack_context'}
            )

        # Clear history if requested
        if clear_history:
            conversation_history = []
            logger.info("🗑️  Conversation history cleared")

        logger.info(f"💬 Slack question from {slack_context.get('asker_name', 'Unknown')}: {question}")

        # 1. Run agentic search to get contexts
        searcher = Search(VAULT_PATH)
        search_result = searcher.search(question)

        if not search_result.get('success'):
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'error': search_result.get('error', 'Search failed'),
                    'question': question
                }
            )

        contexts = search_result.get('contexts', [])
        logger.info(f"📚 Found {len(contexts)} contexts")

        # 2. Determine if user would be interested in responding to this
        should_respond, reason = _should_respond_to_message(
            question,
            contexts,
            slack_context,
            triggered_topics=triggered_topics
        )

        if not should_respond:
            logger.info(f"⏭️  Skipping response: {reason}")
            return JSONResponse(content={
                'success': True,
                'should_respond': False,
                'reason': reason,
                'question': question,
                'answer': ''
            })

        # 3. Synthesize Slack-appropriate answer (poses as user)
        # Use channel history if available, otherwise use conversation_history
        history_for_context = channel_history if channel_history else conversation_history

        synthesizer = SlackAnswerSynthesizer()
        answer = synthesizer.synthesize(
            question=question,
            contexts=contexts,
            slack_context=slack_context,
            conversation_history=history_for_context
        )
        logger.info("✅ Slack answer synthesis complete")

        # 4. Update conversation history
        conversation_history.append({"role": "user", "content": question})
        conversation_history.append({"role": "assistant", "content": answer})

        # Trim to last 25 messages
        if len(conversation_history) > MAX_CONVERSATION_HISTORY:
            conversation_history = conversation_history[-MAX_CONVERSATION_HISTORY:]

        # 5. Return response
        return JSONResponse(content={
            'success': True,
            'should_respond': True,
            'reason': 'user_interested',
            'question': question,
            'answer': answer,
            'conversation_length': len(conversation_history)
        })

    except Exception as e:
        logger.exception("Error handling Slack answer request")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


@app.post("/protocol/slack/webhook")
async def handle_slack_webhook(request: Request):
    """
    Handle Slack Events API webhook.

    This endpoint receives events from Slack when the bot is mentioned or messaged.
    Automatically handles challenge verification and responds to questions.

    Expected Slack Event Format:
        {
            "type": "url_verification",  // Initial challenge
            "challenge": "..."
        }

        OR

        {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "text": "<@BOT_ID> what was my Meta offer?",
                "user": "U123456",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "thread_ts": "1234567890.123456"  // optional
            },
            "team_id": "T123456",
            ...
        }

    Note: For production use, you should verify the Slack request signature
    using the signing secret. This basic implementation is for development.
    """
    try:
        body = await request.json()

        # Handle URL verification challenge (initial Slack setup)
        if body.get('type') == 'url_verification':
            challenge = body.get('challenge', '')
            logger.info("✅ Slack webhook challenge received")
            return JSONResponse(content={'challenge': challenge})

        # Handle event callbacks
        if body.get('type') == 'event_callback':
            event = body.get('event', {})
            event_type = event.get('type')

            # Only handle app_mention and direct messages
            if event_type not in ['app_mention', 'message']:
                logger.debug(f"Ignoring Slack event type: {event_type}")
                return JSONResponse(content={'ok': True})

            # Extract event data
            text = event.get('text', '')
            user_id = event.get('user')
            channel_id = event.get('channel')
            thread_ts = event.get('thread_ts') or event.get('ts')

            # Remove bot mention from text (e.g., "<@U123456> question" -> "question")
            # This regex removes <@USERID> patterns
            import re
            question = re.sub(r'<@[A-Z0-9]+>', '', text).strip()

            if not question:
                logger.warning("Slack event received but no question found")
                return JSONResponse(content={'ok': True})

            # Get team/workspace info (you may want to fetch this via Slack API)
            team_id = body.get('team_id', 'Unknown workspace')

            # Build Slack context
            slack_context = {
                'server_name': team_id,  # In production, fetch workspace name via Slack API
                'channel_name': channel_id,  # In production, fetch channel name via Slack API
                'asker_name': user_id,  # In production, fetch user name via Slack API
                'thread_id': thread_ts
            }

            logger.info(f"🔔 Slack webhook: Question from {user_id} in {channel_id}: {question}")

            # Process the question using our answer endpoint logic
            searcher = Search(VAULT_PATH)
            search_result = searcher.search(question)

            if not search_result.get('success'):
                error_msg = "Sorry, I'm having trouble searching my notes right now."
                # TODO: In production, post this response back to Slack via chat.postMessage API
                logger.error(f"Search failed for Slack webhook: {search_result.get('error')}")
                return JSONResponse(content={
                    'ok': True,
                    'response': error_msg,
                    'note': 'Post this response to Slack via chat.postMessage API'
                })

            contexts = search_result.get('contexts', [])

            # Synthesize answer
            synthesizer = SlackAnswerSynthesizer()
            answer = synthesizer.synthesize(
                question=question,
                contexts=contexts,
                slack_context=slack_context,
                conversation_history=conversation_history
            )

            # Update conversation history
            conversation_history.append({"role": "user", "content": question})
            conversation_history.append({"role": "assistant", "content": answer})

            if len(conversation_history) > MAX_CONVERSATION_HISTORY:
                conversation_history = conversation_history[-MAX_CONVERSATION_HISTORY:]

            logger.info(f"✅ Slack webhook answer generated: {answer[:100]}...")

            # Return response
            # Note: For actual Slack integration, you should POST the answer back to Slack
            # using the Slack Web API (chat.postMessage) with the channel_id and thread_ts
            return JSONResponse(content={
                'ok': True,
                'answer': answer,
                'channel': channel_id,
                'thread_ts': thread_ts,
                'note': 'Use Slack Web API to post this answer back to the channel/thread'
            })

        # Unknown event type
        logger.warning(f"Unknown Slack webhook type: {body.get('type')}")
        return JSONResponse(content={'ok': True})

    except Exception as e:
        logger.exception("Error handling Slack webhook")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


@app.get("/file/{filepath:path}")
async def get_file(filepath: str):
    """
    Fetch full file content from vault.
    
    Allows AI apps to dive deeper after getting context chunks from search.
    
    Example:
        GET /file/career/Job%20Search.md
    """
    try:
        file_path = VAULT_PATH / filepath
        
        # Security: ensure file is within vault
        if not file_path.is_relative_to(VAULT_PATH):
            return JSONResponse(
                status_code=403,
                content={'error': 'Access denied: file outside vault'}
            )
        
        if not file_path.exists():
            return JSONResponse(
                status_code=404,
                content={'error': f'File not found: {filepath}'}
            )
        
        # Read file content
        content = read_file(file_path)
        
        # Read citations if available
        json_path = file_path.with_suffix('.json')
        citations = {}
        if json_path.exists():
            import json
            try:
                citations = json.loads(read_file(json_path))
            except:
                pass
        
        # Get file metadata
        stat = file_path.stat()
        
        return JSONResponse(content={
            'path': filepath,
            'content': content,
            'citations': citations,
            'size': stat.st_size,
            'last_modified': stat.st_mtime
        })
        
    except Exception as e:
        logger.exception("Error fetching file")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


@app.get("/list/{path:path}")
@app.get("/list")
async def list_files(path: str = ""):
    """
    List files and directories in vault.
    
    Allows AI apps to discover available files and browse structure.
    
    Examples:
        GET /list              # Root directory
        GET /list/career       # career/ folder
        GET /list/career/offers  # nested folder
    """
    try:
        # Build full path
        if path:
            full_path = VAULT_PATH / path
        else:
            full_path = VAULT_PATH
        
        # Security: ensure path is within vault
        if not full_path.is_relative_to(VAULT_PATH):
            return JSONResponse(
                status_code=403,
                content={'error': 'Access denied: path outside vault'}
            )
        
        if not full_path.exists():
            return JSONResponse(
                status_code=404,
                content={'error': f'Path not found: {path}'}
            )
        
        if not full_path.is_dir():
            return JSONResponse(
                status_code=400,
                content={'error': f'Path is not a directory: {path}'}
            )
        
        # List directory contents
        items = []
        for item in sorted(full_path.iterdir()):
            # Skip hidden files and system files
            if item.name.startswith('.'):
                continue
            
            stat = item.stat()
            
            if item.is_file():
                # Only include markdown and json files
                if item.suffix not in ['.md', '.json']:
                    continue
                
                items.append({
                    'name': item.name,
                    'type': 'file',
                    'size': stat.st_size,
                    'last_modified': stat.st_mtime
                })
            elif item.is_dir():
                # Count items in directory
                try:
                    item_count = len([f for f in item.iterdir() if not f.name.startswith('.')])
                except:
                    item_count = 0
                
                items.append({
                    'name': item.name,
                    'type': 'directory',
                    'item_count': item_count,
                    'last_modified': stat.st_mtime
                })
        
        return JSONResponse(content={
            'path': path if path else '/',
            'items': items,
            'total': len(items)
        })
        
    except Exception as e:
        logger.exception("Error listing files")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


@app.get("/protocol/parse")
async def parse_protocol_url(url: str):
    """
    Parse a localbrain:// URL and return structured data.
    
    Example:
        /protocol/parse?url=localbrain://ingest?text=hello&platform=Gmail
    """
    try:
        parsed = urlparse(url)
        
        if parsed.scheme != 'localbrain':
            return JSONResponse(
                status_code=400,
                content={'error': 'Invalid protocol scheme (expected localbrain://)'}
            )
        
        command = parsed.netloc
        params = parse_qs(parsed.query)
        
        # Decode parameters
        decoded_params = {
            k: unquote(v[0]) if v else None
            for k, v in params.items()
        }
        
        return {
            'command': command,
            'parameters': decoded_params
        }
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )


# All connector routes now handled by plugin system above
# No more hardcoded connector endpoints!


def main():
    """Start the daemon service."""
    logger.info("="*60)
    logger.info("LocalBrain Background Daemon Starting...")
    logger.info("="*60)
    logger.info(f"Vault: {VAULT_PATH}")
    logger.info(f"Port: {PORT}")
    logger.info(f"Protocol: localbrain://")
    logger.info("")
    logger.info("Available endpoints:")
    logger.info("  POST /protocol/ingest       - Ingest content")
    logger.info("  POST /protocol/search       - Natural language search (raw contexts)")
    logger.info("  POST /protocol/ask          - Conversational search (synthesized answers)")
    logger.info("  POST /protocol/slack/answer - Slack bot query (user impersonation)")
    logger.info("  POST /protocol/slack/webhook - Slack Events API webhook")
    logger.info("  GET  /file/<path>           - Get file contents")
    logger.info("  GET  /list/<path>           - List directory")
    logger.info("")
    logger.info("Gmail Connector:")
    logger.info("  POST /connectors/gmail/auth/start    - Start OAuth")
    logger.info("  GET  /connectors/gmail/auth/callback - OAuth callback")
    logger.info("  POST /connectors/gmail/auth/revoke   - Disconnect Gmail")
    logger.info("  GET  /connectors/gmail/status        - Connection status")
    logger.info("  POST /connectors/gmail/sync          - Sync & ingest emails")
    logger.info("  GET  /connectors/gmail/emails/recent - Fetch recent emails")
    logger.info("")
    logger.info("Google Calendar Connector:")
    logger.info("  POST /connectors/calendar/auth/start      - Start OAuth")
    logger.info("  GET  /connectors/calendar/auth/callback   - OAuth callback")
    logger.info("  POST /connectors/calendar/auth/revoke     - Disconnect Calendar")
    logger.info("  GET  /connectors/calendar/status          - Connection status")
    logger.info("  POST /connectors/calendar/sync            - Sync & ingest events")
    logger.info("  GET  /connectors/calendar/events/upcoming - Fetch upcoming events")
    logger.info("")
    logger.info("")
    logger.info("Service running. Press Ctrl+C to stop.")
    logger.info("="*60)
    
    # Start FastAPI server
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
