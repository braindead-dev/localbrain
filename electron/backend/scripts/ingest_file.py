import chromadb
import sys
import os
import json
import re
from datetime import datetime
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import anthropic

# --- LLM Interaction Functions ---

def get_llm_file_decision(content, file_tree, api_key):
    """LLM Call #1: Decide where the content should go."""
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found.")

    client = anthropic.Anthropic(api_key=api_key)
    model_name = "claude-haiku-4-5-20251001"
    prompt = f"""You are an intelligent file system organizer for a personal knowledge base. Your task is to decide where a new piece of information should be stored.

I will provide you with the content of a new document and a list of the existing markdown files in the vault.

Based on the content, you must decide whether to:
1.  APPEND the content to one of the existing files.
2.  CREATE a new file because the content represents a new, distinct topic.

Your response MUST be a JSON object with two keys:
- `action`: either "APPEND" or "CREATE".
- `path`: The relative path for the file from the vault root (e.g., "career/internship_offers.md"). If creating, provide a new, descriptive, snake_case filename.

Here is the existing file structure:
---
{file_tree}
---

Here is the new document content:
---
{content}
---

Now, provide your decision as a JSON object.
"""
    try:
        message = client.messages.create(
            model=model_name,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        json_str = message[message.find('{'):message.rfind('}') + 1]
        return json.loads(json_str)
    except Exception as e:
        print(f"Error during file decision analysis: {e}")
        return None

def get_llm_content_generation(content, api_key):
    """LLM Call #2: Generate the summary and citations."""
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found.")

    client = anthropic.Anthropic(api_key=api_key)
    model_name = "claude-haiku-4-5-20251001"
    print(f"Using model: {model_name} for content generation.")

    prompt = f"""Analyze the following document. Your task is to create a concise summary and a corresponding set of citations for the key facts within that summary. 

Follow these steps carefully:
1.  Write a one-paragraph summary of the document.
2.  As you write the summary, whenever you state a specific fact (like a number, date, or name), insert a sequential citation marker, starting with `[1]`, then `[2]`, and so on.
3.  Create a JSON object for the citations. The keys must be the citation numbers (as strings), and the value for each key must be an object containing a single key, `quote`, with the direct quote from the original document that supports that fact.
4.  Return a single JSON object with two keys:
    a. `summary_with_citations`: The string of the summary you wrote, including the `[1]`, `[2]` markers.
    b. `citations`: The JSON object of quotes you created.

Here is the document:

---
{content}
---

Respond with only the final JSON object.
"""
    try:
        message = client.messages.create(
            model=model_name,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        json_str = message[message.find('{'):message.rfind('}') + 1]
        return json.loads(json_str)
    except Exception as e:
        print(f"Error during content generation: {e}")
        return None

def get_llm_intelligent_insertion(existing_content, new_summary, api_key):
    """LLM Call #3: Intelligently insert the new summary into the existing document."""
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found.")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""You are an expert markdown editor. Your task is to intelligently insert a new block of text into an existing markdown document.

I will provide you with the `EXISTING_DOCUMENT` and the `NEW_CONTENT` to be inserted.

Analyze the headings and structure of the `EXISTING_DOCUMENT`. Find the most contextually relevant section to place the `NEW_CONTENT`. Insert the `NEW_CONTENT` there. Do not just append to the end unless it is the only logical place. Maintain the original document's formatting and structure.

Return the **entire, updated document** as a single block of text. Do not add any commentary.

---
EXISTING_DOCUMENT:
{existing_content}
---

---
NEW_CONTENT:
{new_summary}
---

Now, provide the full, updated markdown document.
"""
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096, # Allow for larger document context
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        return message
    except Exception as e:
        print(f"Error during intelligent insertion: {e}")
        return existing_content # Fallback to old content on error

# --- Filesystem and Utility Functions ---

def list_vault_files(vault_path):
    tree = []
    for root, dirs, files in os.walk(vault_path):
        if '.localbrain' in dirs:
            dirs.remove('.localbrain')
        level = root.replace(vault_path, '').count(os.sep)
        indent = ' ' * 4 * level
        tree.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            if f.endswith('.md'):
                tree.append(f"{sub_indent}- {f}")
    return "\n".join(tree)

def chunk_text(text):
    return re.split(r'\n\n+', text)

# --- Main Ingestion Logic ---

def ingest_file(file_path, vault_path, model):
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    api_key = os.getenv("ANTHROPIC_API_KEY")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Step 1: Get LLM decision on where to store the file
    file_tree = list_vault_files(vault_path)
    file_decision = get_llm_file_decision(original_content, file_tree, api_key)
    if not file_decision or 'path' not in file_decision:
        print("LLM could not decide on a file path. Aborting.")
        return

    relative_path = file_decision['path']
    action = file_decision.get('action', 'CREATE')
    dest_md_path = os.path.join(vault_path, relative_path)
    dest_json_path = dest_md_path.replace('.md', '.json')
    os.makedirs(os.path.dirname(dest_md_path), exist_ok=True)

    print(f"LLM decided to '{action}' file: {relative_path}")

    # Step 2: Get LLM-generated summary and citations
    content_analysis = get_llm_content_generation(original_content, api_key)
    if not content_analysis or 'summary_with_citations' not in content_analysis:
        print("LLM could not generate summary. Aborting.")
        return

    summary_with_citations = content_analysis['summary_with_citations']
    new_citations = content_analysis.get('citations', {})

    # Step 3: Re-number citations and merge
    existing_citations = {}
    if os.path.exists(dest_json_path):
        with open(dest_json_path, 'r') as f:
            existing_citations = json.load(f)
    start_index = max([int(k) for k in existing_citations.keys()] + [0]) + 1
    
    renumbered_citations = {}
    sorted_new_citation_keys = sorted(new_citations.keys(), key=int)

    for old_key in sorted_new_citation_keys:
        new_key = str(start_index + int(old_key) - 1)
        summary_with_citations = summary_with_citations.replace(f'[{old_key}]', f'[{new_key}]')
        renumbered_citations[new_key] = {
            "platform": "File Ingestion",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "description": f"Source: {os.path.basename(file_path)}",
            "url": file_path,
            "quote": new_citations[old_key].get('quote', 'Quote not available.')
        }

    existing_citations.update(renumbered_citations)
    with open(dest_json_path, 'w') as f:
        json.dump(existing_citations, f, indent=2)

    # Step 4: Write content with intelligent insertion
    new_content_block = f"\n\n---\n*Source: {os.path.basename(file_path)}*\n\n{summary_with_citations}"
    
    final_markdown = ""
    if action == 'APPEND' and os.path.exists(dest_md_path):
        print("Performing intelligent insertion into existing file...")
        with open(dest_md_path, 'r') as f:
            existing_markdown = f.read()
        final_markdown = get_llm_intelligent_insertion(existing_markdown, new_content_block, api_key)
    else:
        # For CREATE action, just use the new content block
        final_markdown = new_content_block

    with open(dest_md_path, 'w') as f:
        f.write(final_markdown)

    print(f"Successfully updated {relative_path}")

    # Step 5: Chunk and embed the updated markdown file
    chunks = chunk_text(final_markdown)
    print(f"Split markdown file into {len(chunks)} chunks for embedding.")

    try:
        client = chromadb.CloudClient(api_key=os.getenv("CHROMA_API_KEY"), tenant=os.getenv("CHROMA_TENANT"), database=os.getenv("CHROMA_DATABASE"))
        collection = client.get_or_create_collection(name="markdown_notes")

        if chunks:
            chunk_ids = [f"{dest_md_path}_{i}_{datetime.utcnow().timestamp()}" for i in range(len(chunks))] # Add timestamp for uniqueness
            collection.add(
                embeddings=model.encode(chunks).tolist(),
                documents=chunks,
                metadatas=[{"source_file": dest_md_path, "chunk_index": i} for i in range(len(chunks))],
                ids=chunk_ids
            )
            print(f"Successfully ingested {len(chunks)} chunks from {relative_path} into ChromaDB.")
    except Exception as e:
        print(f"Could not ingest chunks into ChromaDB: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python ingest_file.py <file_to_ingest_path> <vault_path>")
    else:
        s_model = SentenceTransformer('all-MiniLM-L6-v2')
        ingest_file(sys.argv[1], sys.argv[2], s_model)