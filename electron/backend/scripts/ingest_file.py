import chromadb
import sys
import os
import json
import re
from datetime import datetime
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import anthropic

def get_llm_analysis(content, api_key):
    """
    Uses an LLM to analyze the content and return a summary, filename, and description.
    """
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in .env file.")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Analyze the following document and return a JSON object with three keys:
1.  `summary`: A concise, one-paragraph summary of the document.
2.  `filename`: A descriptive, snake_case filename (without the .md extension) that categorizes this document. Example: 'nvidia_internship_offer'.
3.  `description`: A brief, one-sentence description for a citation, explaining what the source is.

Here is the document:

---
{content}
---

Respond with only the JSON object.
"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        ).content[0].text
        
        # Clean up the response to get only the JSON
        json_str = message[message.find('{'):message.rfind('}') + 1]
        return json.loads(json_str)
    except Exception as e:
        print(f"Error during LLM analysis: {e}")
        return None

def chunk_text(text, chunk_size=1000, overlap=200):
    """Splits text into overlapping chunks."""
    # A simple paragraph-based chunking strategy
    paragraphs = re.split(r'\n\n+', text)
    chunks = []
    current_chunk = ""
    for p in paragraphs:
        if len(current_chunk) + len(p) + 2 > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = p
        else:
            current_chunk += "\n\n" + p
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def ingest_file(file_path, vault_path):
    """
    Ingests a file into the LocalBrain vault using an LLM-powered pipeline.
    """
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)

    # 1. Read the source file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # 2. Get LLM Analysis
    analysis = get_llm_analysis(content, os.getenv("ANTHROPIC_API_KEY"))
    if not analysis:
        return

    summary = analysis.get('summary', 'No summary available.')
    filename = analysis.get('filename', 'uncategorized')
    description = analysis.get('description', 'No description available.')
    
    # Determine file paths based on LLM analysis
    md_filename = f"{filename}.md"
    json_filename = f"{filename}.json"
    # For simplicity, placing it in the 'personal' folder. A more advanced router could place it elsewhere.
    dest_md_path = os.path.join(vault_path, 'personal', md_filename)
    dest_json_path = os.path.join(vault_path, 'personal', json_filename)

    print(f"LLM suggested filename: {md_filename}")

    # 3. Update Citation JSON
    citations = {}
    if os.path.exists(dest_json_path):
        with open(dest_json_path, 'r') as f:
            citations = json.load(f)
    next_citation_num = str(max([int(k) for k in citations.keys()] + [0]) + 1)
    citations[next_citation_num] = {
        "platform": "File Ingestion",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "description": description,
        "url": file_path, # Using the original file path as the URL
        "quote": (summary[:150] + '...') if len(summary) > 150 else summary
    }
    with open(dest_json_path, 'w') as f:
        json.dump(citations, f, indent=2)

    # 4. Update Markdown File
    with open(dest_md_path, 'a') as f:
        f.write(f"\n\n### Summary (from {os.path.basename(file_path)}) [{next_citation_num}]\n\n{summary}")
    
    print(f"Updated {md_filename} with summary and citation.")

    # 5. Chunk content and ingest into ChromaDB
    chunks = chunk_text(content)
    print(f"Split content into {len(chunks)} chunks.")

    try:
        client = chromadb.CloudClient(api_key=os.getenv("CHROMA_API_KEY"), tenant=os.getenv("CHROMA_TENANT"), database=os.getenv("CHROMA_DATABASE"))
        model = SentenceTransformer('all-MiniLM-L6-v2')
        collection = client.get_or_create_collection(name="document_chunks")

        # Create IDs for each chunk
        chunk_ids = [f"{file_path}_{i}" for i in range(len(chunks))]
        
        collection.add(
            embeddings=model.encode(chunks).tolist(),
            documents=chunks,
            metadatas=[{"source_file": file_path, "citation_id": next_citation_num, "chunk_index": i} for i in range(len(chunks))],
            ids=chunk_ids
        )
        print(f"Successfully ingested {len(chunks)} chunks into ChromaDB.")
    except Exception as e:
        print(f"Could not ingest chunks into ChromaDB: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python ingest_file.py <file_to_ingest_path> <vault_path>")
    else:
        ingest_file(sys.argv[1], sys.argv[2])