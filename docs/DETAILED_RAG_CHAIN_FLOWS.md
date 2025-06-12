# Detailed RAG Chain Flow Analysis

## Overview

The system has **3 main conversation types** with **2 output methods** (streaming vs non-streaming) that follow the same logic flow. Here's the complete breakdown:

## 🔄 The 3 Main Conversation Chains

### 1. 🗨️ Regular Conversation (No RAG)
- **Trigger**: No collection specified, no files attached
- **Collection**: None
- **Prompt Used**: `regular_chat_prompt` (configurable)
- **Fallback**: Built-in default if no prompt configured

### 2. 📁 User Files Conversation (User RAG)
- **Trigger**: User uploads files or uses existing user files
- **Collection**: User-specific collection (e.g., `user_123_files`)
- **Prompt Used**: `user_collection_rag_prompt` (configurable)
- **Fallback**: `DEFAULT_RAG_SYSTEM_PROMPT` if config fails

### 3. 🏢 Global Collection Conversation (Admin RAG)
- **Trigger**: Admin-defined/predefined collections
- **Collection**: Global/admin collections (e.g., `company_docs`)
- **Prompt Used**: `global_collection_rag_prompt` (configurable)
- **Fallback**: `DEFAULT_RAG_SYSTEM_PROMPT` if config fails

---

## 📊 Flow Visualizations

### Flow 1: Regular Conversation (No RAG)
```
🟦 User Input
    ↓
🔍 Determine Type: No collection, no files
    ↓
🎯 Route: LLM Service (llm_service.py)
    ↓
⚙️ Prompt: get_regular_chat_prompt(db)
    ↓ (if fails)
🆘 Fallback: None (just basic LLM)
    ↓
🤖 LLM Response (with/without streaming)
    ↓
💾 Save to DB
    ↓
📤 Return Response
```

**Key Method**: `llm_service.get_streaming_llm_response()` or `llm_service.get_llm_response()`

### Flow 2: User Files Conversation (User RAG)
```
🟦 User Input + Files/User Collection
    ↓
🔍 Determine Type: collection_name = user-specific
    ↓
🎯 Route: RAG Service (rag_service.py)
    ↓
🧠 Contextualization: English prompt
    "Given the chat history and the latest user question, 
     create a standalone question..."
    ↓
🔍 Collection Check: _is_global_collection() → FALSE
    ↓
⚙️ RAG Prompt: get_user_collection_rag_prompt(db)
    ↓ (if fails)
🆘 Fallback: DEFAULT_RAG_SYSTEM_PROMPT
    ↓
🔍 Vector Search: In user collection
    ↓
🧩 Context Assembly: Retrieved docs + prompt
    ↓
🤖 LLM Response (with/without streaming)
    ↓
💾 Save to DB (with RAG context)
    ↓
📤 Return Response
```

**Key Method**: `rag_service.get_streaming_rag_response()` or `rag_service.get_rag_response()`

### Flow 3: Global Collection Conversation (Admin RAG)
```
🟦 User Input + Global Collection
    ↓
🔍 Determine Type: collection_name = admin/global
    ↓
🎯 Route: RAG Service (rag_service.py)
    ↓
🧠 Contextualization: English prompt
    "Given the chat history and the latest user question, 
     create a standalone question..."
    ↓
🔍 Collection Check: _is_global_collection() → TRUE
    ↓
⚙️ RAG Prompt: get_global_collection_rag_prompt(db)
    ↓ (if fails)
🆘 Fallback: DEFAULT_RAG_SYSTEM_PROMPT
    ↓
🔍 Vector Search: In global collection
    ↓
🧩 Context Assembly: Retrieved docs + prompt
    ↓
🤖 LLM Response (with/without streaming)
    ↓
💾 Save to DB (with RAG context)
    ↓
📤 Return Response
```

**Key Method**: `rag_service.get_streaming_rag_response()` or `rag_service.get_rag_response()`

---

## 🎯 Prompt Usage Breakdown

### 1. Contextualization Prompt (Shared)
**Location**: `rag_service.py` lines 309-311 and 422-424
**Used in**: Both user files and global collection flows
**Purpose**: Convert conversational questions to standalone search queries

```
Given the chat history and the latest user question, create a standalone question that captures all relevant context. If there's no relevant context, return the original question unchanged.
```

### 2. Regular Chat Prompt (Configurable)
**Config Key**: `regular_chat_prompt`
**Used in**: Regular conversation flow
**Fallback**: None (just basic LLM without system prompt)
**Default**: Not set (admin must configure)

