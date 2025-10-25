#!/usr/bin/env python3
"""
Retrieval Engine for LocalBrain

Handles semantic search using ChromaDB Cloud for vector similarity matching.
Implements the 8-step retrieval process: Query Reception → Preprocessing → 
Embedding → Vector Search → Filtering → Ranking → Formatting → Return
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from loguru import logger


class RetrievalEngine:
    """
    Main retrieval engine for semantic search over vault content.
    
    Uses ChromaDB Cloud for vector storage and similarity search.
    """
    
    def __init__(
        self,
        vault_path: str,
        chroma_api_key: str,
        chroma_tenant: str = "default-tenant",
        chroma_database: str = "default-database",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: str = "markdown_notes"
    ):
        """
        Initialize retrieval engine.
        
        Args:
            vault_path: Path to LocalBrain vault
            chroma_api_key: ChromaDB Cloud API key
            chroma_tenant: ChromaDB Cloud tenant name
            chroma_database: ChromaDB Cloud database name
            embedding_model: SentenceTransformers model name
            collection_name: ChromaDB collection name
        """
        self.vault_path = Path(vault_path).expanduser().resolve()
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB Cloud client
        logger.info(f"Connecting to ChromaDB Cloud (tenant: {chroma_tenant}, db: {chroma_database})")
        self.chroma_client = chromadb.CloudClient(
            api_key=chroma_api_key,
            tenant=chroma_tenant,
            database=chroma_database
        )
        
        # Get or create collection (matching ingestion script pattern)
        try:
            self.collection = self.chroma_client.get_or_create_collection(name=collection_name)
            logger.info(f"Connected to collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB collection: {e}")
            raise
        
        # Query cache
        self._query_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._embedding_cache: Dict[str, List[float]] = {}
    
    # ========================================================================
    # STEP 1: Query Reception
    # ========================================================================
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.0
    ) -> Dict[str, Any]:
        """
        Main semantic search interface.
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            filters: Optional metadata filters
            min_similarity: Minimum similarity threshold
        
        Returns:
            Dictionary with search results and metadata
        """
        start_time = datetime.now()
        
        logger.info(f"Search query: '{query}' (top_k={top_k})")
        
        # Step 1: Validate query
        if not query or not query.strip():
            return self._empty_response("Empty query")
        
        # Step 2: Preprocess query
        processed_query = self._preprocess_query(query)
        
        # Step 3: Generate embedding
        query_embedding = self._generate_embedding(processed_query)
        
        # Step 4: Vector search in ChromaDB
        raw_results = self._vector_search(query_embedding, top_k * 2)  # Get extra for filtering
        
        # Step 5: Apply metadata filters
        filtered_results = self._filter_results(raw_results, filters, min_similarity)
        
        # Step 6: Rank results
        ranked_results = self._rank_results(filtered_results, query_embedding)
        
        # Step 7: Format response
        formatted_results = self._format_results(ranked_results[:top_k])
        
        # Step 8: Return to user
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "query": query,
            "processed_query": processed_query,
            "results": formatted_results,
            "total": len(formatted_results),
            "took_ms": round(elapsed_ms, 2)
        }
    
    # ========================================================================
    # STEP 2: Query Preprocessing
    # ========================================================================
    
    def _preprocess_query(self, query: str) -> str:
        """
        Clean and normalize query text.
        
        - Lowercase conversion
        - Remove extra whitespace
        - Expand common abbreviations
        - Extract intent (future)
        """
        # Lowercase
        processed = query.lower().strip()
        
        # Remove extra whitespace
        processed = re.sub(r'\s+', ' ', processed)
        
        # Expand common abbreviations (add more as needed)
        abbreviations = {
            'swe': 'software engineering',
            'ml': 'machine learning',
            'ai': 'artificial intelligence',
            'cs': 'computer science',
        }
        
        for abbr, full in abbreviations.items():
            processed = re.sub(rf'\b{abbr}\b', full, processed)
        
        logger.debug(f"Preprocessed query: '{query}' -> '{processed}'")
        return processed
    
    # ========================================================================
    # STEP 3: Embedding Generation
    # ========================================================================
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using same model as chunks.
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector (768-dimensional for all-MiniLM-L6-v2)
        """
        # Check cache first
        if text in self._embedding_cache:
            logger.debug("Using cached embedding")
            return self._embedding_cache[text]
        
        # Generate embedding
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        embedding_list = embedding.tolist()
        
        # Cache for future use
        self._embedding_cache[text] = embedding_list
        
        return embedding_list
    
    # ========================================================================
    # STEP 4: Vector Search in ChromaDB
    # ========================================================================
    
    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Perform cosine similarity search in ChromaDB.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to retrieve
        
        Returns:
            List of chunks with similarity scores and metadata
        """
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Parse results
            chunks = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    chunk = {
                        'chunk_id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i],
                        'similarity': 1 - results['distances'][0][i]  # Convert distance to similarity
                    }
                    chunks.append(chunk)
            
            logger.info(f"ChromaDB returned {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return []
    
    # ========================================================================
    # STEP 5: Metadata Filtering
    # ========================================================================
    
    def _filter_results(
        self,
        results: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]],
        min_similarity: float
    ) -> List[Dict[str, Any]]:
        """
        Apply metadata filters and similarity threshold.
        
        Args:
            results: Raw search results
            filters: Metadata filters (platform, date_range, file_type, etc.)
            min_similarity: Minimum similarity score
        
        Returns:
            Filtered results
        """
        filtered = results
        
        # Apply similarity threshold
        filtered = [r for r in filtered if r['similarity'] >= min_similarity]
        
        if not filters:
            return filtered
        
        # Apply custom filters
        if 'platform' in filters:
            platform = filters['platform']
            filtered = [
                r for r in filtered
                if r['metadata'].get('platform') == platform
            ]
        
        if 'file_path' in filters:
            file_path = filters['file_path']
            filtered = [
                r for r in filtered
                if file_path in r['metadata'].get('file_path', '')
            ]
        
        if 'date_from' in filters:
            date_from = filters['date_from']
            filtered = [
                r for r in filtered
                if r['metadata'].get('timestamp', '') >= date_from
            ]
        
        if 'date_to' in filters:
            date_to = filters['date_to']
            filtered = [
                r for r in filtered
                if r['metadata'].get('timestamp', '') <= date_to
            ]
        
        # Exclude archived content
        filtered = [
            r for r in filtered
            if 'archive/' not in r['metadata'].get('file_path', '')
        ]
        
        logger.info(f"Filtered from {len(results)} to {len(filtered)} results")
        return filtered
    
    # ========================================================================
    # STEP 6: Result Ranking
    # ========================================================================
    
    def _rank_results(
        self,
        results: List[Dict[str, Any]],
        query_embedding: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Multi-factor ranking of search results.
        
        Factors:
        - Base similarity score (from ChromaDB)
        - Recency boost (newer content ranked higher)
        - Source quality boost (verified sources)
        - Diversity (avoid redundant results from same file)
        
        Args:
            results: Filtered search results
            query_embedding: Query vector (for re-ranking if needed)
        
        Returns:
            Re-ranked results
        """
        for result in results:
            base_score = result['similarity']
            
            # Recency boost
            recency_score = self._calculate_recency_score(
                result['metadata'].get('timestamp')
            )
            
            # Source quality boost
            quality_score = self._calculate_quality_score(
                result['metadata'].get('platform')
            )
            
            # Combined score
            result['final_score'] = (
                base_score * 0.7 +      # Base similarity: 70%
                recency_score * 0.2 +   # Recency: 20%
                quality_score * 0.1     # Quality: 10%
            )
        
        # Sort by final score
        ranked = sorted(results, key=lambda r: r['final_score'], reverse=True)
        
        # Apply diversity filter (max 3 results from same file)
        ranked = self._apply_diversity(ranked, max_per_file=3)
        
        return ranked
    
    def _calculate_recency_score(self, timestamp: Optional[str]) -> float:
        """Calculate recency boost score (0.0 to 1.0)."""
        if not timestamp:
            return 0.5  # Neutral if no timestamp
        
        try:
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            age_days = (datetime.now() - ts).days
            
            # Exponential decay: newest = 1.0, older = lower
            if age_days <= 7:
                return 1.0
            elif age_days <= 30:
                return 0.8
            elif age_days <= 90:
                return 0.6
            elif age_days <= 180:
                return 0.4
            else:
                return 0.2
        except:
            return 0.5
    
    def _calculate_quality_score(self, platform: Optional[str]) -> float:
        """Calculate source quality score (0.0 to 1.0)."""
        if not platform:
            return 0.5
        
        # Higher quality for certain platforms
        quality_map = {
            'Gmail': 0.9,
            'Discord': 0.8,
            'LinkedIn': 0.9,
            'Manual': 1.0,
            'Slack': 0.8,
            'Drive': 0.7,
        }
        
        return quality_map.get(platform, 0.5)
    
    def _apply_diversity(
        self,
        results: List[Dict[str, Any]],
        max_per_file: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Ensure diversity by limiting results per file.
        
        Args:
            results: Ranked results
            max_per_file: Maximum results from same file
        
        Returns:
            Diversified results
        """
        file_counts = defaultdict(int)
        diverse_results = []
        
        for result in results:
            file_path = result['metadata'].get('file_path', 'unknown')
            
            if file_counts[file_path] < max_per_file:
                diverse_results.append(result)
                file_counts[file_path] += 1
        
        return diverse_results
    
    # ========================================================================
    # STEP 7: Response Formatting
    # ========================================================================
    
    def _format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format results for frontend consumption.
        
        - Extract relevant fields
        - Add context windows
        - Highlight matching terms
        - Clean up metadata
        
        Args:
            results: Ranked search results
        
        Returns:
            Formatted results
        """
        formatted = []
        
        for result in results:
            metadata = result['metadata']
            
            formatted_result = {
                'chunk_id': result['chunk_id'],
                'text': result['text'],
                'snippet': self._create_snippet(result['text'], max_length=200),
                'file_path': metadata.get('file_path', 'unknown'),
                'similarity_score': round(result['similarity'], 3),
                'final_score': round(result['final_score'], 3),
                'platform': metadata.get('platform'),
                'timestamp': metadata.get('timestamp'),
                'chunk_position': metadata.get('chunk_position', 0),
                'source': {
                    'platform': metadata.get('platform'),
                    'url': metadata.get('url'),
                    'quote': metadata.get('quote')
                }
            }
            
            formatted.append(formatted_result)
        
        return formatted
    
    def _create_snippet(self, text: str, max_length: int = 200) -> str:
        """Create a shortened snippet of text."""
        if len(text) <= max_length:
            return text
        
        # Try to cut at sentence boundary
        snippet = text[:max_length]
        last_period = snippet.rfind('.')
        
        if last_period > max_length * 0.7:  # If we can cut at a sentence
            return snippet[:last_period + 1]
        else:
            return snippet + "..."
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _empty_response(self, reason: str) -> Dict[str, Any]:
        """Return empty response with reason."""
        return {
            "query": "",
            "processed_query": "",
            "results": [],
            "total": 0,
            "took_ms": 0,
            "error": reason
        }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the ChromaDB collection."""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model_name
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}


# ============================================================================
# Main Entry Point / Testing
# ============================================================================

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Get ChromaDB credentials
    chroma_api_key = os.getenv("CHROMA_API_KEY")
    chroma_tenant = os.getenv("CHROMA_TENANT", "default-tenant")
    chroma_database = os.getenv("CHROMA_DATABASE", "default-database")
    
    if not chroma_api_key:
        print("Error: CHROMA_API_KEY not found in environment")
        sys.exit(1)
    
    # Get vault path
    vault_path = os.getenv("VAULT_PATH", "~/test-vault")
    
    # Initialize retrieval engine
    print("Initializing Retrieval Engine...")
    engine = RetrievalEngine(
        vault_path=vault_path,
        chroma_api_key=chroma_api_key,
        chroma_tenant=chroma_tenant,
        chroma_database=chroma_database
    )
    
    # Get collection stats
    stats = engine.get_collection_stats()
    print(f"\nCollection Stats: {stats}")
    
    # Example search
    print("\n" + "="*80)
    print("Example Search: 'where did I apply for internships and what happened'")
    print("="*80)
    
    results = engine.search("where did I apply for internships and what happened", top_k=5)
    
    print(f"\nQuery: {results['query']}")
    print(f"Processed: {results['processed_query']}")
    print(f"Found {results['total']} results in {results['took_ms']}ms\n")
    
    for i, result in enumerate(results['results'], 1):
        print(f"{i}. [{result['final_score']:.3f}] {result['file_path']}")
        print(f"   {result['snippet']}")
        print(f"   Platform: {result['platform']} | Timestamp: {result['timestamp']}")
        print()

