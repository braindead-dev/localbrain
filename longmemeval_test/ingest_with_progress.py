#!/usr/bin/env python3
"""
Ingest LongMemEval with real-time progress tracking.
"""

import json
import requests
import time
from pathlib import Path
from datetime import datetime

def ingest_with_progress(data_file, chunk_size=10, batch_size=10):
    """Ingest data in chunks with progress tracking."""
    
    # Setup logging to file
    import sys
    log_file = open('longmemeval_test/progress.log', 'w', buffering=1)
    
    def log(msg):
        """Print to both stdout and file."""
        print(msg)
        print(msg, file=log_file)
        log_file.flush()
    
    # Load data
    log(f"\n📂 Loading {data_file}")
    with open(data_file) as f:
        data = json.load(f)
    
    # Calculate totals
    total_questions = len(data)
    total_sessions = sum(len(item['haystack_sessions']) for item in data)
    total_chunks = (total_questions + chunk_size - 1) // chunk_size
    
    log(f"\n{'='*70}")
    log(f"LONGMEMEVAL BULK INGESTION")
    log(f"{'='*70}")
    log(f"Total questions: {total_questions}")
    log(f"Total sessions: {total_sessions}")
    log(f"Chunk size: {chunk_size} questions")
    log(f"Total chunks: {total_chunks}")
    log(f"Batch size: {batch_size} items per batch")
    log(f"{'='*70}\n")
    
    # Track stats
    total_success = 0
    total_failed = 0
    start_time = time.time()
    
    # Process in chunks
    for chunk_num in range(total_chunks):
        chunk_start = chunk_num * chunk_size
        chunk_end = min(chunk_start + chunk_size, total_questions)
        chunk = data[chunk_start:chunk_end]
        
        log(f"\n{'─'*70}")
        log(f"CHUNK {chunk_num + 1}/{total_chunks} | Questions {chunk_start+1}-{chunk_end}")
        log(f"{'─'*70}")
        
        # Convert to items
        items = []
        for idx, item in enumerate(chunk, 1):
            qid = item['question_id']
            qtype = item['question_type']
            sessions = item['haystack_sessions']
            session_ids = item['haystack_session_ids']
            session_dates = item['haystack_dates']
            
            log(f"  [{chunk_start + idx}] {qid} ({qtype}) - {len(sessions)} sessions")
            
            for sess, sid, sdate in zip(sessions, session_ids, session_dates):
                text_lines = [f"Chat Session {sid}", f"Date: {sdate}", ""]
                for turn in sess:
                    text_lines.append(f"{turn['role'].capitalize()}: {turn['content']}")
                    text_lines.append("")
                
                items.append({
                    'text': '\n'.join(text_lines),
                    'metadata': {
                        'platform': 'LongMemEval',
                        'timestamp': sdate,
                        'url': f'longmemeval://{qid}/{sid}',
                        'note': f'Session {sid} for {qtype} question'
                    }
                })
        
        log(f"\nTotal items in chunk: {len(items)}")
        log(f"Sending to bulk endpoint...")
        
        # Send request
        try:
            chunk_start_time = time.time()
            
            response = requests.post(
                'http://localhost:8765/protocol/bulk-ingest',
                json={'items': items, 'batch_size': batch_size},
                timeout=1200
            )
            
            chunk_elapsed = time.time() - chunk_start_time
            
            if response.status_code == 200:
                result = response.json()
                chunk_success = result.get('successful', 0)
                chunk_failed = result.get('failed', 0)
                
                total_success += chunk_success
                total_failed += chunk_failed
                
                log(f"✅ SUCCESS ({chunk_elapsed:.1f}s)")
                log(f"   Successful: {chunk_success}/{len(items)}")
                log(f"   Files created: {result.get('files_created', 0)}")
                log(f"   Files updated: {result.get('files_updated', 0)}")
            else:
                log(f"❌ HTTP {response.status_code}")
                total_failed += len(items)
        
        except Exception as e:
            log(f"❌ Error: {e}")
            total_failed += len(items)
        
        # Progress summary
        elapsed = time.time() - start_time
        progress = ((chunk_num + 1) / total_chunks) * 100
        sessions_done = total_success + total_failed
        sessions_left = total_sessions - sessions_done
        
        # Time estimates
        if sessions_done > 0:
            avg_time_per_session = elapsed / sessions_done
            eta_seconds = avg_time_per_session * sessions_left
            eta_mins = eta_seconds / 60
        else:
            eta_mins = 0
        
        log(f"\n📊 PROGRESS: {progress:.1f}% complete")
        log(f"   Sessions: {sessions_done}/{total_sessions}")
        log(f"   Elapsed: {elapsed/60:.1f} mins")
        log(f"   ETA: {eta_mins:.1f} mins")
        log(f"   Success rate: {total_success/(total_success+total_failed)*100:.1f}%")
        
        time.sleep(1)  # Brief pause
    
    # Final summary
    total_elapsed = time.time() - start_time
    
    log(f"\n{'='*70}")
    log(f"INGESTION COMPLETE")
    log(f"{'='*70}")
    log(f"Total sessions: {total_sessions}")
    log(f"Successful: {total_success}")
    log(f"Failed: {total_failed}")
    log(f"Success rate: {total_success/(total_success+total_failed)*100:.1f}%")
    log(f"Total time: {total_elapsed/60:.1f} minutes")
    log(f"{'='*70}\n")
    
    # Save results
    results = {
        'total_questions': total_questions,
        'total_sessions': total_sessions,
        'successful': total_success,
        'failed': total_failed,
        'success_rate': total_success/(total_success+total_failed)*100 if (total_success+total_failed) > 0 else 0,
        'elapsed_minutes': total_elapsed/60
    }
    
    with open('longmemeval_test/ingestion_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    log(f"📊 Results saved to longmemeval_test/ingestion_results.json\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('data_file')
    parser.add_argument('--chunk-size', type=int, default=10)
    parser.add_argument('--batch-size', type=int, default=10)
    
    args = parser.parse_args()
    
    ingest_with_progress(args.data_file, args.chunk_size, args.batch_size)
