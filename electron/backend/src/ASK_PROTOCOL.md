# LocalBrain "Ask" Protocol Implementation

This document outlines the design and implementation for the "Ask" feature, which provides LLM-summarized answers from a user's vault instead of just returning raw search results.

## 1. Overview

The goal is to enhance the "Ask local brain" functionality. Currently, it performs a search and returns a list of relevant text chunks. The desired functionality is to take those chunks, send them to an LLM with the original query, and get a synthesized, natural-language answer, while still providing the source chunks for verification.

## 2. Architectural Decisions

The implementation was decided based on the following architectural principles:

### A. Separation of Concerns

Instead of adding the summarization logic directly into the `daemon.py` request handler, a new, dedicated module will be created: `electron/backend/src/agentic_synthesis.py`.

*   **Reasoning**: This follows the existing project pattern of separating distinct functionalities into their own files (`agentic_search.py`, `agentic_ingest.py`). It keeps the `daemon.py` file clean and focused on orchestration, while the new module can own all logic related to answer synthesis.

### B. Backward Compatibility & Endpoint Strategy

Instead of modifying the existing `/protocol/search` endpoint, a new endpoint, `/protocol/ask`, will be created.

*   **Reasoning**: The MCP (Model Context Protocol) layer and potentially other tools rely on the `/protocol/search` endpoint and its specific response format (a list of raw context chunks). Modifying it would be a breaking change. Creating a new `/protocol/ask` endpoint provides the new functionality without affecting existing integrations.

## 3. Final Implementation Plan

The implementation consists of two new components and one modification to the frontend.

### Component 1: The Synthesizer (`agentic_synthesis.py`)

A new file responsible for generating an answer from a query and context.

**File Location**: `electron/backend/src/agentic_synthesis.py`

```python
from typing import List, Dict
from utils.llm_client import LLMClient

class AnswerSynthesizer:
    def __init__(self):
        self.llm = LLMClient()

    def summarize(self, query: str, contexts: List[Dict]) -> str:
        """
        Summarizes the provided context chunks to answer the user's query.
        """
        if not contexts:
            return "I couldn't find any relevant information in your vault."

        # Combine the text from all contexts
        context_str = "\n\n---\n\n".join([ctx['text'] for ctx in contexts])

        # Create a prompt for the LLM
        prompt = f"""Based on the following context, please provide a concise answer to the user's query.

User Query: {query}

Context:
{context_str}

Answer:"""

        # Call the LLM to generate the summary
        summary = self.llm.call(prompt, system="You are a helpful assistant that answers questions based on provided context.")
        return summary
```

### Component 2: The New Endpoint (`daemon.py`)

A new `/protocol/ask` endpoint is added to `daemon.py` to orchestrate the search-and-summarize flow. The existing `/protocol/search` endpoint remains untouched.

**File Location**: `electron/backend/src/daemon.py`

```python
# Add to imports
from agentic_synthesis import AnswerSynthesizer

# This new endpoint will be added
@app.post("/protocol/ask")
async def handle_ask(request: Request):
    """
    Handles a query by searching for context and then synthesizing a
    natural language answer.
    """
    try:
        body = await request.json()
        query = body.get('q', body.get('query', ''))
        
        if not query:
            return JSONResponse(status_code=400, content={'error': 'Missing query parameter'})

        logger.info(f"🧠 Ask: {query}")

        # 1. Get contexts
        searcher = Search(VAULT_PATH)
        search_result = searcher.search(query)
        
        answer = "Could not find an answer."
        contexts = search_result.get('contexts', [])

        # 2. Synthesize answer if contexts were found
        if search_result.get('success') and contexts:
            logger.info(f"Synthesizing answer from {len(contexts)} contexts...")
            synthesizer = AnswerSynthesizer()
            answer = synthesizer.summarize(query, contexts)
            logger.info("✅ Answer synthesis complete.")

        return JSONResponse(content={
            'success': True,
            'query': query,
            'answer': answer,
            'contexts': contexts
        })

    except Exception as e:
        logger.info("Error handling ask request")
        return JSONResponse(status_code=500, content={'error': str(e)})

# The /protocol/search endpoint remains unchanged to support the MCP.
@app.post("/protocol/search")
async def handle_search(request: Request):
    # ... (existing implementation)
    pass
```

### Component 3: Frontend Update

The "Ask local brain" UI component must be updated to send its requests to the new `/protocol/ask` endpoint instead of `/protocol/search`. It should then display the `answer` field from the response, while still having access to the `contexts` for showing sources.

## 4. Data Flow

The new data flow for the "Ask" feature is as follows:

```
UI ("Ask" Feature)
       │
       │ POST /protocol/ask
       ▼
Daemon (`handle_ask`)
       │
       ├─> 1. Calls `agentic_search.search()`
       │              │
       │              └─> Returns [contexts]
       │
       ├─> 2. Calls `agentic_synthesis.summarize(query, contexts)`
       │              │
       │              └─> Returns "answer"
       │
       ▼
JSON Response { success, query, answer, contexts }
       │
       ▼
UI (Displays answer and sources)
```
