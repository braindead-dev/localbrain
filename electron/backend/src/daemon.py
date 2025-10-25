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
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime
from typing import Dict, Optional

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
from bulk_ingest import BulkIngestionPipeline
from utils.file_ops import read_file
from config import load_config, update_config, get_vault_path

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

# FastAPI app
app = FastAPI(title="LocalBrain Background Service")

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Load config
CONFIG = load_config()
VAULT_PATH = get_vault_path()
PORT = CONFIG.get('port', 8765)

# Background task for auto-syncing Gmail
async def auto_sync_gmail():
    """Background task that syncs Gmail every 10 minutes."""
    await asyncio.sleep(60)  # Wait 1 minute after startup before first sync
    
    while True:
        try:
            logger.info("🔄 Auto-sync: Checking Gmail...")
            from connectors.gmail.gmail_connector import GmailConnector
            
            connector = GmailConnector(vault_path=VAULT_PATH)
            
            if connector.is_authenticated():
                logger.info("🔄 Auto-sync: Syncing Gmail...")
                result = connector.sync(max_results=50, minutes=15)
                
                if result['success'] and result['emails']:
                    logger.info(f"🔄 Auto-sync: Found {len(result['emails'])} new emails, ingesting...")
                    pipeline = AgenticIngestionPipeline(VAULT_PATH)
                    
                    ingested = 0
                    for email_data in result['emails']:
                        try:
                            pipeline.ingest(
                                context=email_data['text'],
                                source_metadata=email_data['metadata']
                            )
                            ingested += 1
                        except Exception as e:
                            logger.error(f"Failed to ingest email: {e}")
                    
                    logger.info(f"✅ Auto-sync: Successfully ingested {ingested}/{len(result['emails'])} emails")
                else:
                    logger.info("🔄 Auto-sync: No new emails found")
            else:
                logger.debug("Auto-sync: Gmail not connected, skipping")
                
        except Exception as e:
            logger.error(f"Auto-sync error: {e}")
        
        # Wait 10 minutes before next sync
        await asyncio.sleep(600)  # 600 seconds = 10 minutes

@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    asyncio.create_task(auto_sync_gmail())
    logger.info("📅 Auto-sync task started (runs every 10 minutes)")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "localbrain-daemon"}


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
        - platform (optional): Source platform (e.g., "Gmail", "Discord")
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


# ============================================================================
# Gmail Connector Endpoints
# ============================================================================

@app.post("/connectors/gmail/auth/start")
async def gmail_auth_start():
    """Start Gmail OAuth flow."""
    try:
        from connectors.gmail.gmail_connector import GmailConnector
        connector = GmailConnector()
        auth_url = connector.start_auth_flow()
        return {"auth_url": auth_url, "success": True}
    except FileNotFoundError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.exception("Error starting Gmail auth")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/connectors/gmail/auth/callback")
async def gmail_auth_callback(request: Request):
    """Handle Gmail OAuth callback."""
    try:
        from connectors.gmail.gmail_connector import GmailConnector
        connector = GmailConnector()
        
        # Get full callback URL
        authorization_response = str(request.url)
        user_info = connector.handle_callback(authorization_response)
        
        # Return HTML success page
        email = user_info.get('email', 'Unknown')
        html_content = f"""
        <html>
            <head>
                <title>Gmail Connected</title>
                <style>
                    body {{ 
                        font-family: system-ui, -apple-system, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 3rem;
                        border-radius: 1rem;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        text-align: center;
                    }}
                    h1 {{ color: #10b981; margin: 0 0 1rem 0; }}
                    p {{ color: #6b7280; margin: 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✓ Gmail Connected Successfully!</h1>
                    <p>Connected as: <strong>{email}</strong></p>
                    <p style="margin-top: 1rem;">You can close this window now.</p>
                </div>
                <script>
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
        </html>
        """
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.exception("Error in Gmail callback")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/connectors/gmail/auth/revoke")
async def gmail_auth_revoke():
    """Revoke Gmail access."""
    try:
        from connectors.gmail.gmail_connector import GmailConnector
        connector = GmailConnector()
        connector.revoke_access()
        return {"success": True, "message": "Gmail disconnected"}
    except Exception as e:
        logger.exception("Error revoking Gmail")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/connectors/gmail/status")
async def gmail_status():
    """Get Gmail connection status."""
    try:
        from connectors.gmail.gmail_connector import GmailConnector
        connector = GmailConnector()
        status = connector.get_status()
        return status
    except Exception as e:
        logger.exception("Error getting Gmail status")
        return {"connected": False, "error": str(e)}


