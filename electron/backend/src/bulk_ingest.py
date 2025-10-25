"""
Bulk ingestion pipeline for LocalBrain.

Optimized for ingesting large amounts of content quickly by:
1. Batching similar content together
2. Single LLM call per batch
3. Parallel processing when safe
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

# Load environment
dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path)

from anthropic import Anthropic
from utils.file_ops import read_file, write_file


class BulkIngestionPipeline:
    """Fast bulk ingestion for initialization / large datasets."""
    
    def __init__(self, vault_path: Path, model: str = "claude-haiku-4-5-20251001"):
        self.vault_path = Path(vault_path)
        self.model = model
        self.client = Anthropic()
        
        # Ensure vault exists
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 Initialized bulk ingestion pipeline")
        print(f"📂 Vault: {vault_path}")
        print(f"🧠 Model: {model}")
    
    def bulk_ingest(self, items: List[Dict[str, Any]], batch_size: int = 10) -> Dict:
        """
        Ingest multiple items efficiently.
        
        Args:
            items: List of {text, metadata} dicts
            batch_size: Number of items per batch
            
        Returns:
            Results dict with stats
        """
        print(f"\n📥 Bulk ingesting {len(items)} items (batch_size={batch_size})")
        
        # Group by source/platform for better batching
        grouped = self._group_by_source(items)
        
        stats = {
            'total_items': len(items),
            'successful': 0,
            'failed': 0,
            'files_created': set(),
            'files_updated': set(),
            'batches_processed': 0
        }
        
        # Process each group in batches
        for source, source_items in grouped.items():
            print(f"\n📦 Processing {source}: {len(source_items)} items")
            
            for i in range(0, len(source_items), batch_size):
                batch = source_items[i:i+batch_size]
                stats['batches_processed'] += 1
                
                print(f"  Batch {stats['batches_processed']}: {len(batch)} items")
                
                try:
                    result = self._process_batch(batch, source)
                    
                    if result['success']:
                        stats['successful'] += len(batch)
                        stats['files_created'].update(result.get('files_created', []))
                        stats['files_updated'].update(result.get('files_updated', []))
                        print(f"    ✅ Success: {result.get('files_affected', [])}")
                    else:
                        stats['failed'] += len(batch)
                        print(f"    ❌ Failed: {result.get('error')}")
                
                except Exception as e:
                    stats['failed'] += len(batch)
                    print(f"    ❌ Error: {e}")
        
        return {
            'success': True,
            'stats': {
                'total_items': stats['total_items'],
                'successful': stats['successful'],
                'failed': stats['failed'],
                'files_created': len(stats['files_created']),
                'files_updated': len(stats['files_updated']),
                'batches_processed': stats['batches_processed']
            }
        }
    
    def _group_by_source(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items by source/platform for better batching."""
        grouped = defaultdict(list)
        
        for item in items:
            metadata = item.get('metadata', {})
            source = metadata.get('platform', 'unknown')
            grouped[source].append(item)
        
        return dict(grouped)
    
    def _process_batch(self, batch: List[Dict], source: str) -> Dict:
        """
        Process a batch of items with single LLM call.
        
        Strategy: Give LLM all items at once, let it decide organization.
        Much faster than individual calls.
        """
        # Build combined prompt
        batch_text = self._format_batch(batch)
        
        # Get existing files for context
        existing_files = self._list_existing_files()
        
        # Single LLM call for entire batch
        prompt = f"""You are organizing content into a personal knowledge vault. Be concise and direct.

BATCH CONTENT ({len(batch)} items from {source}):
{batch_text}

EXISTING VAULT STRUCTURE:
{json.dumps(existing_files, indent=2)}

FOLDER NAMING RULES (CRITICAL):
1. Use Title Case with spaces: "Food and Dining" NOT "food_and_dining"
2. Create nested folders 2-3 levels deep: "Personal/Events" NOT "personal_events"  
3. Group by broad category first: "Personal/Shopping" NOT "shopping"
4. No underscores in folder names - use spaces

EXAMPLES:
✅ GOOD: "Personal/Events/weddings.md"
✅ GOOD: "Work and Career/job_search.md"
✅ GOOD: "Health/Fitness/workouts.md"
❌ BAD: "personal_events/weddings.md"
❌ BAD: "work_and_career/job_search.md"
❌ BAD: "health_and_fitness/workouts.md"

CONTENT RULES:
1. Group similar items into same file
2. Create new files only when content is distinct
3. Prefer appending over creating many files
4. Match existing folder structure when possible

OUTPUT FORMAT (JSON only, no markdown fences):
{{
  "actions": [
    {{
      "action": "append|create",
      "file": "Category/Subcategory/filename.md",
      "content": "combined content from items...",
      "items": [0, 1, 2],
      "reason": "why grouped this way"
    }}
  ]
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            response_text = response.content[0].text
            
            # Extract JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            plan = json.loads(json_str)
            
            # Execute actions
            files_created = []
            files_updated = []
            
            for action in plan['actions']:
                action_type = action['action']
                filepath = self.vault_path / action['file']
                content = action['content']
                
                # Ensure directory exists
                filepath.parent.mkdir(parents=True, exist_ok=True)
                
                if action_type == 'create' or not filepath.exists():
                    write_file(filepath, content)
                    files_created.append(action['file'])
                else:  # append
                    existing = read_file(filepath)
                    write_file(filepath, existing + "\n\n" + content)
                    files_updated.append(action['file'])
                
                # Add citations
                self._add_citations_batch(filepath, batch, action['items'])
            
            return {
                'success': True,
                'files_created': files_created,
                'files_updated': files_updated,
                'files_affected': files_created + files_updated
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_batch(self, batch: List[Dict]) -> str:
        """Format batch items for prompt."""
        lines = []
        for i, item in enumerate(batch):
            text = item['text']
            metadata = item.get('metadata', {})
            
            lines.append(f"--- ITEM {i} ---")
            lines.append(f"Source: {metadata.get('platform', 'unknown')}")
            lines.append(f"Date: {metadata.get('timestamp', 'unknown')}")
            lines.append(f"Content:\n{text[:500]}...")  # Truncate for efficiency
            lines.append("")
        
        return "\n".join(lines)
    
    def _list_existing_files(self) -> List[str]:
        """List existing markdown files in vault."""
        files = []
        for md_file in self.vault_path.rglob("*.md"):
            if md_file.name != "about.md":
                rel_path = md_file.relative_to(self.vault_path)
                files.append(str(rel_path))
        return files[:50]  # Limit for prompt size
    
    def _add_citations_batch(self, filepath: Path, batch: List[Dict], item_indices: List[int]):
        """Add citations for multiple items to a file."""
        json_path = filepath.with_suffix('.json')
        
        # Load existing citations
        if json_path.exists():
            citations = json.loads(read_file(json_path))
        else:
            citations = {}
        
        # Add new citations
        for idx in item_indices:
            item = batch[idx]
            metadata = item.get('metadata', {})
            
            # Find next citation ID
            citation_id = max([int(k) for k in citations.keys()], default=0) + 1
            
            citations[str(citation_id)] = {
                'platform': metadata.get('platform', 'unknown'),
                'timestamp': metadata.get('timestamp'),
                'url': metadata.get('url'),
                'quote': item['text'][:200],
                'note': metadata.get('note')
            }
        
        # Save citations
        write_file(json_path, json.dumps(citations, indent=2))
