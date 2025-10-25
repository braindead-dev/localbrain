"""
Discord Connector - Handles bot authentication and DM fetching.

This connector manages Discord Bot API access, fetches direct messages,
and converts them to plain text format for ingestion into LocalBrain.

Note: This connector only processes DMs, not server messages.
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import discord
except ImportError:
    raise ImportError(
        "discord.py-self is required for Discord connector. "
        "Install it with: pip install discord.py-self"
    )


class DiscordConnector:
    """
    Discord connector for authenticating and fetching DMs.
    
    Handles bot token management, DM retrieval, and text conversion.
    Only processes direct messages, not server/guild messages.
    """
    
    def __init__(self, credentials_dir: Optional[Path] = None, vault_path: Optional[Path] = None):
        """
        Initialize Discord connector.
        
        Args:
            credentials_dir: Directory to store bot credentials (default: ~/.localbrain/credentials)
            vault_path: Path to LocalBrain vault for ingestion
        """
        if credentials_dir is None:
            credentials_dir = Path.home() / '.localbrain' / 'credentials'
        
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.token_file = self.credentials_dir / 'discord_token.json'
        self.config_file = self.credentials_dir / 'discord_config.json'
        
        # Vault path for ingestion
        self.vault_path = vault_path
        
        # Discord client (initialized on first use)
        self._client = None
        self._is_running = False
    
    # ========================================================================
    # Authentication Methods
    # ========================================================================
    
    def save_token(self, bot_token: str) -> Dict:
        """
        Save Discord bot token.
        
        Args:
            bot_token: Discord bot token
            
        Returns:
            Status dict with success/error
        """
        try:
            # Validate token format (Discord tokens have specific format)
            if not bot_token or len(bot_token) < 50:
                raise ValueError("Invalid Discord bot token format")
            
            # Save token
            token_data = {
                'token': bot_token,
                'saved_at': datetime.now().isoformat()
            }
            
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            # Initialize config
            config = self._load_config()
            config['connected_at'] = datetime.now().isoformat()
            self._save_config(config)
            
            return {
                'success': True,
                'message': 'Bot token saved successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def revoke_access(self) -> bool:
        """
        Delete local bot token.
        
        Returns:
            True if successful
        """
        # Delete local files
        if self.token_file.exists():
            self.token_file.unlink()
        
        # Reset config
        config = self._load_config()
        config['connected_at'] = None
        config['username'] = None
        self._save_config(config)
        
        # Stop client if running
        if self._client and self._is_running:
            asyncio.create_task(self._client.close())
            self._client = None
            self._is_running = False
        
        return True
    
    def is_authenticated(self) -> bool:
        """Check if bot token is available."""
        return self.token_file.exists()
    
    def get_token(self) -> Optional[str]:
        """
        Get stored user token.
        
        Priority:
        1. Environment variable (DISCORD_TOKEN or DISCORD_RESET_TOKEN)
        2. Token file
        
        Returns:
            User token string or None
        """
        # Try environment variables first
        token = os.getenv('DISCORD_TOKEN') or os.getenv('DISCORD_RESET_TOKEN')
        if token:
            return token
        
        # Fall back to token file
        if not self.token_file.exists():
            return None
        
        try:
            with open(self.token_file, 'r') as f:
                data = json.load(f)
                return data.get('token')
        except Exception as e:
            print(f"Error loading token: {e}")
            return None
    
    # ========================================================================
    # DM Fetching Methods
    # ========================================================================
    
    async def sync(self, max_messages: int = 100, hours: int = 24) -> Dict:
        """
        Sync DMs from the last N hours.
        
        Args:
            max_messages: Maximum number of messages per DM channel (default: 100)
            hours: Fetch messages from last N hours (default: 24)
            
        Returns:
            Dict with sync statistics
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please save bot token first.")
        
        # Calculate timestamp for N hours ago
        time_ago = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Fetch DMs
        dms = await self._fetch_dms(time_ago, max_messages)
        
        # Update config with sync stats
        config = self._load_config()
        config['last_sync'] = datetime.now().isoformat()
        config['message_count'] = len(dms)
        config['total_messages_processed'] = config.get('total_messages_processed', 0) + len(dms)
        self._save_config(config)
        
        return {
            'success': True,
            'messages_fetched': len(dms),
            'time_window_hours': hours,
            'query_time': time_ago.isoformat(),
            'messages': dms
        }
    
    async def fetch_recent_dms(self, days: int = 7, max_messages: int = 50) -> List[Dict]:
        """
        Fetch recent DMs from last N days.
        
        Args:
            days: Number of days to look back
            max_messages: Maximum messages per DM channel
            
        Returns:
            List of message dicts with content and metadata
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please save bot token first.")
        
        # Calculate timestamp
        time_ago = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Fetch DMs
        return await self._fetch_dms(time_ago, max_messages)
    
    async def get_status(self) -> Dict:
        """
        Get Discord connector status.
        
        Returns:
            Status dict with connection info and stats
        """
        if not self.is_authenticated():
            return {'connected': False}
        
        try:
            # Get bot info
            client = await self._get_client()
            
            # Load config
            config = self._load_config()
            
            return {
                'connected': True,
                'username': client.user.name if client.user else 'Unknown',
                'bot_id': str(client.user.id) if client.user else None,
                'lastSync': config.get('last_sync'),
                'messageCount': config.get('message_count', 0),
                'totalProcessed': config.get('total_messages_processed', 0),
                'connectedAt': config.get('connected_at')
            }
        except Exception as e:
            print(f"Error getting status: {e}")
            return {'connected': False, 'error': str(e)}
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _get_client(self) -> discord.Client:
        """Get or create Discord client (user account)."""
        if self._client is None or not self._is_running:
            token = self.get_token()
            if token is None:
                raise Exception("No user token available")
            
            # Create self-bot client (user account, not bot account)
            # This allows reading personal DMs
            self._client = discord.Client()
            
            # Start client in background
            async def start_client():
                try:
                    await self._client.start(token, bot=False)  # bot=False for user accounts
                except Exception as e:
                    print(f"Error starting Discord client: {e}")
            
            # Start client but don't block
            asyncio.create_task(start_client())
            
            # Wait for client to be ready
            await self._client.wait_until_ready()
            self._is_running = True
            
            # Save username to config
            if self._client.user:
                config = self._load_config()
                config['username'] = self._client.user.name
                config['user_id'] = str(self._client.user.id)
                self._save_config(config)
        
        return self._client
    
    async def _fetch_dms(self, after: datetime, max_messages: int) -> List[Dict]:
        """
        Fetch DMs after a certain time.
        
        Args:
            after: Only fetch messages after this time
            max_messages: Max messages per DM channel
            
        Returns:
            List of processed message dicts
        """
        processed_messages = []
        
        try:
            client = await self._get_client()
            
            print(f"Scanning DM channels... (found {len(client.private_channels)} cached)")
            
            # Iterate through all private channels (DMs and Group DMs)
            for channel in client.private_channels:
                if isinstance(channel, discord.DMChannel):
                    try:
                        recipient = channel.recipient
                        print(f"Fetching DMs with {recipient.name}...")
                        
                        # Fetch messages from this DM channel
                        async for message in channel.history(
                            limit=max_messages,
                            after=after,
                            oldest_first=False
                        ):
                            # Process message
                            msg_data = await self._message_to_structured_data(message)
                            if msg_data:
                                processed_messages.append(msg_data)
                        
                        print(f"  ✓ Fetched messages from {recipient.name}")
                    except discord.Forbidden:
                        print(f"  ✗ No access to DM channel with {channel.recipient}")
                        continue
                    except Exception as e:
                        print(f"  ✗ Error fetching messages from DM: {e}")
                        continue
                
                elif isinstance(channel, discord.GroupChannel):
                    # Group DMs
                    try:
                        print(f"Fetching Group DM: {channel.name or 'Unnamed Group'}...")
                        
                        async for message in channel.history(
                            limit=max_messages,
                            after=after,
                            oldest_first=False
                        ):
                            msg_data = await self._message_to_structured_data(message)
                            if msg_data:
                                processed_messages.append(msg_data)
                        
                        print(f"  ✓ Fetched messages from group")
                    except Exception as e:
                        print(f"  ✗ Error fetching group messages: {e}")
                        continue
            
            print(f"Total messages fetched: {len(processed_messages)}")
        
        except Exception as e:
            print(f"Error fetching DMs: {e}")
        
        return processed_messages
    
    async def _message_to_structured_data(self, message: discord.Message) -> Optional[Dict]:
        """
        Convert Discord message to simple text format for ingestion.
        
        Args:
            message: Discord message object
            
        Returns:
            Dict with simple text content and minimal metadata
        """
        try:
            # Skip bot messages (optional, can be configured)
            # if message.author.bot:
            #     return None
            
            # Skip empty messages
            if not message.content and not message.attachments:
                return None
            
            # Extract message details
            author_name = f"{message.author.name}#{message.author.discriminator}" if message.author.discriminator != "0" else message.author.name
            timestamp = message.created_at.isoformat()
            content = message.content or ""
            
            # Get DM partner (the other person in the conversation)
            dm_partner = "Unknown"
            if isinstance(message.channel, discord.DMChannel):
                # For user accounts, check who sent it
                if message.author.id == self._client.user.id:
                    # You sent this message
                    dm_partner = f"{message.channel.recipient.name}"
                else:
                    # They sent this message
                    dm_partner = f"{message.author.name}"
            elif isinstance(message.channel, discord.GroupChannel):
                # Group DM
                dm_partner = message.channel.name or "Group DM"
            
            # Handle attachments
            attachments_text = ""
            if message.attachments:
                attachments_text = "\n\nAttachments:\n"
                for att in message.attachments:
                    attachments_text += f"- {att.filename} ({att.url})\n"
            
            # Handle embeds
            embeds_text = ""
            if message.embeds:
                embeds_text = "\n\nEmbeds:\n"
                for embed in message.embeds:
                    if embed.title:
                        embeds_text += f"Title: {embed.title}\n"
                    if embed.description:
                        embeds_text += f"Description: {embed.description}\n"
                    if embed.url:
                        embeds_text += f"URL: {embed.url}\n"
            
            # Format as simple text
            text_content = f"""Discord DM
