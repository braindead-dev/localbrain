#!/usr/bin/env python3
"""
Evaluate LocalBrain retrieval on LongMemEval questions.

This script:
1. Loads LongMemEval questions
2. Searches vault using our agentic search
3. Compares retrieved contexts to ground truth
4. Computes metrics
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment
dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_search import Search


def evaluate_retrieval(data_file, vault_path, limit=None):
    """
    Evaluate retrieval on LongMemEval.
    
    Args:
        data_file: Path to longmemeval JSON file
        vault_path: Path to vault
        limit: Optional limit on number of questions
        
    Returns:
        Results dict with metrics
    """
    print(f"📂 Loading data from {data_file}")
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    if limit:
        data = data[:limit]
        print(f"⚠️  Limited to {limit} questions for testing")
    
    print(f"📊 Total questions: {len(data)}")
    print(f"🗂️  Vault path: {vault_path}")
    print()
    
    # Initialize searcher
    searcher = Search(vault_path)
    
    results = {
        'total_questions': len(data),
        'questions_answered': 0,
        'questions_failed': 0,
        'total_search_time': 0,
        'predictions': []
    }
    
    # Process each question
    for i, item in enumerate(data, 1):
        question_id = item['question_id']
        question_type = item['question_type']
        question = item['question']
        answer = item['answer']
        answer_session_ids = item.get('answer_session_ids', [])
        
        print(f"[{i}/{len(data)}] {question_id} ({question_type})")
        print(f"  Q: {question[:100]}...")
        print(f"  Expected: {answer}")
        
        # Search vault
        start_time = time.time()
        try:
            search_result = searcher.search(question)
            search_time = time.time() - start_time
            results['total_search_time'] += search_time
            
            if search_result.get('success'):
                contexts = search_result.get('contexts', [])
                results['questions_answered'] += 1
                
                print(f"  ✅ Found {len(contexts)} contexts ({search_time:.1f}s)")
                
                # Show first context
                if contexts:
                    first = contexts[0]
                    print(f"     File: {first['file']}")
                    print(f"     Text: {first['text'][:150]}...")
                
                # Save prediction
                prediction = {
                    'question_id': question_id,
                    'question': question,
                    'expected_answer': answer,
                    'contexts': contexts,
                    'search_time': search_time,
                    'num_contexts': len(contexts)
                }
                results['predictions'].append(prediction)
                
            else:
                results['questions_failed'] += 1
                error = search_result.get('error', 'Unknown error')
                print(f"  ❌ Search failed: {error}")
                
                results['predictions'].append({
                    'question_id': question_id,
                    'question': question,
                    'expected_answer': answer,
                    'contexts': [],
                    'error': error,
                    'search_time': 0,
                    'num_contexts': 0
                })
        
        except Exception as e:
            results['questions_failed'] += 1
            print(f"  ❌ Error: {e}")
            
            results['predictions'].append({
                'question_id': question_id,
                'question': question,
                'expected_answer': answer,
                'contexts': [],
                'error': str(e),
                'search_time': 0,
                'num_contexts': 0
            })
        
        print()
    
    # Calculate metrics
    results['avg_search_time'] = results['total_search_time'] / len(data) if data else 0
    results['success_rate'] = results['questions_answered'] / len(data) * 100 if data else 0
    
    return results


def print_results(results):
    """Print evaluation results."""
    print("="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print(f"Total questions: {results['total_questions']}")
    print(f"Questions answered: {results['questions_answered']}")
    print(f"Questions failed: {results['questions_failed']}")
    print(f"Success rate: {results['success_rate']:.1f}%")
    print(f"Avg search time: {results['avg_search_time']:.2f}s")
    print()
    
    # Distribution of contexts found
    context_counts = [p['num_contexts'] for p in results['predictions']]
    if context_counts:
        print(f"Contexts found per question:")
        print(f"  Min: {min(context_counts)}")
        print(f"  Max: {max(context_counts)}")
        print(f"  Avg: {sum(context_counts)/len(context_counts):.1f}")
    
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate retrieval on LongMemEval')
    parser.add_argument('data_file', help='Path to longmemeval JSON file')
    parser.add_argument('--vault', required=True, help='Vault path')
    parser.add_argument('--limit', type=int, help='Limit number of questions')
    parser.add_argument('--output', default='retrieval_results.json', help='Output file')
    
    args = parser.parse_args()
    
    # Run evaluation
    results = evaluate_retrieval(args.data_file, Path(args.vault), limit=args.limit)
    
    # Print results
    print_results(results)
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📊 Results saved to {args.output}")
