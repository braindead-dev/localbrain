#!/usr/bin/env python3
"""
Test LocalBrain retrieval on LongMemEval - one question at a time with logging.

Uses the daemon's /protocol/search endpoint (which uses Haiku 4.5).
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
import time
import requests


def test_retrieval(data_file, vault_path, limit=None):
    """
    Test retrieval on LongMemEval questions one by one.
    
    Args:
        data_file: Path to longmemeval JSON file
        vault_path: Path to vault
        limit: Optional limit on number of questions
    """
    # Setup logging to file
    log_file = open('longmemeval_test/retrieval_test.log', 'w', buffering=1)
    
    def log(msg):
        """Print to both stdout and file."""
        print(msg)
        print(msg, file=log_file)
        log_file.flush()
    
    log(f"\n{'='*70}")
    log("LONGMEMEVAL RETRIEVAL TEST")
    log(f"{'='*70}")
    log(f"📂 Data: {data_file}")
    log(f"🗂️  Vault: {vault_path}")
    
    # Load data
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    if limit:
        data = data[:limit]
        log(f"⚠️  Limited to {limit} questions")
    
    log(f"📊 Total questions: {len(data)}")
    log(f"{'='*70}\n")
    
    # Daemon URL
    daemon_url = "http://localhost:8765"
    
    predictions = []
    stats = {
        'total': len(data),
        'contexts_found': 0,
        'no_contexts': 0,
        'errors': 0,
        'total_search_time': 0
    }
    
    start_time = time.time()
    
    # Process each question
    for i, item in enumerate(data, 1):
        question_id = item['question_id']
        question_type = item['question_type']
        question = item['question']
        answer = item['answer']
        
        log(f"\n{'─'*70}")
        log(f"[{i}/{len(data)}] {question_id} ({question_type})")
        log(f"{'─'*70}")
        log(f"Q: {question}")
        log(f"Expected: {answer}")
        
        # Call daemon search endpoint (uses Haiku 4.5)
        search_start = time.time()
        try:
            log(f"\n🔍 Searching via daemon...")
            
            response = requests.post(
                f"{daemon_url}/protocol/search",
                json={'q': question},  # JSON body, not query params
                timeout=60
            )
            
            search_time = time.time() - search_start
            stats['total_search_time'] += search_time
            
            if response.status_code == 200:
                result = response.json()
                contexts = result.get('contexts', [])
                
                if contexts:
                    stats['contexts_found'] += 1
                    log(f"✅ Found {len(contexts)} contexts ({search_time:.1f}s)")
                    
                    # Show first context
                    first = contexts[0]
                    log(f"\n📄 Top context:")
                    log(f"   File: {first.get('file', 'unknown')}")
                    log(f"   Text: {first.get('text', '')[:200]}...")
                    
                    # Use first context as answer for now
                    # TODO: Add answer generation to daemon endpoint
                    hypothesis = f"Based on the context: {first.get('text', '')[:200]}"
                    log(f"\n💭 Using context as answer")
                    
                    predictions.append({
                        'question_id': question_id,
                        'hypothesis': hypothesis,
                        'contexts_count': len(contexts),
                        'search_time': search_time
                    })
                else:
                    stats['no_contexts'] += 1
                    log(f"⚠️  No contexts found ({search_time:.1f}s)")
                    
                    predictions.append({
                        'question_id': question_id,
                        'hypothesis': "I don't have information to answer this question.",
                        'contexts_count': 0,
                        'search_time': search_time
                    })
            else:
                stats['errors'] += 1
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                log(f"❌ Daemon error: {error_msg}")
                
                predictions.append({
                    'question_id': question_id,
                    'hypothesis': "Error processing question.",
                    'contexts_count': 0,
                    'error': error_msg
                })
        
        except Exception as e:
            stats['errors'] += 1
            log(f"❌ Exception: {e}")
            
            predictions.append({
                'question_id': question_id,
                'hypothesis': "Error processing question.",
                'contexts_count': 0,
                'error': str(e)
            })
        
        # Progress update
        elapsed = time.time() - start_time
        progress = (i / len(data)) * 100
        remaining = len(data) - i
        if i > 0:
            avg_time = elapsed / i
            eta = avg_time * remaining / 60
        else:
            eta = 0
        
        log(f"\n📊 PROGRESS: {progress:.1f}% ({i}/{len(data)})")
        log(f"   Contexts found: {stats['contexts_found']}")
        log(f"   No contexts: {stats['no_contexts']}")
        log(f"   Errors: {stats['errors']}")
        log(f"   Elapsed: {elapsed/60:.1f} mins")
        log(f"   ETA: {eta:.1f} mins")
    
    # Final stats
    total_elapsed = time.time() - start_time
    
    log(f"\n{'='*70}")
    log("TEST COMPLETE")
    log(f"{'='*70}")
    log(f"Total questions: {stats['total']}")
    log(f"Contexts found: {stats['contexts_found']}")
    log(f"No contexts: {stats['no_contexts']}")
    log(f"Errors: {stats['errors']}")
    log(f"Retrieval rate: {stats['contexts_found']/stats['total']*100:.1f}%")
    log(f"Avg time per question: {stats['total_search_time']/stats['total']:.2f}s")
    log(f"Total time: {total_elapsed/60:.1f} mins")
    log(f"{'='*70}\n")
    
    # Save predictions
    output_file = 'longmemeval_test/predictions.jsonl'
    with open(output_file, 'w') as f:
        for pred in predictions:
            f.write(json.dumps({
                'question_id': pred['question_id'],
                'hypothesis': pred['hypothesis']
            }) + '\n')
    
    log(f"📊 Predictions saved to: {output_file}")
    log(f"\n🔍 To evaluate with LongMemEval's script:")
    log(f"  cd /Users/henry/Documents/GitHub/LongMemEval")
    log(f"  python src/evaluation/evaluate_qa.py gpt-4o-mini \\")
    log(f"    /Users/henry/Documents/GitHub/localbrain/electron/backend/{output_file} \\")
    log(f"    /Users/henry/Documents/GitHub/localbrain/electron/backend/longmemeval_test/longmemeval_oracle.json")
    log("")
    
    log_file.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('data_file')
    parser.add_argument('--vault', required=True)
    parser.add_argument('--limit', type=int)
    
    args = parser.parse_args()
    
    test_retrieval(args.data_file, Path(args.vault), limit=args.limit)
