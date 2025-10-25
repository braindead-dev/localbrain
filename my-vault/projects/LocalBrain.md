# LocalBrain

Personal AI context management system - local-first architecture for managing life context.

## Overview

Building a desktop application that ingests data from various sources (emails, messages, documents) and makes it searchable using embeddings and semantic search.

## Goals

- Create a truly local-first knowledge management system
- Support multiple data connectors (Gmail, Discord, Slack, etc.)
- Implement semantic search using sentence transformers
- Build MCP server for AI tool integration
- Maintain complete user privacy - all data stays local

## Stack

**Frontend:**
- Electron + Next.js
- React for UI components
- TailwindCSS for styling

**Backend:**
- Python 3.10 with FastAPI
- ChromaDB for vector storage
- SQLAlchemy for metadata
- Sentence Transformers for embeddings

Started development on October 1, 2024 [1]. Currently in Phase 1 - building core ingestion and vault management system.

## Progress

- ✅ Vault initialization system
- ✅ Basic ingestion with keyword matching
- ✅ Citation system design (JSON metadata)
- 🚧 LLM-powered intelligent ingestion
- 📋 Embeddings and semantic search
- 📋 MCP server implementation
- 📋 Connector framework


- ✅ Vector search implementation with ChromaDB
- ✅ Embedding generation using sentence-transformers

## Content

## Opportunities

Received final interview date from Amazon for Senior SWE role on November 18th [2].

## Related

- [[AI Projects]]
- [[Learning Goals]]
