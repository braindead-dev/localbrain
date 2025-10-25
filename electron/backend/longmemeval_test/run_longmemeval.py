#!/usr/bin/env python3
"""
Run LocalBrain on LongMemEval benchmark.

This script:
1. Loads LongMemEval questions
2. For each question:
   - Searches vault using agentic search
   - Gets answer from LLM based on retrieved contexts
3. Saves predictions in LongMemEval format
4. Can be evaluated using their evaluate_qa.py script
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
import time
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment
dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_search import Search


def answer_question(question, contexts, client, model="claude-3-5-sonnet-20241022"):
    """
    Answer question based on retrieved contexts.
    
    Args:
        question: The question to answer
        contexts: List of retrieved context dicts
        client: Anthropic client
        model: Model to use for answering
        
    Returns:
        Answer string
    """
    if not contexts:
        return "I don't have enough information to answer this question."
    
    # Build context string
    context_str = "\n\n".join([
        f"From {ctx['file']}:\n{ctx['text']}"
        for ctx in contexts[:5]  # Use top 5 contexts
    ])
    
    # Build prompt
    prompt = f"""You are answering a question based on personal context from a knowledge vault.

CONTEXT:
{context_str}

QUESTION: {question}

Please answer the question based ONLY on the information provided in the context above. Be direct and concise. If the context doesn't contain enough information to answer the question, say so.

ANSWER:"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Error generating answer: {e}"


def run_longmemeval(data_file, vault_path, output_file, limit=None):
    """
    Run LocalBrain on LongMemEval.
    
    Args:
        data_file: Path to longmemeval JSON file
        vault_path: Path to vault
        output_file: Output file for predictions
        limit: Optional limit on number of questions
        
    Returns:
        Results dict
    """
    print(f"\n{'='*70}")
    print("LOCALBRAIN ON LONGMEMEVAL")
    print(f"{'='*70}")
    print(f"📂 Data: {data_file}")
    print(f"🗂️  Vault: {vault_path}")
    print(f"📝 Output: {output_file}")
    
    # Load data
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    if limit:
        data = data[:limit]
        print(f"⚠️  Limited to {limit} questions")
    
    print(f"📊 Total questions: {len(data)}")
    print(f"{'='*70}\n")
    
    # Initialize
    searcher = Search(vault_path)
    client = Anthropic()
    
    predictions = []
    stats = {
        'total': len(data),
        'successful_search': 0,
        'failed_search': 0,
        'total_search_time': 0,
        'total_answer_time': 0
    }
    
    # Process each question
    for i, item in enumerate(data, 1):
        question_id = item['question_id']
        question_type = item['question_type']
        question = item['question']
        
        print(f"[{i}/{len(data)}] {question_id} ({question_type})")
        print(f"  Q: {question}")
        
        # Search vault
        search_start = time.time()
        try:
            search_result = searcher.search(question)
            search_time = time.time() - search_start
            stats['total_search_time'] += search_time
            
            if search_result.get('success'):
                contexts = search_result.get('contexts', [])
                stats['successful_search'] += 1
                
                print(f"  ✅ Search: {len(contexts)} contexts ({search_time:.1f}s)")
                
                # Generate answer
                answer_start = time.time()
                answer = answer_question(question, contexts, client)
                answer_time = time.time() - answer_start
                stats['total_answer_time'] += answer_time
                
                print(f"  ✅ Answer: {answer[:100]}... ({answer_time:.1f}s)")
                
                predictions.append({
                    'question_id': question_id,
                    'hypothesis': answer
                })
            else:
                stats['failed_search'] += 1
                error = search_result.get('error', 'Unknown error')
                print(f"  ❌ Search failed: {error}")
                
                predictions.append({
                    'question_id': question_id,
                    'hypothesis': "I don't have information to answer this question."
                })
        
        except Exception as e:
            stats['failed_search'] += 1
            print(f"  ❌ Error: {e}")
            
            predictions.append({
                'question_id': question_id,
                'hypothesis': "Error processing question."
            })
        
        print()
    
    # Calculate stats
    stats['avg_search_time'] = stats['total_search_time'] / len(data) if data else 0
    stats['avg_answer_time'] = stats['total_answer_time'] / len(data) if data else 0
    stats['search_success_rate'] = (stats['successful_search'] / len(data)) * 100 if data else 0
    
    # Save predictions
    with open(output_file, 'w') as f:
        for pred in predictions:
            f.write(json.dumps(pred) + '\n')
    
    print(f"{'='*70}")
    print("COMPLETED")
    print(f"{'='*70}")
    print(f"Total questions: {stats['total']}")
    print(f"Successful searches: {stats['successful_search']}")
    print(f"Failed searches: {stats['failed_search']}")
    print(f"Search success rate: {stats['search_success_rate']:.1f}%")
    print(f"Avg search time: {stats['avg_search_time']:.2f}s")
    print(f"Avg answer time: {stats['avg_answer_time']:.2f}s")
    print(f"{'='*70}\n")
    
    print(f"📊 Predictions saved to: {output_file}")
    print(f"\n🔍 To evaluate, run:")
    print(f"  cd /Users/henry/Documents/GitHub/LongMemEval")
    print(f"  python src/evaluation/evaluate_qa.py gpt-4o-mini {output_file} {data_file}")
    print()
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run LocalBrain on LongMemEval')
    parser.add_argument('data_file', help='Path to longmemeval oracle JSON')
    parser.add_argument('--vault', required=True, help='Vault path')
    parser.add_argument('--limit', type=int, help='Limit number of questions')
    parser.add_argument('--output', default='longmemeval_test/predictions.jsonl', help='Output file')
    
    args = parser.parse_args()
    
    # Run benchmark
    run_longmemeval(args.data_file, Path(args.vault), args.output, limit=args.limit)