@app.post("/connectors/gmail/sync")
async def gmail_sync(max_results: int = 100, minutes: int = 10, ingest: bool = False):
    """Trigger Gmail sync from last N minutes."""
    try:
        from connectors.gmail.gmail_connector import GmailConnector
        
        connector = GmailConnector(vault_path=VAULT_PATH)
        
        if not connector.is_authenticated():
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated. Please connect Gmail first."}
            )
        
        result = connector.sync(max_results=max_results, minutes=minutes)
        
        # Ingest each email as a separate document
        if ingest and result['success'] and result['emails']:
            try:
                logger.info(f"Starting ingestion of {len(result['emails'])} emails...")
                pipeline = AgenticIngestionPipeline(VAULT_PATH)
                
                ingested_emails = []
                failed_emails = []
                
                for i, email_data in enumerate(result['emails'], 1):
                    try:
                        logger.info(f"Ingesting email {i}/{len(result['emails'])}...")
                        
                        # Ingest this email as a separate document
                        pipeline.ingest(
                            context=email_data['text'],
                            source_metadata=email_data['metadata']
                        )
                        
                        ingested_emails.append(email_data['metadata'].get('quote', f'Email {i}'))
                        logger.info(f"✓ Successfully ingested: {email_data['metadata'].get('quote', 'No subject')}")
                    except Exception as e:
                        failed_emails.append({
                            'subject': email_data['metadata'].get('quote', 'Unknown'),
                            'error': str(e)
                        })
                        logger.error(f"✗ Failed to ingest email {i}: {e}")
                        continue
                
                result['ingested_count'] = len(ingested_emails)
                result['failed_count'] = len(failed_emails)
                result['ingested_subjects'] = ingested_emails
                if failed_emails:
                    result['failed_emails'] = failed_emails
                    
                logger.info(f"✅ Ingestion complete: {len(ingested_emails)} succeeded, {len(failed_emails)} failed")
            except Exception as e:
                logger.exception("Error in ingestion pipeline")
                result['ingestion_error'] = str(e)
                result['ingested_count'] = 0
        else:
            result['ingested_count'] = 0
            result['ingestion_skipped'] = True
        
        # Simplify response - only return text content for display (not when ingesting)
        if not ingest:
            result['emails'] = [email['text'] for email in result['emails']]
        else:
            # When ingesting, show which emails were processed
            result['emails'] = [email['metadata'].get('quote', 'No subject') for email in result['emails']]
        
        return result
    except Exception as e:
        logger.exception("Error syncing Gmail")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/connectors/gmail/emails/recent")
async def gmail_recent_emails(days: int = 7, max_results: int = 50):
    """Fetch recent emails without syncing."""
    try:
        from connectors.gmail.gmail_connector import GmailConnector
        
        connector = GmailConnector()
        
        if not connector.is_authenticated():
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated. Please connect Gmail first."}
            )
        
        emails = connector.fetch_recent_emails(days=days, max_results=max_results)
        
        # Simplify response - only return text content
        email_texts = [email['text'] for email in emails]
        
        return {
            "success": True,
            "count": len(email_texts),
            "emails": email_texts
        }
    except Exception as e:
        logger.exception("Error fetching recent emails")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================================
# Discord Connector Endpoints
# ============================================================================

@app.post("/connectors/discord/auth/save-token")
async def discord_save_token(request: Request):
    """Save Discord bot token."""
    try:
        from connectors.discord.discord_connector import DiscordConnector
        
        data = await request.json()
        bot_token = data.get('token', '').strip()
        
        if not bot_token:
            return JSONResponse(
                status_code=400,    
                content={"error": "Bot token is required"}
            )
        
        connector = DiscordConnector()
        result = connector.save_token(bot_token)
        
        if result['success']:
            return {"success": True, "message": "Discord bot connected successfully"}
        else:
            return JSONResponse(
                status_code=400,
                content={"error": result.get('error', 'Failed to save token')}
            )
    except Exception as e:
        logger.exception("Error saving Discord token")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/connectors/discord/auth/revoke")
async def discord_auth_revoke():
    """Revoke Discord access."""
    try:
        from connectors.discord.discord_connector import DiscordConnector
        connector = DiscordConnector()
        connector.revoke_access()
        return {"success": True, "message": "Discord disconnected"}
    except Exception as e:
        logger.exception("Error revoking Discord")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/connectors/discord/status")
async def discord_status():
    """Get Discord connection status."""
    try:
        from connectors.discord.discord_connector import DiscordConnector
        connector = DiscordConnector()
        status = await connector.get_status()
        return status
    except Exception as e:
        logger.exception("Error getting Discord status")
        return {"connected": False, "error": str(e)}


