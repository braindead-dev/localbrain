#!/usr/bin/env python3
"""
Vault Initialization Script

Creates the LocalBrain vault structure in a specified directory.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path)


DEFAULT_FOLDERS = [
    "personal",
    "career",
    "projects",
    "research",
    "social",
    "finance",
    "health",
    "learning",
    "archive"
]

FOLDER_DESCRIPTIONS = {
    "personal": "Personal information, preferences, and key details about yourself",
    "career": "Professional development, job search, work experience, and career planning",
    "projects": "Personal projects, side work, ideas, and ongoing initiatives",
    "research": "Learning materials, research notes, papers, and technical studies",
    "social": "Social interactions, relationships, networking, and conversations",
    "finance": "Financial decisions, budgets, investments, and money management",
    "health": "Health tracking, fitness goals, wellness practices, and medical information",
    "learning": "Courses, skill development, tutorials, and educational content",
    "archive": "Completed projects, outdated content, and historical information"
}


def init_vault(vault_path: str) -> None:
    """Initialize a LocalBrain vault at the specified path."""
    vault_path = Path(vault_path).expanduser().resolve()
    
    print(f"🚀 Initializing LocalBrain vault at: {vault_path}")
    
    # Create vault directory if it doesn't exist
    vault_path.mkdir(parents=True, exist_ok=True)
    print(f"✅ Vault directory ready: {vault_path}")
    
    # Create .localbrain directory
    localbrain_dir = vault_path / ".localbrain"
    localbrain_dir.mkdir(exist_ok=True)
    print(f"✅ Created .localbrain/ directory")
    
    # Create internal directories
    (localbrain_dir / "data").mkdir(exist_ok=True)
    (localbrain_dir / "logs").mkdir(exist_ok=True)
    print(f"✅ Created internal directories (data/, logs/)")
    
    # Create app.json configuration
    app_config = {
        "version": "0.1.0",
        "vault_path": str(vault_path),
        "created": datetime.utcnow().isoformat() + "Z",
        "settings": {
            "auto_embed": False,
            "default_folders": DEFAULT_FOLDERS,
            "embedding_model": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        }
    }
    
    config_path = localbrain_dir / "app.json"
    with open(config_path, "w") as f:
        json.dump(app_config, f, indent=2)
    print(f"✅ Created app.json with default configuration")
    
    # Create default category folders
    created_folders = []
    for folder in DEFAULT_FOLDERS:
        folder_path = vault_path / folder
        folder_path.mkdir(exist_ok=True)
        created_folders.append(folder)
        
        # Create about.md in each folder
        about_path = folder_path / "about.md"
        if not about_path.exists():
            about_content = f"""# {folder.title()}

{FOLDER_DESCRIPTIONS[folder]}

---

*This folder was created automatically. You can edit or delete this about.md file.*
"""
            with open(about_path, "w") as f:
                f.write(about_content)
    
    print(f"✅ Created {len(created_folders)} default folders:")
    for folder in created_folders:
        print(f"   - {folder}/")
    
    print(f"\n🎉 Vault initialization complete!")
    print(f"📂 Vault location: {vault_path}")
    print(f"📝 Ready to ingest content!")


def main():
    if len(sys.argv) != 2:
        print("Usage: python init_vault.py <vault_path>")
        print("Example: python init_vault.py ~/test-vault")
        sys.exit(1)
    
    vault_path = sys.argv[1]
    init_vault(vault_path)


if __name__ == "__main__":
    main()
