#!/usr/bin/env python3
"""
Agentic Ingestion Pipeline V2 - Redesigned for accuracy

Key improvements over V1:
1. Single-pass analysis: Decides WHAT + WHERE + HOW together
2. One citation per source (not per fact)
3. Pre-written content (no separate formatting step)
4. Validation that citations are actually used

Flow:
  Input → Analyze & Route → Apply Edits → Validate → Done

vs V1:
  Input → Select Files → Format Content → Determine Edits → Apply → Done
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
from utils.file_ops import read_file, write_file
from core.ingestion.content_analyzer import ContentAnalyzer
from core.ingestion.file_modifier import FileModifier
from core.ingestion.citation_manager import CitationManager


class AgenticIngestionPipelineV2:
    """Redesigned ingestion pipeline with single-pass analysis."""
    
    def __init__(self, vault_path: Path):
        """Initialize pipeline."""
        self.vault_path = Path(vault_path)
        
        # Initialize Claude client
        self.llm = LLMClient(model="claude-haiku-4-5-20251001")
        
        # Initialize components
        self.analyzer = ContentAnalyzer(self.llm)
        self.modifier = FileModifier(self.llm)
        self.citations = CitationManager()
        
        print(f"🤖 Initialized agentic ingestion pipeline V2")
        print(f"📂 Vault: {self.vault_path}")
        print(f"🧠 Model: claude-haiku-4-5-20251001\n")
    
    def ingest(
        self,
        context: str,
        source_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest content with redesigned pipeline.
        
        Flow:
        1. Analyze content → Get edit plans with pre-written content
        2. Apply edits directly (content already formatted)
        3. Add ONE citation per source
        4. Validate citations are used
        """
        print(f"📥 Ingesting content...")
        print(f"   Context preview: {context[:100]}...\n")
        
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
            # STEP 1: Analyze and create edit plans (SINGLE CALL)
            print("🎯 Analyzing content and creating edit plans...")
            analysis = self.analyzer.analyze_and_route(
                self.vault_path,
                context,
                source_metadata
            )
            
            source_citation = analysis['source_citation']
            edit_plans = analysis['edits']
            
            print(f"   Created {len(edit_plans)} edit plan(s):")
            for plan in edit_plans:
                print(f"   - {plan['action'].upper()}: {plan['file']} ({plan['priority']})")
                print(f"     Content: {plan['content'][:80]}...")
                print(f"     Reason: {plan.get('reason', 'N/A')}")
            
            # STEP 2: Apply each edit
            print()
            for plan in edit_plans:
                file_path = self.vault_path / plan['file']
                action = plan['action']
                content = plan['content']
                
                print(f"📝 Processing: {plan['file']}")
                
                try:
                    if action == 'create':
                        # Create new file
                        success = self._create_file(file_path, content, plan)
                        if success:
                            results['files_created'].append(str(file_path))
                    
                    elif action in ['append', 'modify']:
                        # Append/modify existing file
                        success = self._edit_file(file_path, content, plan)
                        if success:
                            results['files_modified'].append(str(file_path))
                
                except Exception as e:
                    error_msg = f"Error processing {plan['file']}: {str(e)}"
                    print(f"   ⚠️  {error_msg}")
                    results['errors'].append(error_msg)
            
            # STEP 3: Add citation (ONE per source)
            print()
            print("📚 Adding source citation...")
            files_with_citation = self._add_citation_to_files(
                edit_plans,
                source_citation
            )
            print(f"   ✅ Added citation to {len(files_with_citation)} file(s)")
            
            # STEP 4: Validate citations are used
            print()
            print("✓ Validating citations...")
            validation_errors = self._validate_citations(edit_plans)
            if validation_errors:
                print(f"   ⚠️  Found {len(validation_errors)} validation issue(s):")
                for err in validation_errors:
                    print(f"     - {err}")
                results['errors'].extend(validation_errors)
            else:
                print("   ✅ All citations properly referenced")
            
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
            import traceback
            traceback.print_exc()
            results['errors'].append(error_msg)
            return results
    
    def _create_file(self, file_path: Path, content: str, plan: Dict) -> bool:
        """Create new file with content."""
        print(f"   Creating new file...")
        
        # Determine filename and create basic structure
        filename = file_path.stem
        
        # Build full file with header
        full_content = f"""# {filename}

{content}

## Related

"""
        
        # Write file
        write_file(file_path, full_content)
        print(f"   ✅ Created: {file_path.name}")
        
        return True
    
    def _edit_file(self, file_path: Path, content: str, plan: Dict) -> bool:
        """Edit existing file by appending content."""
        print(f"   Appending to file...")
        
        # Check if file exists
        if not file_path.exists():
            print(f"   File doesn't exist, creating instead...")
            return self._create_file(file_path, content, plan)
        
        # Read existing content
        existing = read_file(file_path)
        
        # Simple append before ## Related section
        if '## Related' in existing:
            parts = existing.split('## Related')
            new_content = f"{parts[0]}\n{content}\n\n## Related{parts[1]}"
        else:
            # Append at end
            new_content = f"{existing}\n\n{content}\n"
        
        # Write updated file
        write_file(file_path, new_content)
        print(f"   ✅ Updated: {file_path.name}")
        
        return True
    
    def _add_citation_to_files(self, edit_plans: list, source_citation: dict) -> list:
        """
        Add ONE citation to each file that references it.
        
        Returns list of files that got the citation.
        """
        files_updated = []
        
        for plan in edit_plans:
            file_path = self.vault_path / plan['file']
            
            # Check if content references [1]
            if '[1]' not in plan['content']:
                continue  # Skip if no citation reference
            
            # Get next available citation number for this file
            existing_citations = self.citations.get_citations(file_path)
            next_num = max([int(k) for k in existing_citations.keys()], default=0) + 1
            
            # If content uses [1], we need to replace with actual number
            # BUT, we designed content to use [1] assuming it's the first citation
            # So we only add if [1] is used
            
            # Add the ONE citation
            new_citation = {
                str(next_num): {
                    'platform': source_citation.get('platform', 'Manual'),
                    'timestamp': source_citation.get('timestamp', ''),
                    'url': source_citation.get('url'),
                    'quote': source_citation.get('quote', '')
                }
            }
            
            self.citations.add_citations(file_path, new_citation)
            files_updated.append(plan['file'])
            
            # Update the file content to use correct citation number if not [1]
            if next_num != 1:
                file_path_obj = self.vault_path / plan['file']
                content = read_file(file_path_obj)
                # Replace [1] with [next_num] in the newly added content
                # This is a bit hacky, but works for now
                updated = content.replace('[1]', f'[{next_num}]')
                write_file(file_path_obj, updated)
        
        return files_updated
    
    def _validate_citations(self, edit_plans: list) -> list:
        """
        Validate that citations in JSON are actually referenced in markdown.
        
        Returns list of validation errors.
        """
        errors = []
        
        for plan in edit_plans:
            file_path = self.vault_path / plan['file']
            
            # Check if content has citation markers
            has_citations = '[1]' in plan['content']
            
            if not has_citations:
                # Content doesn't reference any citations
                # This is OK for secondary files
                continue
            
            # Verify file exists and has content
            if not file_path.exists():
                errors.append(f"{plan['file']}: File doesn't exist")
                continue
            
            content = read_file(file_path)
            
            # Check if markdown actually contains citation markers
            if '[1]' not in content and not any(f'[{i}]' in content for i in range(1, 100)):
                errors.append(f"{plan['file']}: Content has no citation markers")
        
        return errors


def main():
    """CLI interface for agentic ingestion V2."""
    if len(sys.argv) < 3:
        print("Usage: python agentic_ingest_v2.py <vault_path> <context> [source_json]")
        print("\nExample:")
        print('  python agentic_ingest_v2.py ~/my-vault "Got offer from Meta"')
        print('  python agentic_ingest_v2.py ~/my-vault "Interview" \'{"platform": "Gmail", ...}\'')
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
    pipeline = AgenticIngestionPipelineV2(vault_path)
    results = pipeline.ingest(context, source_metadata)
    
    # Exit code
    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()
