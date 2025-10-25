#!/usr/bin/env python3
"""
Content Formatter - Formats content for insertion into markdown files
"""

from pathlib import Path
from typing import Dict, Tuple
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_client import LLMClient
from utils.file_ops import read_file, get_next_citation_number


SYSTEM_PROMPT = """You are a content formatting assistant for LocalBrain knowledge management.

Your job is to format new information for insertion into markdown files with proper structure and citations.

MARKDOWN FORMAT RULES:
1. Use clean, readable markdown
2. Use [1], [2], [3] for citation markers (NOT [^1] footnotes)
3. Citations go at the END of sentences or clauses
4. Only cite FACTUAL CLAIMS (dates, numbers, quotes, events)
5. Don't cite opinions or general observations
6. Keep content concise and informative
7. Use ## for section headers if creating new sections

CITATION GUIDELINES:
- Dates, times, numbers → Cite
- Direct quotes → Cite
- Specific events/decisions → Cite  
- Your analysis/connections → Don't cite
- General observations → Don't cite

EXAMPLE OUTPUT:
Applied to Google for SWE intern position on October 15, 2024 [1]. The role focuses on distributed systems and infrastructure work. Received confirmation email same day [2].

(Notice: facts are cited [1][2], but "The role focuses..." is descriptive and not cited)
"""


class ContentFormatter:
    """Formats content with proper markdown and citations."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def format_for_append(
        self,
        vault_path: Path,
        file_path: Path,
        context: str,
        source_metadata: Dict
    ) -> Tuple[str, Dict]:
        """
        Format content for appending to existing file.
        
        Args:
            vault_path: Path to vault root
            file_path: Target file path
            context: Content to add
            source_metadata: Source info (platform, timestamp, url, quote)
            
        Returns:
            (formatted_markdown, citation_metadata_dict)
        """
        # Read existing file to understand structure
        try:
            existing_content = read_file(file_path)
            file_preview = existing_content[:500] if len(existing_content) > 500 else existing_content
        except:
            file_preview = "(New file)"
        
        # Get next citation number
        next_num = get_next_citation_number(file_path)
        
        # Build prompt
        prompt = f"""Format this content for appending to an existing file:

NEW CONTENT:
{context}

SOURCE METADATA:
- Platform: {source_metadata.get('platform', 'Manual')}
- Timestamp: {source_metadata.get('timestamp', 'N/A')}
- URL: {source_metadata.get('url', 'N/A')}
- Quote: {source_metadata.get('quote', 'N/A')}

EXISTING FILE PREVIEW:
{file_preview}

INSTRUCTIONS:
1. Format content as clean markdown
2. Use citation numbers starting from [{next_num}]
3. Only cite factual claims that need verification
4. Make it fit naturally with existing content style
5. Return JSON with two fields:
   - "markdown": The formatted content
   - "citations": Object mapping citation numbers to metadata

EXAMPLE JSON OUTPUT:
{{
  "markdown": "Applied to Meta on Oct 20 [{next_num}]. Got interview [{next_num + 1}].",
  "citations": {{
    "{next_num}": {{"platform": "Gmail", "timestamp": "2024-10-20T10:00:00Z", "url": null, "quote": "Application received"}},
    "{next_num + 1}": {{"platform": "Gmail", "timestamp": "2024-10-22T14:00:00Z", "url": null, "quote": "We'd like to schedule an interview"}}
  }}
}}

Now format the content:"""
        
        try:
            response = self.llm.call_json(prompt, system=SYSTEM_PROMPT, max_tokens=2048)
            
            markdown = response.get('markdown', context)
            citations = response.get('citations', {})
            
            return markdown, citations
            
        except Exception as e:
            print(f"⚠️  Content formatting failed: {e}")
            # Fallback: simple format
            return f"{context} [{next_num}].", {
                str(next_num): {
                    "platform": source_metadata.get('platform', 'Manual'),
                    "timestamp": source_metadata.get('timestamp', ''),
                    "url": source_metadata.get('url'),
                    "quote": source_metadata.get('quote')
                }
            }
    
    def format_for_new_file(
        self,
        file_path: Path,
        context: str,
        source_metadata: Dict,
        purpose: str = None
    ) -> Tuple[str, Dict]:
        """
        Format content for a new file with complete structure.
        
        Returns:
            (complete_markdown_file, citation_metadata_dict)
        """
        filename = file_path.stem
        
        prompt = f"""Create a complete markdown file for this content:

FILENAME: {filename}.md

CONTENT:
{context}

SOURCE METADATA:
- Platform: {source_metadata.get('platform', 'Manual')}
- Timestamp: {source_metadata.get('timestamp', 'N/A')}
- URL: {source_metadata.get('url', 'N/A')}
- Quote: {source_metadata.get('quote', 'N/A')}

INSTRUCTIONS:
1. Start with # {filename} as title
2. Add a purpose/description paragraph
3. Create relevant ## sections
4. Format the content with citations [1], [2], etc.
5. Add ## Related section at end (leave empty for now)
6. Return JSON with "markdown" and "citations"

EXAMPLE STRUCTURE:
# {filename}

Purpose paragraph explaining what this file contains.

## Main Section

Content here with citations [1].

## Related

"""
        
        try:
            response = self.llm.call_json(prompt, system=SYSTEM_PROMPT, max_tokens=3000)
            
            markdown = response.get('markdown', '')
            citations = response.get('citations', {})
            
            return markdown, citations
            
        except Exception as e:
            print(f"⚠️  New file formatting failed: {e}")
            # Fallback: basic template
            markdown = f"""# {filename}

Information related to {filename.lower()}.

## Content

{context} [1].

## Related

"""
            citations = {
                "1": {
                    "platform": source_metadata.get('platform', 'Manual'),
                    "timestamp": source_metadata.get('timestamp', ''),
                    "url": source_metadata.get('url'),
                    "quote": source_metadata.get('quote')
                }
            }
            return markdown, citations