### 3. User Collection RAG Prompt (Configurable)
**Config Key**: `user_collection_rag_prompt`
**Used in**: User files conversation flow
**Fallback**: `DEFAULT_RAG_SYSTEM_PROMPT`
**Default**: Available in `/app/app/api/routes/config.py`

### 4. Global Collection RAG Prompt (Configurable)
**Config Key**: `global_collection_rag_prompt`
**Used in**: Global collection conversation flow
**Fallback**: `DEFAULT_RAG_SYSTEM_PROMPT`
**Default**: Available in `/app/app/api/routes/config.py`

---

## 🔧 Collection Detection Logic

### How the System Determines Collection Type:

```python
def _is_global_collection(self, db: Session, collection_name: str) -> bool:
    """Check if collection is global/predefined"""
    predefined_collection = RAGConfigService.get_predefined_collection(db)
    
    return (collection_name == predefined_collection or 
            collection_name == f"admin_{predefined_collection}" or
            collection_name.replace("admin_", "") == predefined_collection)
```

### Collection Type Examples:
- **Global**: `company_docs`, `admin_company_docs`, `knowledge_base`
- **User**: `user_123_documents`, `user_456_files`, etc.
- **None**: No collection specified → Regular chat

---

## 🚨 Fallback Chain

### Primary Fallbacks:
1. **Config Retrieval Fails** → Use `DEFAULT_RAG_SYSTEM_PROMPT`
2. **Vector Search Fails** → Continue with empty context
3. **LLM Fails** → Return error message
4. **Collection Not Found** → Fall back to regular chat

### Error Handling:
```python
# In get_rag_response()
except Exception as e:
    return {
        "response": "I'm having trouble accessing the knowledge base. Please try again later.",
        "conversation_id": conversation_id or str(uuid.uuid4()),
        "meta_data": meta_data
    }
```

---

## ⚡ Streaming vs Non-Streaming

### Same Logic, Different Output:

| Aspect | Streaming | Non-Streaming |
|--------|-----------|---------------|
| **Methods** | `get_streaming_rag_response()` | `get_rag_response()` |
| **Contextualization** | ✅ Same prompt | ✅ Same prompt |
| **RAG Prompts** | ✅ Same selection logic | ✅ Same selection logic |
| **Vector Search** | ✅ Same retrieval | ✅ Same retrieval |
| **LLM Call** | `astream()` | `ainvoke()` |
| **Output** | Token-by-token generator | Complete response |
| **Save to DB** | After streaming complete | Immediately |

---

## 🏗️ API Entry Points

### Unified Chat (Main Entry)
**File**: `/app/app/api/routes/unified_chat.py`
**Logic**:
1. Determine conversation type from request
2. Route to appropriate service method
3. Handle streaming response

### Direct RAG Endpoint
**File**: `/app/app/api/routes/rag.py`
**Logic**:
1. Always uses RAG service
2. Requires collection specification
3. Handles permission checks

---

## 🎯 Key Implementation Details

### 1. Collection Name Sanitization
- User input: `My Documents!`
- Sanitized: `my_documents`
- Used for Milvus collection naming

### 2. Dynamic Prompt Selection
```python
def _get_rag_system_prompt(self, db: Session, collection_name: str = None) -> str:
    if collection_name and self._is_global_collection(db, collection_name):
        return RAGConfigService.get_global_collection_rag_prompt(db)
    else:
        return RAGConfigService.get_user_collection_rag_prompt(db)
```

### 3. Context Assembly
```python
# Format context from retrieved documents
context_texts = []
for doc in relevant_docs:
    context_texts.append(self._extract_doc_text(doc))
context = "\n\n".join(context_texts)

# Add to system prompt
system_prompt = f"{base_system_prompt}\n\nContext: {context}"
```

### 4. Message History
- Both flows use `CustomMessageHistory(conversation_id, db)`
- Stored in PostgreSQL, not in-memory
- Consistent across streaming and non-streaming

---

## ✅ Summary

The system uses **identical logic** for streaming and non-streaming, with **3 distinct conversation types**:

1. **Regular**: No RAG, uses `regular_chat_prompt`
2. **User Files**: User RAG, uses `user_collection_rag_prompt`  
3. **Global Collection**: Admin RAG, uses `global_collection_rag_prompt`

The **contextualization prompt is shared** across RAG flows, and **fallbacks ensure robustness** at every level. The main difference between streaming and non-streaming is simply the LLM output method, not the core logic.
