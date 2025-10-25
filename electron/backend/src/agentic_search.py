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
                # LLM is done, return final answer
                final_answer = response.content[0].text if response.content else "No answer generated"
                
                print(f"✅ Search complete ({iteration} iterations)")
                
                return {
                    "success": True,
                    "answer": final_answer,
                    "iterations": iteration,
                    "query": query
                }
        
        return {
            "success": False,
            "error": "Max iterations reached",
            "iterations": iteration
        }
    
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
