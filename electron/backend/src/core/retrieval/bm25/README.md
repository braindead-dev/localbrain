# BM25 Retrieval

Traditional keyword-based search using the BM25 (Best Matching 25) algorithm for precise citation and source metadata retrieval in LocalBrain.

## Core Responsibilities

- **Keyword Search**: Exact term matching across citation metadata
- **Citation Discovery**: Find sources by platform, date, or content
- **Metadata Filtering**: Search and filter by citation fields
- **Ranking**: Score results by term frequency and relevance
- **Complementary Search**: Work alongside semantic search for precision

## Overview

BM25 provides **keyword-based retrieval** over JSON citation files stored in the vault. Unlike semantic search (which finds similar meanings), BM25 excels at finding exact matches, specific terms, dates, platforms, and quoted text.

**Use Cases:**
- Find all citations from a specific platform (e.g., "Gmail", "Discord")
- Search for citations within a date range
- Locate specific quotes or keywords
- Filter sources by URL patterns
- Combine multiple search criteria for precise results

## Data Source

### JSON Citation Files

BM25 searches through all JSON citation files stored alongside markdown files in the vault:

```
~/my-vault/
├── career/
│   ├── job-search.md
│   ├── job-search.json     ← BM25 searches this
│   ├── resume.md
│   └── resume.json         ← And this
├── personal/
│   ├── about.md
│   └── about.json          ← And this
└── projects/
    ├── hackathon.md
    └── hackathon.json      ← And all JSON files
```

**Exclusions:**
- Files in `.localbrain/` internal directory are skipped
- Only user-facing content is indexed
- System configuration and logs are excluded

### Citation Structure

Each JSON file contains citation metadata with 4 standardized fields:

```json
{
  "1": {
    "platform": "Gmail",
    "timestamp": "2024-03-15T10:30:00Z",
    "url": null,
    "quote": "The deadline has been moved to April 1st"
  },
  "2": {
    "platform": "Discord",
    "timestamp": "2024-03-20T14:00:00Z",
    "url": "https://discord.com/channels/123/456",
    "quote": null
  }
}
```

**Fields:**
- `platform`: Source platform (Gmail, Discord, LinkedIn, Manual, etc.)
- `timestamp`: ISO 8601 formatted timestamp
- `url`: Link to source (nullable)
- `quote`: Direct quotation from source (nullable)

## BM25 Algorithm

**BM25 (Okapi BM25)** is a probabilistic ranking function that scores documents based on query term frequency and document length. It's the gold standard for keyword-based information retrieval.

**Key Strengths:**
- **Exact keyword matching**: Find specific terms like "NVIDIA" or "internship"
- **Multi-term queries**: Score documents containing multiple search terms
- **Term frequency weighting**: Prioritize documents with more occurrences
- **Length normalization**: Account for document length differences
- **Fast execution**: Much faster than semantic search for exact matches

**Ranking Approach:**
- Calculates relevance score for each citation
- Considers term frequency within document
- Normalizes by document length
- Applies inverse document frequency (IDF) weighting
- Returns ranked list of matching citations

## Search Process

### 1. Index Building

**Citation Loading:**
- Walk through vault directory recursively
- Find all `.json` files (excluding `.localbrain/`)
- Parse each citation entry
- Extract searchable text from all fields
- Link to corresponding markdown file

**Index Creation:**
- Tokenize searchable text for each citation
- Build BM25 ranking function
- Precompute document statistics
- Cache index for fast queries

### 2. Query Processing

**Query Tokenization:**
- Split query into individual terms
- Lowercase normalization
- Remove stop words (optional)
- Apply stemming (optional)

**Scoring:**
- Calculate BM25 score for each citation
- Rank by relevance score
- Filter out zero-score results
- Return top K results

### 3. Result Formatting

**Citation Results:**
- Include original citation metadata
- Add BM25 relevance score
- Link to source markdown file
- Provide file path and citation ID
- Format for frontend consumption

## Advanced Filtering

### Metadata Filters

**Platform Filtering:**
- Filter citations by source platform
- Support exact matches (e.g., "Gmail", "Discord")
- Enable multi-platform searches

**Date Range Filtering:**
- Filter by timestamp ranges
- Support relative dates ("last 7 days")
- ISO 8601 date format for precision

**Content Filters:**
- `has_url`: Only citations with URLs
- `has_quote`: Only citations with direct quotes
- `url_contains`: Filter by URL patterns
- `quote_contains`: Search within quotes only

### Combined Filtering

**Pre-filter + Search:**
- Apply metadata filters first
- Then perform BM25 search on filtered set
- Reduces search space for better performance
- Enables precise targeted queries

**Example Scenarios:**
- "Find Discord citations with quotes from last 7 days"
- "Search Gmail citations for 'deadline' in March 2024"
- "Find all LinkedIn citations with URLs"

## Integration Points

### Frontend

