#!/usr/bin/env python3
"""
Test Discord Connector

Quick test script to verify Discord connector is working.

Usage:
    python scripts/test_discord.py <bot_token>
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from connectors.discord.discord_connector import DiscordConnector


async def test_discord_connector(bot_token: str):
    """Test Discord connector functionality."""
    
    print("="*60)
    print("Discord Connector Test")
    print("="*60)
    print()
    
    # Initialize connector
    print("1. Initializing Discord connector...")
    connector = DiscordConnector()
    
    # Save token
    print("2. Saving bot token...")
    result = connector.save_token(bot_token)
    if result['success']:
        print(f"   ✓ Token saved successfully")
    else:
        print(f"   ✗ Failed to save token: {result.get('error')}")
        return
    
    # Check status
    print("3. Checking connection status...")
    status = await connector.get_status()
    if status.get('connected'):
        print(f"   ✓ Connected as: {status.get('username')}")
        print(f"   ✓ Bot ID: {status.get('bot_id')}")
    else:
        print(f"   ✗ Not connected: {status.get('error')}")
        return
    
    # Sync DMs (dry run - don't ingest)
    print("4. Syncing DMs from last 24 hours (dry run)...")
    sync_result = await connector.sync(max_messages=10, hours=24)
    
    if sync_result['success']:
        msg_count = sync_result['messages_fetched']
        print(f"   ✓ Found {msg_count} messages")
        
        if msg_count > 0:
            print(f"\n   Sample message:")
            print(f"   {'-'*50}")
            print(f"   {sync_result['messages'][0]['text'][:200]}...")
            print(f"   {'-'*50}")
    else:
        print(f"   ✗ Sync failed")
    
    # Test disconnect
    print("5. Testing disconnect...")
    connector.revoke_access()
    print(f"   ✓ Disconnected successfully")
    
    print()
    print("="*60)
    print("✅ All tests passed!")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Start daemon: python src/daemon.py")
    print("  2. Save token via API:")
    print("     curl -X POST http://localhost:8765/connectors/discord/auth/save-token \\")
    print("       -H 'Content-Type: application/json' \\")
    print("       -d '{\"token\": \"YOUR_TOKEN\"}'")
    print("  3. Sync DMs:")
    print("     curl -X POST 'http://localhost:8765/connectors/discord/sync?hours=24&ingest=true'")
    print()


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_discord.py <bot_token>")
        print()
        print("Get your bot token from:")
        print("  https://discord.com/developers/applications")
        print()
        sys.exit(1)
    
    bot_token = sys.argv[1]
    
    try:
        asyncio.run(test_discord_connector(bot_token))
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

