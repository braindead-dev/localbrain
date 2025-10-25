"""
Natural Language Search for LocalBrain

Input: Natural language query
Output: Relevant context + answer

Uses agentic retrieval (ripgrep + LLM with tools) under the hood.
Model: claude-haiku-4-5-20251001 (same as ingestion)
"""

import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import os
from anthropic import Anthropic

try:
    from src.utils.file_ops import read_file
except ImportError:
    # Fallback for direct execution
    from utils.file_ops import read_file


class Search:
    """
    Natural language search for LocalBrain.
    
    Input: Natural language query (e.g., "What was my Meta offer?")
    Output: Answer + relevant context
    
    Uses agentic retrieval: LLM with grep_vault and read_file tools.
    Model: claude-haiku-4-5-20251001 (same as ingestion)
    """
    
    def __init__(self, vault_path: Path, model: str = "claude-haiku-4-5-20251001"):
        self.vault_path = Path(vault_path)
        self.model = model
        
        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        self.client = Anthropic(api_key=api_key)
        
    def search(self, query: str, max_results: int = 5) -> Dict:
        """
        Agentic search using LLM with grep and read tools.
        
        Flow:
        1. Give LLM tools: grep_vault, read_file
        2. LLM decides what to search for
        3. LLM reads relevant files
        4. LLM synthesizes answer
        """
        print(f"🔍 Agentic search: {query}")
        
        # System prompt for search agent
        system_prompt = f"""You are a search agent for a personal knowledge vault.

Your task: Answer the user's query by searching and reading their markdown files.

Available tools:
1. grep_vault(pattern, limit=20) - Search markdown files for pattern (regex supported)
2. read_file(filepath) - Read a specific markdown file

Vault location: {self.vault_path}

Strategy:
- Use grep_vault to find relevant files (sorted by modification time - recent = relevant)
- Read the most promising files
- Synthesize answer from file contents
- Include citations [filename] in your answer

Be thorough but efficient. Don't read more than 5 files unless necessary."""

        # Define tools for LLM
        tools = [
            {
                "name": "grep_vault",
                "description": "Search all markdown files in vault using regex pattern. Returns list of matching files sorted by modification time (recent first).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for (case-insensitive)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 20
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "read_file",
                "description": "Read the full contents of a markdown file from the vault.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to file relative to vault (e.g. 'career/Job Search.md')"
                        }
                    },
                    "required": ["filepath"]
                }
            }
        ]
        
        # Run agentic loop
        messages = [{"role": "user", "content": query}]
        
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Call LLM with tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=messages,
                system=system_prompt,
                tools=tools
            )
            
            # Add assistant response to messages
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            # Check if LLM wants to use tools
            if hasattr(response, 'stop_reason') and response.stop_reason == 'tool_use':
                # Process tool calls
                tool_results = []
                
                for content_block in response.content:
                    if content_block.type == 'tool_use':
                        tool_name = content_block.name
                        tool_input = content_block.input
                        tool_use_id = content_block.id
                        
                        print(f"  🔧 Tool call: {tool_name}({tool_input})")
                        
                        # Execute tool
                        if tool_name == "grep_vault":
                            result = self._grep_vault(
                                pattern=tool_input['pattern'],
                                limit=tool_input.get('limit', 20)
                            )
                        elif tool_name == "read_file":
                            result = self._read_file(tool_input['filepath'])
                        else:
                            result = {"error": f"Unknown tool: {tool_name}"}
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result, indent=2)
                        })
                
                # Add tool results to messages
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                
            else:
                # LLM is done - extract context chunks
                print(f"✅ Search complete ({iteration} iterations)")
                
                # Extract files that were read
                contexts = self._extract_contexts(messages)
                
                return {
                    "success": True,
                    "query": query,
                    "contexts": contexts,
                    "total_results": len(contexts)
                }
        
        return {
            "success": False,
            "error": "Max iterations reached",
            "iterations": iteration
        }
    
    def _extract_contexts(self, messages: List[Dict]) -> List[Dict]:
        """
        Extract context chunks from read_file tool results.
        
        Returns list of contexts with:
        - text: Actual content from .md file
        - file: File path
        - citations: Array of citation objects referenced in text
        """
        contexts = []
        
        # Find all read_file tool results in messages
        for msg in messages:
            if msg.get("role") != "user":
                continue
            
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            
            for item in content:
                if item.get("type") != "tool_result":
                    continue
                
                # Parse tool result
                try:
                    result_str = item.get("content", "{}")
                    result = json.loads(result_str)
                    
                    if "content" not in result or "filepath" not in result:
                        continue
                    
                    file_content = result["content"]
                    filepath = result["filepath"]
                    all_citations = result.get("citations", {})
                    
                    # Extract relevant paragraphs (simplified: take first few paragraphs)
                    # In production, could use LLM to identify most relevant sections
                    paragraphs = self._extract_paragraphs(file_content)
                    
                    if not paragraphs:
                        continue
                    
                    # Take first 3 paragraphs as context
                    text = "\n\n".join(paragraphs[:3])
                    
                    # Find which citations are referenced in this text
                    cited_ids = self._find_citation_ids(text)
                    
                    # Build citations array
                    citations = []
                    for cid in cited_ids:
                        if str(cid) in all_citations:
                            citation_data = all_citations[str(cid)]
                            citations.append({
                                "id": cid,
                                "platform": citation_data.get("platform"),
                                "timestamp": citation_data.get("timestamp"),
                                "url": citation_data.get("url"),
                                "quote": citation_data.get("quote"),
                                "note": citation_data.get("note")
                            })
                    
                    contexts.append({
                        "text": text,
                        "file": filepath,
                        "citations": citations
                    })
                    
                except Exception as e:
                    print(f"  ⚠️  Error extracting context: {e}")
                    continue
        
        return contexts
    
    def _extract_paragraphs(self, content: str) -> List[str]:
        """Extract non-empty paragraphs from markdown content."""
        # Split by double newlines
        paragraphs = content.split('\n\n')
        
        # Filter out headers, empty lines, and about.md sections
        result = []
        for p in paragraphs:
            p = p.strip()
            # Skip if empty, is a header, or is the about.md boilerplate
            if not p or p.startswith('#') or 'This file contains' in p:
                continue
            result.append(p)
        
        return result
    
    def _find_citation_ids(self, text: str) -> List[int]:
        """Find all citation markers [1], [2], etc. in text."""
        import re
        matches = re.findall(r'\[(\d+)\]', text)
        return sorted(set(int(m) for m in matches))
    
    def _grep_vault(self, pattern: str, limit: int = 20) -> Dict:
        """
        Grep vault using ripgrep (or fallback to grep).
        Returns files sorted by modification time.
        """
        try:
            # Try ripgrep first (much faster)
            cmd = [
                'rg',
                '--case-insensitive',
                '--type', 'md',
                '--files-with-matches',
                '--max-count', '1',  # Stop after first match per file
                '--sort', 'modified',  # Sort by modification time (recent first)
                pattern,
                str(self.vault_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                files = result.stdout.strip().split('\n')
                files = [f for f in files if f]  # Remove empty lines
                files = files[:limit]  # Limit results
                
                # Convert to relative paths and get preview
                results = []
                for file_path in files:
                    rel_path = Path(file_path).relative_to(self.vault_path)
                    
                    # Get a snippet from the file
                    try:
                        content = read_file(Path(file_path))
                        lines = content.split('\n')
                        # Find line with match
                        matching_lines = [l for l in lines if pattern.lower() in l.lower()]
                        preview = matching_lines[0] if matching_lines else lines[0] if lines else ""
                        preview = preview[:100] + "..." if len(preview) > 100 else preview
                    except:
                        preview = ""
                    
                    results.append({
                        "file": str(rel_path),
                        "preview": preview
                    })
                
                return {
                    "matches": results,
                    "count": len(results),
                    "pattern": pattern
                }
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to simple file walk if ripgrep not available
            pass
        
        # Fallback: manual search
        results = []
        for md_file in self.vault_path.rglob("*.md"):
            if md_file.name.startswith('.'):
                continue
            
            try:
                content = read_file(md_file)
                if pattern.lower() in content.lower():
                    rel_path = md_file.relative_to(self.vault_path)
                    
                    # Get preview
                    lines = content.split('\n')
                    matching_lines = [l for l in lines if pattern.lower() in l.lower()]
                    preview = matching_lines[0] if matching_lines else ""
                    preview = preview[:100] + "..." if len(preview) > 100 else preview
                    
                    results.append({
                        "file": str(rel_path),
                        "preview": preview,
                        "modified": md_file.stat().st_mtime
                    })
            except:
                continue
        
        # Sort by modification time
        results.sort(key=lambda x: x.get('modified', 0), reverse=True)
        results = results[:limit]
        
        return {
            "matches": results,
            "count": len(results),
            "pattern": pattern
        }
    
    def _read_file(self, filepath: str) -> Dict:
        """Read a file from the vault."""
        try:
            file_path = self.vault_path / filepath
            
            if not file_path.exists():
                return {"error": f"File not found: {filepath}"}
            
            if not file_path.is_relative_to(self.vault_path):
                return {"error": "Access denied: file outside vault"}
            
            content = read_file(file_path)
            
            # Also read citations if available
            json_path = file_path.with_suffix('.json')
            citations = {}
            if json_path.exists():
                try:
                    citations = json.loads(read_file(json_path))
                except:
                    pass
            
            return {
                "filepath": filepath,
                "content": content,
                "citations": citations,
                "length": len(content)
            }
            
        except Exception as e:
            return {"error": str(e)}
