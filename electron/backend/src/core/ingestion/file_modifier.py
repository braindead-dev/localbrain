#!/usr/bin/env python3
"""
File Modifier - Makes surgical edits to existing markdown files
"""

from pathlib import Path
from typing import Dict, List, Tuple
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_client import LLMClient
from utils.file_ops import read_file, get_next_citation_number
from utils.fuzzy_matcher import find_best_section_match


SYSTEM_PROMPT = """You are a precise file editing assistant for LocalBrain knowledge management.

Your job is to determine HOW to modify an existing markdown file with new information.

EDIT STRATEGIES:
1. **append_to_section**: Add new content at end of existing section
2. **insert_after_line**: Insert content after specific line
3. **replace_line**: Replace specific line with new content
4. **create_section**: Add new ## Section at end of file (before ## Related)
5. **modify_line**: Update part of a line (e.g., change a date or detail)

THINK CAREFULLY:
- Does this content RELATE to existing content? → append/insert nearby
- Does this UPDATE existing information? → modify/replace
- Is this a NEW topic in the file? → create_section
- Are there multiple changes needed? → return multiple operations

EXAMPLE SCENARIOS:

Scenario 1: New application (append to section)
Existing: "Applied to Google [1]."
New: "Applied to Meta"
→ append_to_section in "Applications" section

Scenario 2: Interview date changed (modify line)
Existing: "Meta interview scheduled for Nov 5th [2]."
New: "Interview moved to Nov 10th"
→ modify_line to update the date

Scenario 3: New topic (create section)
Existing: Has ## Applications section
New: "Preparing for system design interviews"
→ create_section called "Interview Prep"

OUTPUT FORMAT:
Return JSON with list of edit operations:
{
  "operations": [
    {
      "type": "append_to_section|insert_after_line|replace_line|create_section|modify_line",
      "section": "Section Name" (for append_to_section),
      "line_number": 15 (for insert/replace/modify, 1-indexed),
      "content": "New content to add",
      "reason": "Why this edit"
    }
  ]
}

Be SURGICAL and PRECISE. Make minimal changes.
"""


class FileModifier:
    """Makes intelligent edits to existing files."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def determine_edits(
        self,
        file_path: Path,
        new_content: str,
        formatted_markdown: str,
        context: str
    ) -> List[Dict]:
        """
        Determine what edits to make to existing file.
        
        Args:
            file_path: Path to file
            new_content: New information to add
            formatted_markdown: Pre-formatted markdown content
            context: Original context
            
        Returns:
            List of edit operations
        """
        # Read existing file
        try:
            existing = read_file(file_path)
        except:
            # File doesn't exist, treat as append
            return [{
                "type": "append_to_end",
                "content": formatted_markdown,
                "reason": "New file"
            }]
        
        # Number the lines for reference
        lines = existing.split('\n')
        numbered_lines = '\n'.join([f"{i+1:3d} | {line}" for i, line in enumerate(lines)])
        
        prompt = f"""Analyze this file and determine how to integrate new content:

EXISTING FILE ({file_path.name}):
```
{numbered_lines}
```

NEW CONTENT TO ADD:
{new_content}

FORMATTED VERSION:
{formatted_markdown}

INSTRUCTIONS:
1. Read the existing file carefully
2. Determine if new content:
   - Relates to existing section → append_to_section
   - Updates existing info → modify_line or replace_line
   - Is new topic → create_section
3. Identify exact line numbers if needed (shown in left column)
4. Return precise edit operations

Think step by step:
- What sections exist in the file?
- Where does this content logically belong?
- Does it update or add to existing info?

Return JSON with operations list."""
        
        try:
            response = self.llm.call_json(prompt, system=SYSTEM_PROMPT, max_tokens=2048)
            
            operations = response.get('operations', [])
            
            if not operations:
                # Fallback: append to end
                operations = [{
                    "type": "append_to_end",
                    "content": formatted_markdown,
                    "reason": "No specific location determined"
                }]
            
            return operations
            
        except Exception as e:
            print(f"⚠️  Edit determination failed: {e}")
            # Fallback: simple append
            return [{
                "type": "append_to_end",
                "content": formatted_markdown,
                "reason": f"Fallback due to error: {str(e)}"
            }]
    
    def apply_edits(self, file_path: Path, operations: List[Dict]) -> str:
        """
        Apply edit operations to file.
        
        Args:
            file_path: Path to file
            operations: List of edit operations
            
        Returns:
            New file content
        """
        try:
            content = read_file(file_path)
        except:
            content = ""
        
        lines = content.split('\n')
        
        for op in operations:
            op_type = op.get('type')
            
            if op_type == 'append_to_end':
                # Add to end of file
                if not content.endswith('\n\n'):
                    content += '\n\n'
                content += op['content']
            
            elif op_type == 'append_to_section':
                # Find section and append within it
                section_name = op.get('section', '')
                content = self._append_to_section(content, section_name, op['content'])
            
            elif op_type == 'insert_after_line':
                # Insert after specific line
                line_num = op.get('line_number', len(lines))
                lines.insert(line_num, op['content'])
                content = '\n'.join(lines)
            
            elif op_type == 'replace_line':
                # Replace specific line
                line_num = op.get('line_number', 0) - 1  # Convert to 0-indexed
                if 0 <= line_num < len(lines):
                    lines[line_num] = op['content']
                    content = '\n'.join(lines)
            
            elif op_type == 'modify_line':
                # Modify part of line (replace whole line for now)
                line_num = op.get('line_number', 0) - 1
                if 0 <= line_num < len(lines):
                    lines[line_num] = op['content']
                    content = '\n'.join(lines)
            
            elif op_type == 'create_section':
                # Add new section before ## Related or at end
                section_header = f"## {op.get('section', 'Content')}"
                section_content = op['content']
                
                if '## Related' in content:
                    # Insert before Related section
                    parts = content.split('## Related')
                    content = f"{parts[0]}\n{section_header}\n\n{section_content}\n\n## Related{parts[1]}"
                else:
                    # Append at end
                    content += f"\n\n{section_header}\n\n{section_content}\n\n## Related\n\n"
        
        return content
    
    def _append_to_section(self, content: str, section_name: str, new_content: str) -> str:
        """Append content to a specific section using fuzzy matching."""
        # Try fuzzy match to find actual section
        matched_section = find_best_section_match(content, section_name, threshold=0.6)
        
        if matched_section:
            section_name = matched_section
            print(f"   Fuzzy matched '{section_name}' to '{matched_section}'")
        
        lines = content.split('\n')
        
        # Find the section
        section_line = -1
        next_section_line = len(lines)
        
        for i, line in enumerate(lines):
            if line.startswith('##') and section_name.lower() in line.lower():
                section_line = i
            elif section_line != -1 and line.startswith('##'):
                next_section_line = i
                break
        
        if section_line == -1:
            # Section not found even with fuzzy match, append at end
            return content + f"\n\n{new_content}"
        
        # Insert before next section
        lines.insert(next_section_line, new_content)
        lines.insert(next_section_line, '')  # Blank line
        
        return '\n'.join(lines)
