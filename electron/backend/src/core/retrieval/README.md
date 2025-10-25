# Retrieval Engine

Handles search queries and returns relevant information from stored data. Provides semantic search, context-aware ranking, and multi-format result generation.

## Core Responsibilities

- **Query Processing**: Parse and understand natural language queries
- **Semantic Search**: Vector similarity matching across all content
- **Result Ranking**: Context-aware ordering of search results
- **Multi-Query Support**: Handle complex queries with multiple components
- **Response Generation**: Format results for frontend consumption
- **Performance Optimization**: Fast retrieval with caching strategies

## Query Processing

**Natural Language Understanding:**
- Intent recognition and query classification
- Entity extraction and context identification
- Query expansion and synonym handling
- Multi-language support preparation

**Search Types:**
- **Semantic Search**: Meaning-based similarity matching
- **Keyword Search**: Exact term matching with agentic syntax
- **Hybrid Search**: Combined semantic and keyword approaches
- **Contextual Search**: Results based on user history and preferences

## Result Ranking & Generation

**Ranking Factors:**
- **Relevance Score**: Vector similarity and semantic matching
- **Recency**: Recent content weighted higher
- **Source Quality**: Verified sources ranked above unverified
- **Context Fit**: Results matching user query intent
- **Diversity**: Varied sources and content types

**Response Formats:**
- **File Results**: Direct file and line references
- **Text Snippets**: Relevant excerpts with context
- **Natural Language**: Generated responses when appropriate
- **Structured Data**: Formatted results with metadata

## Database Integration

**Vector Search:**
- Embed query in same space as document chunks
- Cosine similarity and distance calculations
- Metadata filtering and faceting
- Hybrid search combining vector and keyword results

**Performance Features:**
- **Caching**: Frequently accessed results and embeddings
- **Indexing**: Optimized data structures for fast retrieval
- **Batch Processing**: Handle multiple queries efficiently
- **Incremental Updates**: Real-time index updates on content changes

## Frontend Integration

**API Endpoints:**
- **Search Queries**: Accept search requests from UI
- **Result Streaming**: Progressive result delivery
- **Query Suggestions**: Auto-complete and query expansion
- **Search History**: User query tracking and analytics

**Result Formatting:**
- **Highlighting**: Relevant terms and phrases
- **Context Windows**: Surrounding content for snippets
- **Source Attribution**: Clear citation of result sources
- **Action Links**: Direct links to open files or take actions

## Protocol Handler Integration

**localbrain:// Search Commands:**
- Parse protocol URLs into search queries
- Route search requests to appropriate engines
- Format responses for protocol return values
- Handle search-specific protocol parameters

## Advanced Features

**Query Understanding:**
- Multi-intent query parsing
- Temporal queries (e.g., "last week", "before 2023")
- Comparative queries ("better than", "similar to")
- Negative queries (exclude certain terms or concepts)

**Personalization:**
- User behavior learning
- Query history analysis
- Content preference modeling
- Adaptive ranking based on interaction patterns

## Retrieval Process Architecture

**Complete Flow (Query → Results):**

```
1. Query Reception
   ↓
2. Query Preprocessing
   ↓
3. Embedding Generation
   ↓
4. Vector Search
   ↓
5. Metadata Filtering
   ↓
6. Result Ranking
   ↓
7. Response Formatting
   ↓
8. Return to User
```

### Detailed Process Breakdown

**1. Query Reception** (`src/core/retrieval/query_handler.py`)
- Receive query from protocol handler or MCP API
- Parse query parameters (filters, limits, etc.)
- Validate request and check permissions

**2. Query Preprocessing** (`src/core/retrieval/preprocessor.py`)
- Clean and normalize query text
- Expand abbreviations and synonyms
- Extract intent and entities
- Handle multi-part queries

**3. Embedding Generation** (`src/core/retrieval/embedder.py`)
- Generate embedding vector for query
- Use same model as document chunks (consistency)
- Batch process for multiple queries
- Cache frequent queries

