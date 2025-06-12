# Contextualization Prompts Flow Guide

## Overview

Great news! The codebase has been cleaned up and now uses **only 1 English contextualization prompt** for consistency. The legacy Indonesian prompt and unused methods have been removed.

## What is Contextualization?

**Purpose**: Transform user questions that reference chat history into standalone, searchable queries for vector search.

**Example**:
- User: "What is RAG?" 
- Assistant: "RAG stands for Retrieval Augmented Generation..."
- User: "How does it work?" ← This needs contextualization!
- Contextualized: "How does RAG (Retrieval Augmented Generation) work?"

## The Single Contextualization Prompt

### English Contextualization Prompt  
**Location**: `/app/app/services/rag_service.py` lines 309-311 and 422-424
**Language**: English
**Used in**: `get_streaming_rag_response()` and `get_rag_response()` methods

```
Given the chat history and the latest user question, create a standalone question that captures all relevant context. If there's no relevant context, return the original question unchanged.
```

## Flow Diagrams

### Flow 1: Streaming RAG Response
```
User Question → get_streaming_rag_response()
    ↓
English Contextualization Prompt
    ↓
Contextualizer Chain (creates standalone question)
    ↓
Vector Search with contextualized question
    ↓
RAG System Prompt (Global/User Collection specific)
    ↓
Streaming Response
```

**Used for**: Real-time streaming responses

### Flow 2: Non-Streaming RAG Response
```
User Question → get_rag_response()
    ↓
English Contextualization Prompt (same as Flow 1)
    ↓
Contextualizer Chain (creates standalone question)
    ↓
Vector Search with contextualized question
    ↓
RAG System Prompt (Global/User Collection specific)
    ↓
Complete Response
```

**Used for**: Non-streaming responses

## When Each Flow is Used

### 1. Regular Conversation Flow
- **Entry Point**: API endpoints calling `get_streaming_rag_response()` or `get_rag_response()`
- **Collection**: User's personal collections or global collections
- **Contextualization**: English prompt
- **RAG Prompt**: Dynamically selected based on collection type

### 2. User Own Files Flow  
- **Entry Point**: File upload → collection creation → RAG response
- **Collection**: User-specific collection (e.g., `user_123_documents`)
- **Contextualization**: English prompt
- **RAG Prompt**: `user_collection_rag_prompt` (configurable)

### 3. Global Collection Flow
- **Entry Point**: Admin-managed knowledge base queries
- **Collection**: Global/predefined collections (e.g., `company_docs`, `admin_knowledge`)
- **Contextualization**: English prompt  
- **RAG Prompt**: `global_collection_rag_prompt` (configurable)

## Key Benefits of the Cleanup

1. **Consistency**: Single English contextualization prompt across all flows
2. **Simplicity**: Removed unused legacy methods (`create_rag_chain()`, `get_conversation_chain()`)
3. **Maintainability**: Fewer code paths to maintain and debug
4. **Performance**: Eliminated unused imports and dead code

## Current Implementation Status

- ✅ **Single Contextualization Prompt**: English prompt used consistently
- ✅ **Modern Methods Only**: `get_streaming_rag_response()` and `get_rag_response()` 
- ✅ **Clean Imports**: Removed unused LangChain imports
- ✅ **Collection-Agnostic**: Contextualization works for all collection types

## Summary

- **Purpose**: Transform conversational questions into standalone search queries
- **Count**: 1 English prompt (simplified from previous 2-3 prompts)  
- **Usage**: Used in both streaming and non-streaming RAG methods
- **Flow**: Question → Contextualize → Search → RAG Response
- **Collection Types**: Works with user files, global collections, and regular conversations
- **Status**: ✅ Code cleaned up and simplified
