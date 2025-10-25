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
from utils.file_ops import list_vault_files, read_file


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
7. CHECK EXISTING CONTENT - don't duplicate what's already there

DUPLICATE HANDLING:
- If info already exists with same facts → SKIP (return empty edits)
- If info exists but NEW SOURCE confirms it → append [NEW] to existing citation
  Example: "Accepted to NVIDIA [2]" becomes "Accepted to NVIDIA [2][NEW]"
- If info is NEW or different → add normally with [1]
- Citations don't need to be sequential in file, just in order added
- IMPORTANT: For update_citation, use [NEW] placeholder, not [1]

FILE SELECTION:
- PRIMARY: Main topic file, full details
- SECONDARY: Related context file, brief mention only
- Create new ONLY if topic is truly distinct
- Read existing content to avoid duplicates

CONTENT WRITING:
- Write actual markdown, not descriptions
- Use [1] for ALL facts from this source
- Match existing tone and formatting
- Be surgical - minimal necessary text
- If confirming existing fact, add [1] to existing line

ERRORS TO AVOID:
- ❌ Verbose: "I will now add..." (just do it)
- ❌ Multiple citations for same source
- ❌ Citing non-facts
- ❌ Creating files when existing fits
- ❌ Descriptions instead of actual content
- ❌ DUPLICATING existing information

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
      "action": "append|create|update_citation",
      "reason": "One sentence"
    }
  ]
}

For update_citation action:
{
  "action": "update_citation",
  "search_text": "Exact text to find",
  "replace_with": "Same text with [1] added"
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
        # Get existing files with content snippets
        existing_files = list_vault_files(vault_path, include_about=False)
        
        file_info = []
        if existing_files:
            # Read top 10 most relevant files (by modification time or relevance)
            for f in existing_files[:10]:
                file_path = vault_path / f['relative_path']
                try:
                    content = read_file(file_path)
                    # Get first 500 chars (enough to see recent additions)
                    snippet = content[:500] + "..." if len(content) > 500 else content
                    file_info.append(f"\n## {f['relative_path']}\n{snippet}\n")
                except:
                    file_info.append(f"\n## {f['relative_path']}\n(Could not read)\n")
            
            file_list = "".join(file_info)
        else:
            file_list = "(Vault is empty)"
        
        # Build prompt
        prompt = f"""Analyze this content and create specific edit plans:

CONTENT TO INGEST:
{context}

SOURCE INFO:
- Platform: {source_metadata.get('platform', 'Manual')}
- Timestamp: {source_metadata.get('timestamp', 'N/A')}

EXISTING FILES IN VAULT (check for duplicates!):
{file_list}

TASK:
1. READ existing content carefully
2. Check if this info already exists
3. If duplicate → skip or just add citation to existing fact
4. If new → write specific text to add
5. Return edit plans

DUPLICATE HANDLING:
- Same info, same source → SKIP (empty edits)
- Same info, NEW source → update_citation action (add [1] to existing)
- New or different info → append with [1]

Remember:
- Citations don't need to be sequential, just in order added
- Don't duplicate existing content!
- Write actual markdown, not descriptions
- Use [1] for this source
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
                if 'file' not in edit:
                    raise ValueError(f"Edit missing 'file' field: {edit}")
                
                # Set default action
                if 'action' not in edit:
                    edit['action'] = 'append'
                
                # Validate fields based on action
                if edit['action'] == 'update_citation':
                    if 'search_text' not in edit or 'replace_with' not in edit:
                        raise ValueError(f"update_citation edit missing search_text or replace_with: {edit}")
                else:
                    if 'content' not in edit:
                        raise ValueError(f"Edit missing 'content' field: {edit}")
                
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
