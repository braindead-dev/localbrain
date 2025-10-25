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
        
        # System prompt for search agent (OpenCode-inspired: ultra-concise)
        system_prompt = f"""You are a search agent. Answer questions by searching markdown files. Be direct.

Tools:
- grep_vault(pattern) - Search files, returns matches with line numbers
- read_file(filepath) - Read file

IMPORTANT: Minimize output. Answer directly without explanation.

Example:
Q: Which device first, Samsung S22 or Dell XPS?
1. grep_vault("Samsung.*S22") → tech/devices.md:5 "Purchased Feb 20, 2023"
2. grep_vault("Dell.*XPS") → tech/devices.md:10 "Arrived Feb 25, 2023"
3. Compare: Feb 20 < Feb 25
Answer: Samsung Galaxy S22

Strategy:
1. Grep for key terms
2. Check line numbers and dates
3. Read files ONLY if grep insufficient
4. Answer with facts, no hedging

Vault: {self.vault_path}"""

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
        Extract context chunks from grep_vault AND read_file tool results.
        
        Returns list of contexts with:
        - text: Actual content
        - file: File path
        - citations: Array of citation objects (if from read_file)
        """
        contexts = []
        seen_files = set()
        
        # Find all tool results in messages
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
                    
                    # Handle grep_vault results - read full files for better context
                    if "matches" in result:
                        for match in result.get("matches", []):
                            file = match.get("file")
                            if file and file not in seen_files:
                                # Read full file content for better context
                                try:
                                    from utils.file_ops import read_file
                                    file_path = self.vault_path / file
                                    content = read_file(file_path)
                                    
                                    # Extract first few paragraphs as context
                                    paragraphs = self._extract_paragraphs(content)
                                    text = "\n\n".join(paragraphs[:5]) if paragraphs else content[:1000]
                                    
                                    contexts.append({
                                        "file": file,
                                        "text": text,
                                        "citations": []
                                    })
                                    seen_files.add(file)
                                except Exception as e:
                                    # Fallback to just the match line
                                    contexts.append({
                                        "file": file,
                                        "text": match.get("match_text", match.get("preview", "")),
                                        "line_number": match.get("line_number"),
                                        "citations": []
                                    })
                                    seen_files.add(file)
                        continue
                    
                    # Handle read_file results
                    
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
                # Parse ripgrep output with line numbers
                # Format: filepath:line_number:line_content
                results = []
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        file_path = Path(parts[0])
                        line_num = parts[1]
                        match_text = parts[2]
                        
                        try:
                            rel_path = file_path.relative_to(self.vault_path)
                            
                            results.append({
                                "file": str(rel_path),
                                "line_number": int(line_num),
                                "match_text": match_text.strip(),
                                "preview": match_text.strip()[:150]
                            })
                        except:
                            continue
                
                # Limit and group by file
                results = results[:limit * 2]  # More results for better coverage
                
                return {
                    "matches": results,
                    "count": len(results),
                    "pattern": pattern
                }
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to simple file walk if ripgrep not available
            pass
        
        # Fallback: manual search with line numbers
        results = []
        for md_file in self.vault_path.rglob("*.md"):
            if md_file.name.startswith('.'):
                continue
            
            try:
                content = read_file(md_file)
                lines = content.split('\n')
                rel_path = md_file.relative_to(self.vault_path)
                
                # Find all matching lines with line numbers
                for line_num, line in enumerate(lines, 1):
                    if pattern.lower() in line.lower():
                        results.append({
                            "file": str(rel_path),
                            "line_number": line_num,
                            "match_text": line.strip(),
                            "preview": line.strip()[:150],
                            "modified": md_file.stat().st_mtime
                        })
            except:
                continue
        
        # Sort by modification time
        results.sort(key=lambda x: x.get('modified', 0), reverse=True)
        results = results[:limit * 2]
        
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
