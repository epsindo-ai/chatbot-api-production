# Visual RAG Chain Flow Diagram

## 🎯 Complete Flow Visualization

```
                           🟦 USER INPUT
                                |
                                v
                    🔍 CONVERSATION TYPE DETECTION
                           /        |        \
                          /         |         \
                         v          v          v
                ┌─────────────┐ ┌──────────┐ ┌─────────────┐
                │ 🗨️ REGULAR  │ │ 📁 USER   │ │ 🏢 GLOBAL   │
                │ CHAT        │ │ FILES     │ │ COLLECTION  │
                │             │ │ RAG       │ │ RAG         │
                └─────────────┘ └──────────┘ └─────────────┘
                       |             |              |
                       v             v              v
            ┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
            │ LLM SERVICE     │ │ RAG SERVICE  │ │ RAG SERVICE  │
            │ llm_service.py  │ │ rag_service  │ │ rag_service  │
            └─────────────────┘ └──────────────┘ └──────────────┘
                       |             |              |
                       v             v              v
            ┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
            │ PROMPT:         │ │ PROMPT:      │ │ PROMPT:      │
            │ regular_chat_   │ │ user_        │ │ global_      │
            │ prompt          │ │ collection_  │ │ collection_  │
            │                 │ │ rag_prompt   │ │ rag_prompt   │
            └─────────────────┘ └──────────────┘ └──────────────┘
                       |             |              |
                       v             |              |
            ┌─────────────────┐      v              v
            │ DIRECT LLM      │ ┌──────────────────────────┐
            │ RESPONSE        │ │ CONTEXTUALIZATION STEP   │
            │                 │ │ (English Prompt)         │
            └─────────────────┘ │ "Given chat history..."  │
                       |        └──────────────────────────┘
                       |                     |
                       |                     v
                       |        ┌──────────────────────────┐
                       |        │ VECTOR SEARCH            │
                       |        │ • User Collection        │
                       |        │ • Global Collection      │
                       |        └──────────────────────────┘
                       |                     |
                       |                     v
                       |        ┌──────────────────────────┐
                       |        │ CONTEXT ASSEMBLY         │
                       |        │ Retrieved Docs + Prompt  │
                       |        └──────────────────────────┘
                       |                     |
                       v                     v
            ┌─────────────────────────────────────────────┐
            │           🤖 LLM GENERATION                 │
            │                                             │
            │  ⚡ STREAMING     or    💾 NON-STREAMING    │
            │  • astream()              • ainvoke()       │
            │  • Token by token         • Complete resp   │
            └─────────────────────────────────────────────┘
                                    |
                                    v
            ┌─────────────────────────────────────────────┐
            │           💾 SAVE TO DATABASE               │
            │  • User message                             │
            │  • Assistant response                       │
            │  • RAG context (if applicable)              │
            └─────────────────────────────────────────────┘
                                    |
                                    v
                              📤 RETURN RESPONSE
```

## 🔄 Detailed Flow Breakdown

### 🗨️ Flow 1: Regular Chat (No RAG)
```
User: "Hello, how are you?"
  ↓
Type Detection: No collection, no files → REGULAR
  ↓
Service: llm_service.py
  ↓
Prompt: get_regular_chat_prompt(db)
  ↓
Fallback: None (basic LLM)
  ↓
LLM: Direct response
  ↓
Output: "Hello! I'm doing well, thank you for asking..."
```

### 📁 Flow 2: User Files RAG
```
User: "Summarize my uploaded document"
Files: [user_123_resume.pdf]
  ↓
Type Detection: User files present → USER_FILES
  ↓
Service: rag_service.py
  ↓
Collection: "user_123_documents"
  ↓
Contextualization: "Summarize my uploaded document" (no history)
  ↓
Collection Check: _is_global_collection() → FALSE
  ↓
Prompt: get_user_collection_rag_prompt(db)
  ↓
Vector Search: In user_123_documents collection
  ↓
Context: Retrieved relevant sections from resume
  ↓
LLM: RAG response with personal document context
  ↓
Output: "Based on your uploaded resume, here's a summary..."
```

### 🏢 Flow 3: Global Collection RAG
```
User: "What's our company policy on vacation?"
Collection: "company_policies"
  ↓
Type Detection: Global collection specified → GLOBAL_COLLECTION
  ↓
Service: rag_service.py
  ↓
Collection: "company_policies" (admin-managed)
  ↓
Contextualization: "What's our company policy on vacation?"
  ↓
Collection Check: _is_global_collection() → TRUE
  ↓
Prompt: get_global_collection_rag_prompt(db)
  ↓
Vector Search: In company_policies collection
  ↓
Context: Retrieved policy documents
  ↓
LLM: RAG response with company context
  ↓
Output: "According to our company policy documents..."
```

## 🚨 Fallback Scenarios

### Scenario 1: Config Failure
```
User Input → Type Detection → Service Selection → Prompt Retrieval FAILS
  ↓
Fallback: DEFAULT_RAG_SYSTEM_PROMPT
  ↓
Continue with default prompt
```

### Scenario 2: Collection Not Found
```
User Input → RAG Service → Vector Search FAILS
  ↓
Fallback: Continue with empty context
  ↓
LLM responds: "I don't have enough information..."
```

### Scenario 3: Complete RAG Failure
```
User Input → RAG Service → Multiple Failures
  ↓
Fallback: Return error message
  ↓
Output: "I'm having trouble accessing the knowledge base..."
```

## 🎛️ Configuration Matrix

| Flow Type | Prompt Config Key | Default Available | Fallback |
|-----------|------------------|-------------------|----------|
| Regular Chat | `regular_chat_prompt` | ❌ No | None |
| User Files | `user_collection_rag_prompt` | ✅ Yes | DEFAULT_RAG_SYSTEM_PROMPT |
| Global Collection | `global_collection_rag_prompt` | ✅ Yes | DEFAULT_RAG_SYSTEM_PROMPT |

## 🔧 Collection Detection Examples

### Global Collections (Returns TRUE):
- `company_docs`
- `admin_company_docs` 
- `knowledge_base`
- `admin_knowledge_base`

### User Collections (Returns FALSE):
- `user_123_documents`
- `user_456_files`
- `personal_collection`

### Regular Chat (No Collection):
- `null`
- `undefined`
- Empty string

## ⚡ Streaming vs Non-Streaming Comparison

| Aspect | Method Called | LLM Function | Output Format |
|--------|---------------|--------------|---------------|
| **Streaming** | `get_streaming_rag_response()` | `astream()` | Generator yielding tokens |
| **Non-Streaming** | `get_rag_response()` | `ainvoke()` | Complete response string |

**Both use identical logic for:**
- ✅ Contextualization
- ✅ Prompt selection  
- ✅ Vector search
- ✅ Context assembly
- ✅ Error handling

## 🎯 Entry Point Routing

### Unified Chat API (`/chat`)
```python
# Auto-detects type based on:
if request.collection_name and is_global:
    → Global Collection Flow
elif request.file_ids or existing_user_files:
    → User Files Flow  
else:
    → Regular Chat Flow
```

### Direct RAG API (`/rag`)
```python
# Always RAG, type based on collection:
if _is_global_collection(collection_name):
    → Global Collection Flow
else:
    → User Files Flow
```

This visual breakdown shows how the 3 chains work identically for streaming/non-streaming, with the key differentiator being the collection type and corresponding prompt selection.
