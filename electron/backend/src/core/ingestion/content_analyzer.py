#!/usr/bin/env python3
"""
Content Analyzer - Analyzes and routes content with specific edit plans

This is the NEW first step that replaces separate file selection + formatting.
Instead of deciding WHERE then HOW, we decide WHAT to say, then WHERE/HOW.
"""

from pathlib import Path
from typing import List, Dict
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_client import LLMClient
from utils.file_ops import list_vault_files


SYSTEM_PROMPT = """You are a content routing assistant for LocalBrain knowledge management.

Your job: Analyze new information and create SPECIFIC EDIT PLANS for vault files.

CRITICAL RULES:
1. Think about WHAT you want to say FIRST, then WHERE to put it
2. Create ONE citation per source document (not multiple citations per fact)
3. Only select files you have SPECIFIC edits for
4. PRIMARY files get full details, SECONDARY files get brief mentions

OUTPUT FORMAT:
Return JSON with edit plans:
{
  "source_citation": {
    "platform": "Gmail",
    "timestamp": "...",
    "quote": "The most relevant excerpt from source (100-200 chars)",
    "note": "Brief description of what this source is"
  },
  "edits": [
    {
      "file": "career/Job Search.md",
      "priority": "primary",
      "content": "Received offer from Netflix for Software Engineer - Content Streaming [1]. Base salary $155k, sign-on $25k, RSUs $180k over 4 years [1]. Start date July 14, 2025 [1]. Deadline October 31 [1].",
      "action": "append|create|modify",
      "reason": "Why this edit is needed"
    },
    {
      "file": "personal/About Me.md",
      "priority": "secondary", 
      "content": "Accepted position at Netflix [1].",
      "action": "append",
      "reason": "Brief career update"
    }
  ]
}

CITATION RULES:
- ONE citation [1] for the entire source
- Reference [1] multiple times in content, but same citation
- All facts from same source use same citation number
- Quote should be representative excerpt, not individual facts

DETAIL LEVEL RULES:
- PRIMARY: Full details (salary $155k, bonus $25k, specific dates)
- SECONDARY: Key fact only ("Accepted position at Netflix")

ONLY SELECT FILES YOU HAVE REAL EDITS FOR.
Don't speculatively select files "just in case".
"""


class ContentAnalyzer:
    """Analyzes content and creates specific edit plans."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def analyze_and_route(
        self,
        vault_path: Path,
        context: str,
        source_metadata: Dict
    ) -> Dict:
        """
        Analyze content and create specific edit plans.
        
        Returns:
            {
                "source_citation": {...},
                "edits": [...]
            }
        """
        # Get existing files for context
        existing_files = list_vault_files(vault_path, include_about=False)
        
        if existing_files:
            file_list = "\n".join([
                f"- {f['relative_path']}"
                for f in existing_files[:20]  # Limit to avoid token bloat
            ])
        else:
            file_list = "(Vault is empty)"
        
        # Build prompt
        prompt = f"""Analyze this content and create specific edit plans:

CONTENT TO INGEST:
{context}

SOURCE INFO:
- Platform: {source_metadata.get('platform', 'Manual')}
- Timestamp: {source_metadata.get('timestamp', 'N/A')}

EXISTING FILES IN VAULT:
{file_list}

TASK:
1. Identify the key information in this content
2. Decide what specific text to add to each file
3. Choose PRIMARY vs SECONDARY detail level
4. Create ONE citation for the source
5. Return edit plans

Remember:
- Write the actual content you want to add (don't just describe it)
- Use [1] for citation references in the content
- Only include files you have specific edits for
- Don't create new files unless truly needed (prefer existing files)
"""
        
        try:
            response = self.llm.call_json(prompt, system=SYSTEM_PROMPT, max_tokens=3000)
            
            # Validate response
            if 'edits' not in response:
                raise ValueError("Response missing 'edits' field")
            
            if 'source_citation' not in response:
                # Create default citation
                response['source_citation'] = {
                    "platform": source_metadata.get('platform', 'Manual'),
                    "timestamp": source_metadata.get('timestamp', ''),
                    "url": source_metadata.get('url'),
                    "quote": context[:200] if len(context) > 200 else context,
                    "note": "Ingested content"
                }
            
            # Ensure all edits have required fields
            for edit in response['edits']:
                if 'file' not in edit or 'content' not in edit:
                    raise ValueError(f"Edit missing required fields: {edit}")
                if 'action' not in edit:
                    edit['action'] = 'append'
                if 'priority' not in edit:
                    edit['priority'] = 'primary'
            
            return response
            
        except Exception as e:
            print(f"⚠️  Content analysis failed: {e}")
            # Fallback
            return {
                "source_citation": {
                    "platform": source_metadata.get('platform', 'Manual'),
                    "timestamp": source_metadata.get('timestamp', ''),
                    "url": source_metadata.get('url'),
                    "quote": context[:200],
                    "note": "Ingested content"
                },
                "edits": [{
                    "file": "personal/Notes.md",
                    "priority": "primary",
                    "content": f"{context} [1].",
                    "action": "append",
                    "reason": f"Fallback due to error: {str(e)}"
                }]
            }
