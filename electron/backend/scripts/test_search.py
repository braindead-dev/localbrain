#!/usr/bin/env python3
"""
Test natural language search.

Usage:
    python scripts/test_search.py
    python scripts/test_search.py "What was my Meta offer?"
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agentic_search import Search
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / '.env')

def main():
    # Test queries
    test_queries = [
        "What was my Meta offer?",
        "What projects did I work on?",
        "Tell me about my education"
    ]
    
    # Use custom query if provided
    if len(sys.argv) > 1:
        test_queries = [" ".join(sys.argv[1:])]
    
    # Use vault path
    vault_path = Path.home() / "Documents" / "GitHub" / "localbrain" / "my-vault"
    
    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        print("   Update vault_path in this script or set VAULT_PATH env var")
        sys.exit(1)
    
    print("="*60)
    print(f"Vault: {vault_path}")
    print("="*60)
    print()
    
    # Run searches
    searcher = Search(vault_path)
    
    for query in test_queries:
        print("="*60)
        print(f"Query: {query}")
        print("="*60)
        print()
        
        try:
            result = searcher.search(query)
            
            print()
            if result.get('success'):
                print("✅ SUCCESS")
                print(f"Iterations: {result.get('iterations', 0)}")
                print()
                print("Answer:")
                print("-" * 60)
                print(result['answer'])
                print("-" * 60)
            else:
                print("❌ FAILED")
                print(f"Error: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
        
        print()

if __name__ == "__main__":
    main()
