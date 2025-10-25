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

## Integration Points

- **Frontend**: Receive and display search results
- **Ingestion**: Access processed content and embeddings
- **MCP Server**: Provide search tools for external integrations
- **Bridge Service**: Enforce access permissions and logging
- **Database**: Query vector stores and metadata
