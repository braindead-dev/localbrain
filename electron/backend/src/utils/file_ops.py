#!/usr/bin/env python3
"""
File Operations - Helper functions for reading/writing vault files
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


def list_vault_files(vault_path: Path, include_about: bool = False) -> List[Dict[str, str]]:
    """
    List all markdown files in vault with metadata.
    
    Args:
        vault_path: Path to vault root
        include_about: Whether to include about.md files
        
    Returns:
        List of dicts with file info: {folder, filename, path, preview}
    """
    files = []
    
    # Get all folders except .localbrain
    for folder_path in vault_path.iterdir():
        if folder_path.name.startswith('.') or not folder_path.is_dir():
            continue
        
        # Find markdown files in folder
        for file_path in folder_path.glob("*.md"):
            # Skip about.md if not requested
            if not include_about and file_path.name.lower() == "about.md":
                continue
            
            # Read first few lines for preview
            try:
                with open(file_path, 'r') as f:
                    lines = [line.strip() for line in f.readlines()[:10] if line.strip()]
                    preview = '\n'.join(lines[:5])  # First 5 non-empty lines
            except:
                preview = ""
            
            files.append({
                "folder": folder_path.name,
                "filename": file_path.name,
                "path": str(file_path),
                "relative_path": f"{folder_path.name}/{file_path.name}",
                "preview": preview
            })
    
    return files


def read_file(file_path: Path) -> str:
    """Read file contents."""
    with open(file_path, 'r') as f:
        return f.read()


def write_file(file_path: Path, content: str) -> None:
    """Write content to file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(content)


def read_json_citations(file_path: Path) -> Dict:
    """
    Read JSON citation file (e.g., 'Job Search.json').
    
    Returns:
        Dict of citations, or empty dict if file doesn't exist
    """
    json_path = file_path.with_suffix('.json')
    if not json_path.exists():
        return {}
    
    with open(json_path, 'r') as f:
        return json.load(f)


def write_json_citations(file_path: Path, citations: Dict) -> None:
    """Write JSON citation file."""
    json_path = file_path.with_suffix('.json')
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_path, 'w') as f:
        json.dump(citations, f, indent=2)


def get_next_citation_number(file_path: Path) -> int:
    """Get the next available citation number for a file."""
    citations = read_json_citations(file_path)
    if not citations:
        return 1
    
    # Find highest number
    max_num = max([int(k) for k in citations.keys()])
    return max_num + 1


def file_exists(vault_path: Path, relative_path: str) -> bool:
    """Check if file exists in vault."""
    full_path = vault_path / relative_path
    return full_path.exists()


def create_new_file_template(filename: str, folder: str, purpose: str = None) -> str:
    """
    Create a template for a new markdown file.
    
    Args:
        filename: Name of file (with .md)
        folder: Folder name (for default purpose)
        purpose: Optional custom purpose description
        
    Returns:
        Template markdown content
    """
    title = filename.replace('.md', '')
    
    if not purpose:
        purpose = f"Information and notes related to {title.lower()}."
    
    template = f"""# {title}

{purpose}

## Content

(No content yet)

## Related

"""
    
    return template
