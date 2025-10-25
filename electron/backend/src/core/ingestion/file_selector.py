#!/usr/bin/env python3
"""
File Selector - Determines which files to update based on ingestion context
"""

from pathlib import Path
from typing import List, Dict
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_client import LLMClient
from utils.file_ops import list_vault_files


SYSTEM_PROMPT = """You are a file organization assistant for LocalBrain, a personal knowledge management system.

Your job is to analyze new information and determine which files in the vault should be updated.

RULES:
1. Choose existing files when content is related to their topic
2. Suggest new files for distinct new topics
3. You can select MULTIPLE files if content spans topics
4. Use descriptive filenames with Title Case (e.g., "Job Search.md", not "job-search.md")
5. Consider the folder structure: personal/, career/, projects/, research/, social/, finance/, health/, learning/, archive/

Be smart about relationships:
- Job applications → career/Job Search.md
- Project work → projects/[Project Name].md
- Learning notes → learning/ or research/
- Multiple topics → Multiple files

OUTPUT FORMAT:
Return JSON array of file selections:
[
  {
    "action": "append|create|modify",
    "path": "folder/Filename.md",
    "reason": "Brief explanation",
    "priority": "primary|secondary"
  }
]

- "append": Add new content to existing file
- "create": Create new file
- "modify": Update existing content in file
- "primary": Main target for this content
- "secondary": Additional related files to update
"""


class FileSelector:
    """Selects target files for ingestion."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def select_files(self, vault_path: Path, context: str, source_metadata: Dict = None) -> List[Dict]:
        """
        Determine which files to update based on context.
        
        Args:
            vault_path: Path to vault root
            context: Text content to ingest
            source_metadata: Optional metadata about source (platform, timestamp, etc.)
            
        Returns:
            List of file selections with action, path, reason, priority
        """
        # Get list of existing files
        existing_files = list_vault_files(vault_path, include_about=False)
        
        # Build file list description
        if existing_files:
            file_list = "\n".join([
                f"- {f['relative_path']}: {f['preview'][:100]}..."
                for f in existing_files
            ])
        else:
            file_list = "(No files yet - vault is empty)"
        
        # Build prompt
        prompt = f"""Analyze this content and determine which files to update:

CONTENT TO INGEST:
{context}

SOURCE INFO:
{source_metadata if source_metadata else "Manual input"}

EXISTING FILES IN VAULT:
{file_list}

Determine:
1. Which existing file(s) should be updated?
2. Should any new files be created?
3. What is the action for each file (append/create/modify)?
4. What is the priority (primary/secondary)?

Return the JSON array of file selections."""
        
        try:
            response = self.llm.call_json(prompt, system=SYSTEM_PROMPT)
            
            # Handle both array and single object responses
            if isinstance(response, list):
                selections = response
            elif isinstance(response, dict) and 'files' in response:
                selections = response['files']
            else:
                selections = [response]
            
            # Validate selections
            for sel in selections:
                if 'action' not in sel or 'path' not in sel:
                    raise ValueError(f"Invalid selection: {sel}")
                if sel['action'] not in ['append', 'create', 'modify']:
                    sel['action'] = 'append'  # Default
                if 'priority' not in sel:
                    sel['priority'] = 'primary'
            
            return selections
            
        except Exception as e:
            print(f"⚠️  File selection failed: {e}")
            # Fallback: create a simple selection
            return [{
                "action": "append",
                "path": "personal/Notes.md",
                "reason": f"Fallback due to error: {str(e)}",
                "priority": "primary"
            }]