From: {author_name}
To: {dm_partner}
Date: {timestamp}

{content}{attachments_text}{embeds_text}

---
Message ID: {message.id}
Channel ID: {message.channel.id}
"""
            
            # Return simple format for ingestion
            return {
                'text': text_content,
                'metadata': {
                    'platform': 'Discord',
                    'timestamp': timestamp,
                    'quote': content[:100] if content else f"Message from {author_name}",
                    'source': f"Discord/{message.id}",
                    'type': 'dm',
                    'from': author_name,
                    'to': dm_partner,
                    'message_id': str(message.id),
                    'channel_id': str(message.channel.id)
                }
            }
        
        except Exception as e:
            print(f"Error processing message {message.id}: {e}")
            return None
    
    # ========================================================================
    # Config/State Management
    # ========================================================================
    
    def _load_config(self) -> Dict:
        """Load connector configuration."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_config(self, config: Dict):
        """Save connector configuration."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)


# ============================================================================
# Sync Function for Background Tasks
# ============================================================================

async def sync_discord_dms(vault_path: Path, max_messages: int = 100, hours: int = 24) -> Dict:
    """
    Helper function to sync Discord DMs and ingest them.
    
    Args:
        vault_path: Path to LocalBrain vault
        max_messages: Max messages per DM channel
        hours: Fetch messages from last N hours
        
    Returns:
        Dict with sync results
    """
    connector = DiscordConnector(vault_path=vault_path)
    
    if not connector.is_authenticated():
        return {
            'success': False,
            'error': 'Discord not authenticated'
        }
    
    result = await connector.sync(max_messages=max_messages, hours=hours)
    return result

