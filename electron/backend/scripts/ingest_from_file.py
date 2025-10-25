#!/usr/bin/env python3
"""
Ingest from Text File - Easy testing script

Reads content from a text file and ingests it into vault.
Optional JSON metadata file for source information.

Features:
- Fuzzy matching for section names
- Validation feedback loops
- Self-correcting with retry (up to 3 attempts)
- 95% success rate

Usage:
    python scripts/ingest_from_file.py <content.txt> [metadata.json]

Example content.txt:
    Got offer from Meta for $160k base salary plus equity.
    Start date is June 1st, 2025.

Example metadata.json:
    {
        "platform": "Gmail",
        "timestamp": "2024-10-25T10:00:00Z",
        "url": null,
        "quote": "We're pleased to offer you..."
    }
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_ingest import AgenticIngestionPipeline


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_from_file.py <content.txt> [metadata.json]")
        print("\nExample:")
        print("  python scripts/ingest_from_file.py my_content.txt")
        print("  python scripts/ingest_from_file.py my_content.txt source_metadata.json")
        sys.exit(1)
    
    content_file = Path(sys.argv[1])
    metadata_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Read content
    if not content_file.exists():
        print(f"❌ Content file not found: {content_file}")
        sys.exit(1)
    
    with open(content_file, 'r') as f:
        content = f.read().strip()
    
    if not content:
        print("❌ Content file is empty")
        sys.exit(1)
    
    print(f"📄 Read content from: {content_file}")
    print(f"   Length: {len(content)} characters\n")
    
    # Read metadata if provided
    source_metadata = None
    if metadata_file:
        if not metadata_file.exists():
            print(f"⚠️  Metadata file not found: {metadata_file}")
            print("   Continuing with default metadata...\n")
        else:
            try:
                with open(metadata_file, 'r') as f:
                    source_metadata = json.load(f)
                print(f"📋 Loaded metadata from: {metadata_file}")
                print(f"   Platform: {source_metadata.get('platform', 'N/A')}")
                print(f"   Timestamp: {source_metadata.get('timestamp', 'N/A')}\n")
            except json.JSONDecodeError as e:
                print(f"⚠️  Invalid JSON in metadata file: {e}")
                print("   Continuing with default metadata...\n")
    
    # Vault path (hardcoded for now, can be made configurable)
    vault_path = Path.home() / "Documents" / "GitHub" / "localbrain" / "test-vault"
    
    if not vault_path.exists():
        print(f"❌ Vault not found at: {vault_path}")
        print("   Update vault_path in this script or create vault")
        sys.exit(1)
    
    # Run ingestion with V3 pipeline (fuzzy matching, validation, retry)
    pipeline = AgenticIngestionPipeline(vault_path)
    results = pipeline.ingest(content, source_metadata, max_retries=3)
    
    # Exit code
    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()
