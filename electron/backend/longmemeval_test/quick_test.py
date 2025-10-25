#!/usr/bin/env python3
"""Quick test: Ingest 50 questions with new prompts, then test search."""

import json
import requests
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from bulk_ingest import BulkIngestionPipeline

print("=" * 70)
print("QUICK TEST: New Prompts")
print("=" * 70)

# Load first 50 questions
with open('longmemeval_test/longmemeval_oracle.json') as f:
    data = json.load(f)[:50]

print(f"\n📊 Testing with {len(data)} questions")

# Convert to items
items = []
for item in data:
    for sess, sid, sdate in zip(item['haystack_sessions'], item['haystack_session_ids'], item['haystack_dates']):
        text_lines = [f"Chat Session {sid}", f"Date: {sdate}", ""]
        for turn in sess:
            text_lines.append(f"{turn['role'].capitalize()}: {turn['content']}")
            text_lines.append("")
        
        items.append({
            'text': '\n'.join(text_lines),
            'metadata': {
                'platform': 'LongMemEval',
                'timestamp': sdate,
                'url': f'longmemeval://{item["question_id"]}/{sid}',
                'note': f'Session {sid}'
            }
        })

print(f"📝 Total sessions: {len(items)}")

# Ingest
print("\n🚀 Starting ingestion with NEW prompts...")
pipeline = BulkIngestionPipeline(Path('longmemeval_test/test-vault'))
result = pipeline.bulk_ingest(items, batch_size=10)

if result['success']:
    stats = result['stats']
    print(f"\n✅ Ingestion complete!")
    print(f"   Successful: {stats['successful']}/{stats['total_items']}")
    print(f"   Files created: {stats['files_created']}")
    print(f"   Files updated: {stats['files_updated']}")
else:
    print(f"\n❌ Ingestion failed: {result.get('error')}")
    sys.exit(1)

# Check folder structure
print("\n📁 Folder structure:")
from subprocess import run
result = run(['find', 'longmemeval_test/test-vault', '-type', 'd', '-maxdepth', 2], 
             capture_output=True, text=True)
for line in sorted(result.stdout.strip().split('\n')[:20]):
    if line:
        print(f"   {line}")

# Test search on a known question
print("\n🔍 Testing search...")
test_question = "Which device did I get first, Samsung Galaxy S22 or Dell XPS 13?"
print(f"Q: {test_question}")

response = requests.post(
    'http://localhost:8765/protocol/search',
    json={'q': test_question},
    timeout=60
)

if response.status_code == 200:
    result = response.json()
    contexts = result.get('contexts', [])
    print(f"✅ Found {len(contexts)} contexts")
    if contexts:
        first = contexts[0]
        print(f"\nTop context:")
        print(f"  File: {first.get('file')}")
        print(f"  Text: {first.get('text')[:200]}...")
    else:
        print("⚠️  No contexts found")
else:
    print(f"❌ Search failed: {response.status_code}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
