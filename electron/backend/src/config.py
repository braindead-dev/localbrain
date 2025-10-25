"""
Configuration management for LocalBrain.

Stores config in ~/.localbrain/config.json
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


CONFIG_DIR = Path.home() / ".localbrain"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "vault_path": str(Path.home() / "Documents" / "GitHub" / "localbrain" / "my-vault"),
    "port": 8765,
    "auto_start": True,
}


def load_config() -> Dict[str, Any]:
    """
    Load configuration from file.
    
    Creates default config if file doesn't exist.
    
    Returns:
        Config dictionary
    """
    # Create config directory if it doesn't exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create default config if file doesn't exist
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    # Load existing config
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Merge with defaults (in case new keys were added)
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)
        
        return merged
    except Exception as e:
        print(f"Error loading config: {e}")
        print("Using default config")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to file.
    
    Args:
        config: Config dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update specific config values.
    
    Args:
        updates: Dictionary of values to update
        
    Returns:
        Updated config dictionary
    """
    config = load_config()
    config.update(updates)
    save_config(config)
    return config


def get_vault_path() -> Path:
    """
    Get vault path from config.
    
    Returns:
        Path object for vault
    """
    config = load_config()
    return Path(config['vault_path']).expanduser()


def set_vault_path(path: str) -> bool:
    """
    Set vault path in config.
    
    Args:
        path: New vault path (can use ~ for home)
        
    Returns:
        True if successful
    """
    # Validate path exists
    full_path = Path(path).expanduser()
    if not full_path.exists():
        raise ValueError(f"Path does not exist: {path}")
    
    if not full_path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
    
    # Update config
    config = load_config()
    config['vault_path'] = str(full_path)
    return save_config(config)
