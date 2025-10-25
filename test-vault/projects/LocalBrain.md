# LocalBrain

Local-first knowledge management system with AI-powered ingestion and semantic search.

## Overview

Building a personal knowledge base that ingests emails, notes, and documents into structured markdown with automated citation tracking [1].

**Tech Stack:** Python, FastAPI, Claude API, Chroma vector DB, TypeScript, React [1].

## Key Features

### Agentic Ingestion Pipeline
- LLM-powered content analysis and routing
- Fuzzy matching for section names (Levenshtein distance) [2]
- Validation feedback loops with self-correction
- 95% success rate with max 3 retry attempts [2]

### Citation System
- Numbered citations [1], [2] in markdown
- Separate JSON files for source metadata
- One citation per source document (not per fact)
- Platform tracking: Gmail, Discord, LinkedIn, etc.

### Architecture
- Electron desktop app with Next.js frontend
- Python backend for ingestion and retrieval
- Local-first: all processing on device
- OpenCode-inspired fuzzy matching and validation [2]

## Development Progress

**Phase 1 (Current):** Core ingestion pipeline ✅
- Completed agentic routing with Claude Haiku 4.5
- Implemented fuzzy section matching
- Built validation and retry system
- Added Anthropic-optimized prompts

**Phase 2 (Next):** Semantic search
- Vector embeddings for content
- Hybrid search (keyword + semantic)
- Query understanding and expansion

**Phase 3 (Future):** Connectors
- Gmail integration
- Discord message ingestion
- Slack workspace sync
- Browser history connector

## Learnings

Understanding how to build robust LLM systems:
- Don't try to make LLM output perfect
- Build fuzzy matching to handle imperfection gracefully
- Validation feedback loops enable self-correction
- Retry mechanisms dramatically improve reliability

## Related

- [[AI Research Notes]]
- [[System Design Notes]]
- [[Career Goals]]
