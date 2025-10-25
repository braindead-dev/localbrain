#!/usr/bin/env python3
"""
LocalBrain Protocol Handler

Handles localbrain:// URLs triggered by the system and forwards them to the daemon.

Usage:
    python src/protocol_handler.py "localbrain://ingest?text=hello&platform=Gmail"
"""

import sys
import requests
import json
import logging
from urllib.parse import urlparse, parse_qs, unquote

# Configuration
DAEMON_URL = "http://127.0.0.1:8765"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/localbrain-protocol.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('protocol-handler')


def parse_localbrain_url(url: str) -> dict:
    """Parse a localbrain:// URL into structured data."""
    try:
        parsed = urlparse(url)
        
        if parsed.scheme != 'localbrain':
            raise ValueError(f"Invalid protocol scheme: {parsed.scheme} (expected localbrain)")
        
        command = parsed.netloc or parsed.path.split('/')[0]
        params = parse_qs(parsed.query)
        
        # Decode and flatten parameters
        decoded_params = {}
        for k, v in params.items():
            if v:
                decoded_params[k] = unquote(v[0])
        
        return {
            'command': command,
            'parameters': decoded_params
        }
    
    except Exception as e:
        logger.error(f"Failed to parse URL: {e}")
        raise


def handle_ingest(params: dict) -> dict:
    """Handle ingest command."""
    text = params.get('text', '')
    platform = params.get('platform', 'Manual')
    timestamp = params.get('timestamp')
    url = params.get('url')
    
    if not text:
        raise ValueError("Missing required parameter: text")
    
    # Build request payload
    payload = {
        'text': text,
        'platform': platform,
    }
    
    if timestamp:
        payload['timestamp'] = timestamp
    if url:
        payload['url'] = url
    
    # Send to daemon
    logger.info(f"Forwarding ingest request to daemon")
    logger.info(f"Platform: {platform}")
    logger.info(f"Text preview: {text[:100]}...")
    
    response = requests.post(
        f"{DAEMON_URL}/protocol/ingest",
        json=payload,
        timeout=60  # Ingestion can take time
    )
    
    response.raise_for_status()
    return response.json()


def main():
    """Main entry point for protocol handler."""
    if len(sys.argv) < 2:
        print("Usage: protocol_handler.py <localbrain:// URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    logger.info("="*60)
    logger.info(f"Received protocol URL: {url}")
    logger.info("="*60)
    
    try:
        # Parse URL
        parsed = parse_localbrain_url(url)
        command = parsed['command']
        params = parsed['parameters']
        
        logger.info(f"Command: {command}")
        logger.info(f"Parameters: {json.dumps(params, indent=2)}")
        
        # Route to appropriate handler
        if command == 'ingest':
            result = handle_ingest(params)
            logger.info("Success!")
            logger.info(f"Result: {json.dumps(result, indent=2)}")
            print(json.dumps(result, indent=2))
            sys.exit(0)
        
        else:
            logger.error(f"Unknown command: {command}")
            print(f"Error: Unknown command '{command}'")
            print("Supported commands: ingest")
            sys.exit(1)
    
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to daemon. Is it running?")
        print("Error: LocalBrain daemon is not running")
        print("Start it with: python src/tray.py")
        sys.exit(1)
    
    except Exception as e:
        logger.exception("Error handling protocol URL")
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
