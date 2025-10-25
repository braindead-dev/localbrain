#!/usr/bin/env python3
"""
Simple Ingestion Test Script

Tests basic ingestion without LLM - uses hardcoded keyword matching
to determine file placement.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple


def load_vault_config(vault_path: Path) -> dict:
    """Load vault configuration from app.json."""
    config_path = vault_path / ".localbrain" / "app.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Vault not initialized. Run: python init_vault.py {vault_path}"
        )
    
    with open(config_path) as f:
        return json.load(f)


def determine_file(context: str) -> Tuple[str, str]:
    """
    Determine which folder and file to use based on context.
    Simple keyword matching (no LLM).
    
    Returns: (folder_name, filename)
    """
    context_lower = context.lower()
    
    # Job/career related
    if any(word in context_lower for word in [
        'applied', 'internship', 'job', 'interview', 'resume', 
        'career', 'work', 'company', 'offer', 'recruiter'
    ]):
        return ('career', 'job-search.md')
    
    # Project related
    elif any(word in context_lower for word in [
        'built', 'project', 'launched', 'developing', 'created',
        'app', 'website', 'code', 'github'
    ]):
        return ('projects', 'current-projects.md')
    
    # Learning/research related
    elif any(word in context_lower for word in [
        'learned', 'studying', 'course', 'tutorial', 'research',
        'paper', 'reading', 'book'
    ]):
        return ('learning', 'notes.md')
    
    # Finance related
    elif any(word in context_lower for word in [
        'money', 'paid', 'bought', 'investment', 'budget',
        'price', 'cost', 'financial', 'bank'
    ]):
        return ('finance', 'transactions.md')
    
    # Health related
    elif any(word in context_lower for word in [
        'workout', 'exercise', 'health', 'fitness', 'gym',
        'ran', 'weight', 'doctor', 'medical'
    ]):
        return ('health', 'tracking.md')
    
    # Social related
    elif any(word in context_lower for word in [
        'met', 'talked', 'conversation', 'friend', 'meeting',
        'party', 'event', 'networking'
    ]):
        return ('social', 'interactions.md')
    
    # Default: personal notes
    else:
        return ('personal', 'notes.md')


def create_or_append_file(vault_path: Path, folder: str, filename: str, context: str) -> None:
    """Create a new file or append to existing file."""
    file_path = vault_path / folder / filename
    
    # Get current timestamp
    timestamp = datetime.utcnow().strftime("%B %d, %Y")
    
    # Check if file exists
    if file_path.exists():
        print(f"📝 Appending to existing file: {folder}/{filename}")
        
        # Read existing content
        with open(file_path, 'r') as f:
            existing_content = f.read()
        
        # Append new content before footnotes section
        if '\n---\n' in existing_content:
            # Insert before footnotes
            parts = existing_content.split('\n---\n', 1)
            new_content = f"{parts[0]}\n\n{context}[^{get_next_footnote_number(existing_content)}].\n\n---\n{parts[1]}"
        else:
            # Just append
            new_content = f"{existing_content}\n\n{context}[^1].\n\n---\n\n[^1]: Manual input, {timestamp}"
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        # Also append footnote
        with open(file_path, 'a') as f:
            footnote_num = get_next_footnote_number(existing_content)
            f.write(f"\n[^{footnote_num}]: Manual input, {timestamp}")
    
    else:
        print(f"✨ Creating new file: {folder}/{filename}")
        
        # Generate file title from filename
        title = filename.replace('.md', '').replace('-', ' ').title()
        
        # Create new file with template
        content = f"""# {filename.replace('.md', '')}

Tracking and organizing {folder}-related information.

## Content

{context}[^1].

---

[^1]: Manual input, {timestamp}
"""
        
        with open(file_path, 'w') as f:
            f.write(content)
    
    print(f"✅ Content saved to: {file_path}")


def get_next_footnote_number(content: str) -> int:
    """Get the next footnote number from existing content."""
    import re
    footnotes = re.findall(r'\[\^(\d+)\]:', content)
    if footnotes:
        return max(int(n) for n in footnotes) + 1
    return 1


def ingest_context(vault_path: str, context: str) -> None:
    """Ingest a piece of context into the vault."""
    vault_path = Path(vault_path).expanduser().resolve()
    
    print(f"\n📥 Processing context:")
    print(f'   "{context[:80]}{"..." if len(context) > 80 else ""}"')
    print()
    
    # Load config (validates vault is initialized)
    config = load_vault_config(vault_path)
    
    # Determine which file to use
    folder, filename = determine_file(context)
    print(f"📂 Determined location: {folder}/{filename}")
    
    # Create or append to file
    create_or_append_file(vault_path, folder, filename, context)
    
    print(f"\n✨ Ingestion complete!")


def main():
    if len(sys.argv) != 3:
        print("Usage: python test_ingestion.py <vault_path> <context>")
        print('Example: python test_ingestion.py ~/test-vault "I applied to NVIDIA"')
        sys.exit(1)
    
    vault_path = sys.argv[1]
    context = sys.argv[2]
    
    ingest_context(vault_path, context)


if __name__ == "__main__":
    main()