@app.post("/connectors/discord/sync")
async def discord_sync(max_messages: int = 100, hours: int = 24, ingest: bool = False):
    """Trigger Discord DM sync from last N hours."""
    try:
        from connectors.discord.discord_connector import DiscordConnector
        
        connector = DiscordConnector(vault_path=VAULT_PATH)
        
        if not connector.is_authenticated():
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated. Please save bot token first."}
            )
        
        result = await connector.sync(max_messages=max_messages, hours=hours)
        
        # Ingest each message as a separate document
        if ingest and result['success'] and result['messages']:
            try:
                logger.info(f"Starting ingestion of {len(result['messages'])} Discord messages...")
                pipeline = AgenticIngestionPipeline(VAULT_PATH)
                
                ingested_messages = []
                failed_messages = []
                
                for i, msg_data in enumerate(result['messages'], 1):
                    try:
                        logger.info(f"Ingesting message {i}/{len(result['messages'])}...")
                        
                        # Ingest this message as a separate document
                        pipeline.ingest(
                            context=msg_data['text'],
                            source_metadata=msg_data['metadata']
                        )
                        
                        ingested_messages.append(msg_data['metadata'].get('quote', f'Message {i}'))
                        logger.info(f"✓ Successfully ingested: {msg_data['metadata'].get('quote', 'No content')}")
                    except Exception as e:
                        failed_messages.append({
                            'content': msg_data['metadata'].get('quote', 'Unknown'),
                            'error': str(e)
                        })
                        logger.error(f"✗ Failed to ingest message {i}: {e}")
                        continue
                
                result['ingested_count'] = len(ingested_messages)
                result['failed_count'] = len(failed_messages)
                result['ingested_messages'] = ingested_messages
                if failed_messages:
                    result['failed_messages'] = failed_messages
                    
                logger.info(f"✅ Ingestion complete: {len(ingested_messages)} succeeded, {len(failed_messages)} failed")
            except Exception as e:
                logger.exception("Error in ingestion pipeline")
                result['ingestion_error'] = str(e)
                result['ingested_count'] = 0
        else:
            result['ingested_count'] = 0
            result['ingestion_skipped'] = True
        
        # Simplify response - only return text content for display (not when ingesting)
        if not ingest:
            result['messages'] = [msg['text'] for msg in result['messages']]
        else:
            # When ingesting, show which messages were processed
            result['messages'] = [msg['metadata'].get('quote', 'No content') for msg in result['messages']]
        
        return result
    except Exception as e:
        logger.exception("Error syncing Discord")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/connectors/discord/dms/recent")
async def discord_recent_dms(hours: int = None, days: int = None, max_messages: int = 50):
    """
    Fetch recent DMs without syncing.
    
    Query params:
        hours: Fetch DMs from last N hours (takes priority over days)
        days: Fetch DMs from last N days (default: 7)
        max_messages: Max messages per DM channel (default: 50)
    """
    try:
        from connectors.discord.discord_connector import DiscordConnector
        
        connector = DiscordConnector()
        
        if not connector.is_authenticated():
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated. Please save bot token first."}
            )
        
        # Determine time window - hours takes priority
        if hours is not None:
            messages = await connector.fetch_recent_dms(days=0, max_messages=max_messages)
            # Filter by hours in connector
            from datetime import datetime, timedelta, timezone
            time_ago = datetime.now(timezone.utc) - timedelta(hours=hours)
            # Re-fetch with hours
            result = await connector.sync(max_messages=max_messages, hours=hours)
            messages = result.get('messages', [])
        else:
            # Use days (default 7)
            if days is None:
                days = 7
            messages = await connector.fetch_recent_dms(days=days, max_messages=max_messages)
        
        # Simplify response - only return text content
        message_texts = [msg['text'] for msg in messages]
        
        return {
            "success": True,
            "count": len(message_texts),
            "messages": message_texts,
            "time_window": f"{hours} hours" if hours else f"{days if days else 7} days"
        }
    except Exception as e:
        logger.exception("Error fetching recent DMs")
        return JSONResponse(status_code=500, content={"error": str(e)})


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
    logger.info("  POST /protocol/ingest - Ingest content")
    logger.info("  POST /protocol/search - Natural language search")
    logger.info("  GET  /file/<path>      - Get file contents")
    logger.info("  GET  /list/<path>      - List directory")
    logger.info("")
    logger.info("Gmail Connector:")
    logger.info("  POST /connectors/gmail/auth/start    - Start OAuth")
    logger.info("  GET  /connectors/gmail/auth/callback - OAuth callback")
    logger.info("  POST /connectors/gmail/auth/revoke   - Disconnect Gmail")
    logger.info("  GET  /connectors/gmail/status        - Connection status")
    logger.info("  POST /connectors/gmail/sync          - Sync & ingest emails")
    logger.info("  GET  /connectors/gmail/emails/recent - Fetch recent emails")
    logger.info("")
    logger.info("Discord Connector:")
    logger.info("  POST /connectors/discord/auth/save-token - Save bot token")
    logger.info("  POST /connectors/discord/auth/revoke     - Disconnect Discord")
    logger.info("  GET  /connectors/discord/status          - Connection status")
    logger.info("  POST /connectors/discord/sync            - Sync & ingest DMs")
    logger.info("  GET  /connectors/discord/dms/recent      - Fetch recent DMs")
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
