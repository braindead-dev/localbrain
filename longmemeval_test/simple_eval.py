#!/usr/bin/env python3
"""Simple eval - use daemon as-is, generate answers from contexts."""

import json
import requests
import time
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

# Load env
load_dotenv(Path(__file__).parent.parent / '.env')

# Setup logging
log_file = open('longmemeval_test/eval.log', 'w', buffering=1)

def log(msg):
    print(msg)
    print(msg, file=log_file)
    log_file.flush()

# Setup
daemon_url = "http://localhost:8765"
client = Anthropic()

# Load data
with open('longmemeval_test/longmemeval_oracle.json') as f:
    data = json.load(f)[:50]  # First 50

predictions = []

for i, item in enumerate(data, 1):
    qid = item['question_id']
    question = item['question']
    
    log(f"[{i}/50] {qid}")
    log(f"Q: {question}")
    
    # Call daemon
    try:
        resp = requests.post(f"{daemon_url}/protocol/search", json={'q': question}, timeout=60)
        
        if resp.status_code == 200:
            result = resp.json()
            contexts = result.get('contexts', [])
            
            if contexts:
                log(f"✅ {len(contexts)} contexts")
                
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
                log(f"A: {hypothesis[:100]}...")
                
                predictions.append({'question_id': qid, 'hypothesis': hypothesis})
            else:
                log("⚠️  No contexts")
                predictions.append({'question_id': qid, 'hypothesis': "I don't have information to answer this."})
        else:
            log(f"❌ Error: {resp.status_code}")
            predictions.append({'question_id': qid, 'hypothesis': "Error."})
    
    except Exception as e:
        log(f"❌ {e}")
        predictions.append({'question_id': qid, 'hypothesis': "Error."})
    
    log("")

# Save
with open('longmemeval_test/predictions.jsonl', 'w') as f:
    for p in predictions:
        f.write(json.dumps(p) + '\n')

log(f"\n✅ Saved {len(predictions)} predictions")
log("\nTo evaluate:")
log("cd /Users/henry/Documents/GitHub/LongMemEval")
log("python src/evaluation/evaluate_qa.py gpt-4o-mini \\")
log("  /Users/henry/Documents/GitHub/localbrain/electron/backend/longmemeval_test/predictions.jsonl \\")
log("  /Users/henry/Documents/GitHub/localbrain/electron/backend/longmemeval_test/longmemeval_oracle.json")

log_file.close()
