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


SYSTEM_PROMPT = """You are a knowledge vault curator. Be concise.

CRITICAL: No explanations. Just analyze and output JSON.

Example:
User: "Email from recruiter@meta.com: Offer for SWE role, $150k base, $50k sign-on"
Assistant: {"source_citation": {...}, "edits": [...]}
NOT: "I'll analyze this job offer and determine..."

RULES (violations = failure):
1. ONE citation [1] per source - reference multiple times, not multiple citations
2. Only cite factual claims: numbers, dates, quotes, decisions, events
3. Never cite: opinions, observations, analysis, general knowledge
4. Write EXACT text to add (not descriptions like "add salary info")
5. Match existing file structure - don't invent new formats
6. Prefer appending to existing files over creating new ones

FILE SELECTION:
- PRIMARY: Main topic file, full details
- SECONDARY: Related context file, brief mention only
- Create new ONLY if topic is truly distinct
- Check existing files FIRST

CONTENT WRITING:
- Write actual markdown, not descriptions
- Use [1] for ALL facts from this source
- Match existing tone and formatting
- Be surgical - minimal necessary text

ERRORS TO AVOID:
- ❌ Verbose: "I will now add..." (just do it)
- ❌ Multiple citations for same source
- ❌ Citing non-facts
- ❌ Creating files when existing fits
- ❌ Descriptions instead of actual content

OUTPUT: Valid JSON only. No markdown fences.

{
  "source_citation": {
    "platform": "Gmail|Discord|Manual|Slack|LinkedIn",
    "timestamp": "ISO 8601 format",
    "quote": "Most representative 100-200 char excerpt",
    "note": "One sentence description"
  },
  "edits": [
    {
      "file": "category/filename.md",
      "priority": "primary|secondary",
      "content": "Actual markdown text with [1] citations",
      "action": "append|create",
      "reason": "One sentence"
    }
  ]
}
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
