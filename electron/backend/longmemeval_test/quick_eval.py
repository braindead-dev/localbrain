#!/usr/bin/env python3
"""Quick eval on first 20 questions to test improved prompt."""

import json
import requests
import time
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

# Load env
load_dotenv(Path(__file__).parent.parent / '.env')

# Setup
daemon_url = "http://localhost:8765"
client = Anthropic()

# Load data - just first 20
with open('longmemeval_test/longmemeval_oracle.json') as f:
    data = json.load(f)[:20]

predictions = []

for i, item in enumerate(data, 1):
    qid = item['question_id']
    question = item['question']
    
    print(f"[{i}/20] {qid}")
    print(f"Q: {question}")
    
    # Call daemon
    try:
        resp = requests.post(f"{daemon_url}/protocol/search", json={'q': question}, timeout=60)
        
        if resp.status_code == 200:
            result = resp.json()
            contexts = result.get('contexts', [])
            
            if contexts:
                print(f"✅ {len(contexts)} contexts")
                
                # Generate answer from contexts
                context_text = "\n\n".join([f"{c['file']}:\n{c['text']}" for c in contexts[:3]])
                
                answer_resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=200,
                    messages=[{
                        "role": "user",
                        "content": f"""Extract the answer from the context below. State facts directly from the text.

Context:
{context_text}

Question: {question}

Instructions:
1. Find relevant dates, names, or facts in context
2. Compare them if needed
3. State the answer directly - no hedging
4. If truly insufficient info, say "Insufficient information" (rare)

Answer (be direct):"""
                    }]
                )
                
                hypothesis = answer_resp.content[0].text.strip()
                print(f"A: {hypothesis[:100]}...")
                
                predictions.append({'question_id': qid, 'hypothesis': hypothesis})
            else:
                print("⚠️  No contexts")
                predictions.append({'question_id': qid, 'hypothesis': "I don't have information to answer this."})
        else:
            print(f"❌ Error: {resp.status_code}")
            predictions.append({'question_id': qid, 'hypothesis': "Error."})
    
    except Exception as e:
        print(f"❌ {e}")
        predictions.append({'question_id': qid, 'hypothesis': "Error."})
    
    print("")

# Save
with open('longmemeval_test/predictions_quick.jsonl', 'w') as f:
    for p in predictions:
        f.write(json.dumps(p) + '\n')

print(f"\n✅ Saved {len(predictions)} predictions to predictions_quick.jsonl")
print("\nRunning evaluation...")

# Run evaluator
import subprocess
result = subprocess.run([
    'python', 
    '/Users/henry/Documents/GitHub/LongMemEval/src/evaluation/evaluate_qa.py',
    'gpt-4o-mini',
    'longmemeval_test/predictions_quick.jsonl',
    'longmemeval_test/longmemeval_oracle.json'
], capture_output=True, text=True, cwd='/Users/henry/Documents/GitHub/LongMemEval')

print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr)