**Search Interface:**
- Accept keyword queries from UI
- Provide filter options (platform, date, etc.)
- Display ranked results with scores
- Show citation context and metadata

**Result Display:**
- Highlight matching terms in quotes
- Link to source markdown files
- Show platform badges and timestamps
- Enable filtering and refinement

### MCP API

**External Tool Access:**
- Expose BM25 search via MCP interface
- Support structured query parameters
- Return standardized result format
- Respect bridge access permissions

### Retrieval Engine

**Hybrid Search:**
- Combine with semantic search for best results
- BM25 for precision (exact matches)
- Semantic for recall (similar concepts)
- Weighted combination of both approaches

**Search Types:**
- `search_agentic()`: Uses BM25 for exact matching
- `search()`: Uses semantic for concept matching
- `search_hybrid()`: Combines both approaches

### Protocol Handler

**localbrain:// Commands:**
- `localbrain://search_agentic?q=NVIDIA&platform=Gmail`
- Parse query parameters into BM25 filters
- Execute search and return results
- Format for protocol response

## Performance Features

### Caching Strategy

**Index Caching:**
- Cache BM25 index in memory
- Persist to disk for fast startup
- Invalidate on vault changes
- Automatic cache refresh

**Query Caching:**
- Cache frequent query results
- Expire on content updates
- LRU eviction policy
- Configurable cache size

### Incremental Updates

**File Change Detection:**
- Monitor vault for JSON file changes
- Update index incrementally
- No need to rebuild entire index
- Fast refresh for single file updates

**Watchdog Integration:**
- Use filesystem watcher
- Detect create, modify, delete events
- Trigger index updates automatically
- Keep index in sync with vault

### Optimization Techniques

**Parallel Processing:**
- Load JSON files in parallel
- Multi-threaded index building
- Concurrent query processing
- Batch result formatting

**Memory Efficiency:**
- Stream large JSON files
- Index only searchable fields
- Compress stored text
- Lazy load full citation data

## Comparison: BM25 vs Semantic Search

### When to Use BM25

**Best for:**
- Exact keyword searches ("NVIDIA", "internship")
- Platform-specific queries
- Date-based filtering
- URL or quote searches
- Known-item search (user knows what they want)

**Advantages:**
- Much faster than semantic search
- Deterministic results
- Works without embeddings
- Lower computational cost

### When to Use Semantic Search

**Best for:**
- Natural language queries
- Conceptual similarity
- Exploratory search
- Cross-topic connections
- When exact terms aren't known

**Advantages:**
- Understands meaning and context
- Finds related concepts
- Handles synonyms automatically
- Better for vague queries

### Hybrid Approach

**Combined Strengths:**
- Use BM25 for filtering and precision
- Use semantic for conceptual matching
- Weight results from both approaches
- Provide toggle in UI for user preference

**Implementation:**
- Run both searches in parallel
- Combine results with weighted scores
- Remove duplicates
- Re-rank by combined relevance

## Configuration

**BM25 Parameters:**
- `k1`: Term frequency saturation (default: 1.5)
- `b`: Length normalization (default: 0.75)
- `epsilon`: Floor value for IDF (default: 0.25)

**Search Settings:**
- `top_k`: Number of results to return (default: 10)
- `min_score`: Minimum BM25 score threshold (default: 0.0)
- `max_results`: Hard limit on results (default: 100)

**Index Settings:**
- `cache_enabled`: Enable index caching (default: true)
- `auto_refresh`: Automatic index updates (default: true)
- `parallel_loading`: Multi-threaded loading (default: true)

## Development & Testing

**Test Scenarios:**
- Basic keyword search ("NVIDIA", "internship")
- Multi-term queries ("offer deadline March")
- Platform filtering (Gmail only)
- Date range queries (last 30 days)
- Combined filters (Discord + quotes + recent)
- Empty results (no matches)
- Large result sets (100+ matches)

**Performance Benchmarks:**
- Index build time for 1000 citations
- Query latency (<50ms target)
- Cache hit rate (>80% target)
- Memory usage (<100MB per 10k citations)

**Integration Tests:**
- Load citations from test vault
- Verify all JSON files indexed
- Test filter combinations
- Validate result format
- Check error handling

## Future Enhancements

**Query Features:**
- Phrase matching with quotes ("exact phrase")
- Boolean operators (AND, OR, NOT)
- Wildcard searches (intern*)
- Fuzzy matching for typos
- Regular expression support

**Advanced Filtering:**
- Nested field queries
- Range queries (numeric, date)
- Aggregation and faceting
- Custom scoring functions
- User-defined filters

**Performance:**
- Distributed search for large vaults
- GPU acceleration for scoring
- Approximate nearest neighbor (ANN) for speed
- Adaptive caching strategies
- Query optimization

**Integration:**
- Real-time index updates (no delays)
- Multi-vault search
- Cross-citation analysis
- Citation graph navigation
- Export results in multiple formats
