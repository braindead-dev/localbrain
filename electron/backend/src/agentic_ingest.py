#!/usr/bin/env python3
"""
Agentic Ingestion Pipeline - Full AI-powered ingestion for LocalBrain

Uses Claude to intelligently:
1. Analyze content and select target files
2. Determine edit strategy (append/modify/create)
3. Format content with proper citations
4. Apply surgical edits to files
5. Update JSON citation metadata
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path)

from utils.llm_client import LLMClient
from utils.file_ops import (
    read_file, write_file, file_exists,
    create_new_file_template, list_vault_files
)
from core.ingestion.file_selector import FileSelector
from core.ingestion.content_formatter import ContentFormatter
from core.ingestion.file_modifier import FileModifier
from core.ingestion.citation_manager import CitationManager


class AgenticIngestionPipeline:
    """Full agentic ingestion pipeline with Claude."""
    
    def __init__(self, vault_path: Path):
        """Initialize pipeline."""
        self.vault_path = Path(vault_path)
        
        # Initialize Claude client (using Haiku 4.5 for speed)
        self.llm = LLMClient(model="claude-haiku-4-5-20251001")
        
        # Initialize components
        self.file_selector = FileSelector(self.llm)
        self.formatter = ContentFormatter(self.llm)
        self.modifier = FileModifier(self.llm)
        self.citations = CitationManager()
        
        print(f"🤖 Initialized agentic ingestion pipeline")
        print(f"📂 Vault: {self.vault_path}")
        print(f"🧠 Model: claude-haiku-4-5-20251001\n")
    
    def ingest(
        self,
        context: str,
        source_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest content with full AI pipeline.
        
        Args:
            context: Text content to ingest
            source_metadata: Optional dict with {platform, timestamp, url, quote}
            
        Returns:
            Dict with ingestion results
        """
        print(f"📥 Ingesting content...")
        print(f"   Context preview: {context[:100]}...")
        
        # Default source metadata
        if source_metadata is None:
            source_metadata = {
                'platform': 'Manual',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'url': None,
                'quote': None
            }
        
        results = {
            'success': False,
            'files_modified': [],
            'files_created': [],
            'errors': []
        }
        
        try:
            # STEP 1: Select target files
            print("\n🎯 Step 1: Selecting target files...")
            selections = self.file_selector.select_files(
                self.vault_path,
                context,
                source_metadata
            )
            
            print(f"   Selected {len(selections)} file(s):")
            for sel in selections:
                print(f"   - {sel['action'].upper()}: {sel['path']} ({sel['priority']})")
                print(f"     Reason: {sel.get('reason', 'N/A')}")
            
            # STEP 2: Process each selected file
            for selection in selections:
                file_path = self.vault_path / selection['path']
                action = selection['action']
                
                print(f"\n📝 Processing: {selection['path']}")
                
                try:
                    if action == 'create':
                        # Create new file
                        success = self._create_new_file(
                            file_path,
                            context,
                            source_metadata
                        )
                        if success:
                            results['files_created'].append(str(file_path))
                    
                    elif action == 'append':
                        # Append to existing file
                        success = self._append_to_file(
                            file_path,
                            context,
                            source_metadata,
                            priority=selection.get('priority', 'primary')
                        )
                        if success:
                            results['files_modified'].append(str(file_path))
                    
                    elif action == 'modify':
                        # Modify existing file
                        success = self._modify_file(
                            file_path,
                            context,
                            source_metadata,
                            priority=selection.get('priority', 'primary')
                        )
                        if success:
                            results['files_modified'].append(str(file_path))
                    
                except Exception as e:
                    error_msg = f"Error processing {selection['path']}: {str(e)}"
                    print(f"   ⚠️  {error_msg}")
                    results['errors'].append(error_msg)
            
            results['success'] = len(results['files_modified']) + len(results['files_created']) > 0
            
            # Summary
            print(f"\n✨ Ingestion complete!")
            print(f"   Files created: {len(results['files_created'])}")
            print(f"   Files modified: {len(results['files_modified'])}")
            if results['errors']:
                print(f"   Errors: {len(results['errors'])}")
            
            return results
            
        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            print(f"\n❌ {error_msg}")
            results['errors'].append(error_msg)
            return results
    
    def _create_new_file(
        self,
        file_path: Path,
        context: str,
        source_metadata: Dict
    ) -> bool:
        """Create a new file with formatted content."""
        print(f"   Creating new file...")
        
        # Format content for new file
        markdown, citations = self.formatter.format_for_new_file(
            file_path,
            context,
            source_metadata
        )
        
        # Write file
        write_file(file_path, markdown)
        print(f"   ✅ Created: {file_path.name}")
        
        # Write citations
        if citations:
            clean_citations = self.citations.clean_citations(citations)
            self.citations.add_citations(file_path, clean_citations)
            print(f"   ✅ Added {len(citations)} citation(s)")
        
        return True
    
    def _append_to_file(
        self,
        file_path: Path,
        context: str,
        source_metadata: Dict,
        priority: str = "primary"
    ) -> bool:
        """Append content to existing file."""
        detail_level = "full details" if priority == "primary" else "high-level summary"
        print(f"   Appending to file ({detail_level})...")
        
        # Check if file exists
        if not file_path.exists():
            print(f"   File doesn't exist, creating new file instead...")
            return self._create_new_file(file_path, context, source_metadata)
        
        # Format content with priority
        formatted_md, new_citations = self.formatter.format_for_append(
            self.vault_path,
            file_path,
            context,
            source_metadata,
            priority=priority
        )
        
        # Determine where to place content
        operations = self.modifier.determine_edits(
            file_path,
            context,
            formatted_md,
            context
        )
        
        print(f"   Applying {len(operations)} edit operation(s)...")
        for i, op in enumerate(operations, 1):
            print(f"     {i}. {op['type']}: {op.get('reason', 'N/A')[:50]}...")
        
        # Apply edits
        new_content = self.modifier.apply_edits(file_path, operations)
        
        # Write updated file
        write_file(file_path, new_content)
        print(f"   ✅ Updated: {file_path.name}")
        
        # Update citations
        if new_citations:
            clean_citations = self.citations.clean_citations(new_citations)
            self.citations.add_citations(file_path, clean_citations)
            print(f"   ✅ Added {len(new_citations)} citation(s)")
        
        return True
    
    def _modify_file(
        self,
        file_path: Path,
        context: str,
        source_metadata: Dict,
        priority: str = "primary"
    ) -> bool:
        """Modify existing content in file."""
        print(f"   Modifying existing content...")
        
        # Same as append but with different edit strategy
        # The modifier will determine if it's a true modification or append
        return self._append_to_file(file_path, context, source_metadata, priority=priority)


def main():
    """CLI interface for agentic ingestion."""
    if len(sys.argv) < 3:
        print("Usage: python agentic_ingest.py <vault_path> <context> [source_json]")
        print("\nExample:")
        print('  python agentic_ingest.py ~/my-vault "Got offer from Meta"')
        print('  python agentic_ingest.py ~/my-vault "Interview" \'{"platform": "Gmail", ...}\'')
        sys.exit(1)
    
    vault_path = Path(sys.argv[1]).expanduser()
    context = sys.argv[2]
    
    # Parse source metadata if provided
    source_metadata = None
    if len(sys.argv) > 3:
        try:
            source_metadata = json.loads(sys.argv[3])
        except json.JSONDecodeError as e:
            print(f"⚠️  Invalid JSON for source metadata: {e}")
            print("   Using default metadata...")
    
    # Run ingestion
    pipeline = AgenticIngestionPipeline(vault_path)
    results = pipeline.ingest(context, source_metadata)
    
    # Exit code
    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()