**4. Vector Search** (`src/database/embeddings/vector_search.py`)
- Cosine similarity search against chunk embeddings
- Return top K most similar chunks (K=50-100)
- Include similarity scores
- Filter by minimum similarity threshold

**5. Metadata Filtering** (`src/core/retrieval/filter.py`)
- Apply user filters (date range, file type, source)
- Respect bridge access permissions
- Filter by vault directory scope
- Exclude archived or deleted content

**6. Result Ranking** (`src/core/retrieval/ranker.py`)
- Multi-factor scoring algorithm:
  - Base: Vector similarity score
  - Recency: Newer content ranked higher
  - Source quality: Verified sources boosted
  - Context fit: File-level relevance
  - Diversity: Avoid redundant results
- Combine scores with learned weights
- Re-rank top results

**7. Response Formatting** (`src/core/retrieval/formatter.py`)
- Group chunks by file
- Extract surrounding context for snippets
- Generate file summaries if needed
- Add metadata (file path, timestamp, source)
- Highlight matching terms
- Generate natural language response (optional)

**8. Return to User**
- Send formatted results via protocol response
- Log query for analytics and audit
- Update query history and suggestions
- Trigger related content recommendations

### Code Organization

```
src/core/retrieval/
├── query_handler.py      # Entry point, request routing
├── preprocessor.py       # Query cleaning and expansion
├── embedder.py           # Embedding generation
├── filter.py             # Metadata and permission filtering
├── ranker.py             # Multi-factor result ranking
├── formatter.py          # Response formatting
├── cache.py              # Query and result caching
└── models.py             # Data models and types
```

### Search Types

**Semantic Search** (`search()`)
- Natural language query
- Vector similarity matching
- Returns relevant chunks with context
- Best for: "find information about X"

**Agentic Search** (`search_agentic()`)
- Structured query with filters
- Keyword matching + metadata filters
- Exact term matching when needed
- Best for: "emails from X in the last 7 days"

**Hybrid Search** (automatic)
- Combines semantic and keyword approaches
- Used when query has both concepts and specific terms
- Balances precision and recall

### Performance Optimizations

**Query Caching:**
- Cache embeddings for frequent queries
- Cache results for common searches
- Invalidate on content updates

**Precomputation:**
- Precompute file-level summaries
- Index frequently accessed chunks
- Maintain popularity scores

**Parallel Processing:**
- Parallel vector search across shards
- Concurrent metadata filtering
- Async result formatting

### Example Query Flow

```python
# Input
query = "internship application emails from last month"

# Step 1-2: Reception and preprocessing
processed_query = "internship application communication recent"
filters = {"source": "gmail", "date_range": "last_30_days"}

# Step 3: Embedding
query_vector = embed_model.encode(processed_query)  # [768-dim vector]

# Step 4: Vector search
chunks = vector_db.search(query_vector, top_k=100)
# Returns: [
#   {chunk_id: "abc123", similarity: 0.89, text: "Applied to NVIDIA..."},
#   {chunk_id: "def456", similarity: 0.85, text: "Received rejection..."},
#   ...
# ]

# Step 5: Filter
filtered = filter_by_metadata(chunks, filters)
# Keeps only chunks from gmail in last 30 days

# Step 6: Rank
ranked = multi_factor_rank(filtered, query_vector)
# Applies recency boost, deduplicates, diversifies

# Step 7: Format
results = format_response(ranked, include_context=True)
# Groups by file, adds snippets, generates summary

# Step 8: Return
return {
  "results": results,
  "total": len(results),
  "query": processed_query,
  "took_ms": 45
}
```

## Integration Points

- **Frontend**: Receive and display search results
- **Ingestion**: Access processed content and embeddings
- **MCP Server**: Provide search tools for external integrations
- **Bridge Service**: Enforce access permissions and logging
- **Database**: Query vector stores and metadata
- **Protocol Handler**: Process `localbrain://search` commands
- **Cache Layer**: Store and retrieve frequent queries
