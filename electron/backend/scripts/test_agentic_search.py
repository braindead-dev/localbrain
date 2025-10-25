#!/usr/bin/env python3
"""
Test script for agentic search.

Usage:
    python scripts/test_agentic_search.py "What was my Meta offer?"
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agentic_search import AgenticSearch

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_agentic_search.py <query>")
        print('Example: python test_agentic_search.py "What was my Meta offer?"')
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    # Use test vault
    vault_path = Path.home() / "Documents" / "GitHub" / "localbrain" / "test-vault"
    
    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        print("   Create test vault with: python src/init_vault.py <path>")
        sys.exit(1)
    
    print("="*60)
    print(f"Query: {query}")
    print(f"Vault: {vault_path}")
    print("="*60)
    print()
    
    # Run search
    searcher = AgenticSearch(vault_path)
    result = searcher.search(query)
    
    print()
    print("="*60)
    if result.get('success'):
        print("✅ SUCCESS")
        print(f"Iterations: {result.get('iterations', 0)}")
        print()
        print("Answer:")
        print(result['answer'])
    else:
        print("❌ FAILED")
        print(f"Error: {result.get('error', 'Unknown error')}")
    print("="*60)

if __name__ == "__main__":
    main()
