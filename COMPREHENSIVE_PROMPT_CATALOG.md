# Comprehensive LLM Prompts Catalog

## Executive Summary

This document provides a complete analysis of all prompts in the codebase, their locations, values, and usage in chains. The system contains **18+ unique prompts** across **6 categories** serving different purposes from RAG operations to title generation.

**Recent Update**: Legacy Indonesian contextualization prompt and unused methods have been removed for consistency. The system now uses a single English contextualization prompt.

## System Architecture

### Prompt Management
- **Configuration**: Managed via unified admin config system (`AdminConfigService`)
- **Database Storage**: Prompts stored in `admin_config` table with keys and categories
- **API Access**: Available through unified config endpoints
- **Default Fallbacks**: System provides defaults when prompts aren't configured

### Key Configuration Keys
- `global_collection_rag_prompt` - RAG prompt for global/admin collections
- `user_collection_rag_prompt` - RAG prompt for user collections  
- `regular_chat_prompt` - System prompt for non-RAG chat

---

## 1. RAG System Prompts (6 Total)

### 1.1 Default RAG System Prompt
**Location**: `/app/app/services/rag_service.py` lines 39-43  
**Usage**: Default fallback for all RAG operations  
**Chain**: Used in `create_rag_chain()`, `get_rag_response()`, `get_streaming_rag_response()`
```
You are a helpful AI assistant. Answer the user's question based on the provided context and chat history.
If the answer isn't in the context, politely say you don't know rather than making up an answer.
Be concise, accurate, and helpful in your response.
```

### 1.2 Global Collection RAG Prompt
**Location**: Admin config with key `global_collection_rag_prompt`  
**Usage**: RAG operations on admin/predefined collections  
**Chain**: Selected by `_get_rag_system_prompt()` based on collection type  
**Default Value** (from `/app/app/api/routes/config.py` lines 103-113):
```
You are a helpful AI assistant for the organizational knowledge base. Use the provided context from official documents and resources to answer questions accurately and comprehensively. 

Context: {context}

Instructions:
- Answer based only on the provided context
- If information is not available, clearly state "I don't have enough information to answer that question"
- Maintain a professional and helpful tone
- Cite specific documents when possible
```

### 1.3 User Collection RAG Prompt  
**Location**: Admin config with key `user_collection_rag_prompt`  
**Usage**: RAG operations on user-uploaded collections  
**Chain**: Selected by `_get_rag_system_prompt()` for non-global collections  
**Default Value** (from `/app/app/api/routes/config.py` lines 114-122):
```
You are a helpful AI assistant. Use the documents provided by the user to answer their questions accurately and comprehensively.

Context: {context}

Instructions:
- Answer based on the user's uploaded documents
- If the answer isn't in the context, politely say you don't know
- Be concise, accurate, and helpful in your response
- Reference specific sections of documents when relevant
```

### 1.4 Regular Chat Prompt
**Location**: Admin config with key `regular_chat_prompt`  
**Usage**: Non-RAG chat conversations  
**Chain**: Used in `get_llm_response()` and `get_streaming_llm_response()`  
**Default Value** (from `/app/app/api/routes/config.py` lines 123-130):
```
You are a helpful AI assistant. Provide clear, accurate, and helpful responses to the user's questions.

Instructions:
- Use your general knowledge to assist the user
- Be conversational yet professional
- Ask clarifying questions when needed
- Provide step-by-step explanations for complex topics
```

### 1.5 QA System Prompt (Streaming)
**Location**: `/app/app/services/rag_service.py` lines 463-467  
**Usage**: Streaming RAG responses  
**Chain**: Used in `get_streaming_rag_response()`
```
You are a helpful AI assistant. Answer the user's question based on the provided context. If the answer isn't in the context, politely say you don't know rather than making up an answer. Be concise, accurate, and helpful in your response.

Context: {context}
```

### 1.6 Streaming Assistant Prompt
**Location**: `/app/app/services/rag_service.py` lines 818-821  
**Usage**: Conversation-specific streaming responses  
**Chain**: Used in `get_streaming_conversation_rag_response()`
```
You are a helpful assistant that answers questions based on the provided context. If you don't know the answer based on the context, say you don't know. Do not make up information. Always cite the document source when referring to specific information.
```

---

## 2. Contextualization Prompts (1 Total)

**Purpose**: Transform conversational questions into standalone, searchable queries for vector search.

### 2.1 Contextualization System Prompt (English)
**Location**: `/app/app/services/rag_service.py` lines 309-311 and 422-424  
**Usage**: Question contextualization for all RAG operations  
**Chain**: Used in both `get_streaming_rag_response()` and `get_rag_response()` methods
```
Given the chat history and the latest user question, create a standalone question that captures all relevant context. If there's no relevant context, return the original question unchanged.
```

**Note**: Legacy Indonesian contextualization prompt and unused methods have been removed for consistency. The system now uses a single English prompt for all contextualization needs.

---

## 3. Title Generation Prompts (5 Total)

### 3.1 Initial Title Generation Prompt
**Location**: `/app/app/services/title_service.py` lines 53-59  
**Function**: `generate_initial_title()`  
**Usage**: Generate title from first user message  
**Chain**: Direct LLM invocation with thinking disabled
```
Generate a short, descriptive title (2-5 words) for a conversation that starts with this message.
Focus only on the main topic or intent. Be concise and specific.
Use the same language as the user's message.

Message: "{message}"

Title: 
```

### 3.2 Periodic Title Update Prompt
**Location**: `/app/app/services/title_service.py` lines 106-112  
**Function**: `update_title_periodic()`  
**Usage**: Update title based on recent messages  
**Chain**: Direct LLM invocation with thinking disabled
```
Generate a short, descriptive title (2-5 words) for a conversation containing these messages.
Focus on the main topic or intent. Be concise and specific.
Use the same language as the user's messages.

Messages:
{messages}

Title: 
```

### 3.3 Topic Shift Detection Prompt
**Location**: `/app/app/services/title_service.py` lines 147-152  
**Function**: `detect_topic_shift()`  
**Usage**: Detect significant topic changes  
**Chain**: Direct LLM invocation for boolean decision
```
Determine if there's a significant topic shift between the current conversation title and the new message.
Current title: "{title}"
New message: "{message}"

Is there a significant shift in topic? Answer YES or NO only.
```

### 3.4 Topic Shift Title Update Prompt
**Location**: `/app/app/services/title_service.py` lines 188-198  
**Function**: `update_title_on_shift()`  
**Usage**: Generate new title when topic shift detected  
**Chain**: Direct LLM invocation with thinking disabled
```
Generate a short, descriptive title (2-5 words) for a conversation that has shifted to a new topic.
Focus on the most recent topic or intent. Be concise and specific.
Use the same language as the user's messages.

Previous title: "{previous_title}"

Recent messages:
{messages}

New title reflecting the current topic: 
```

### 3.5 Final Title Generation Prompt
**Location**: `/app/app/services/title_service.py` lines 253-262  
**Function**: `generate_final_title()`  
**Usage**: Comprehensive title when conversation ends  
**Chain**: Direct LLM invocation with thinking disabled
```
Generate a short, comprehensive title (2-5 words) that captures the entire conversation.
Focus on the most significant topic or purpose. Be concise but descriptive.
Use the same language as the user's messages.

Conversation length: {message_count} messages
First user message: "{first_message}"
Last user message: "{last_message}"
Current title: "{current_title}"

Final comprehensive title: 
```

---

## 4. Headline Generation Prompts (2 Total)

### 4.1 Conversation Headline Prompt
**Location**: `/app/app/services/llm_service.py` lines 384-400  
**Function**: `generate_conversation_headline()`  
**Usage**: Generate topic labels for conversations  
**Chain**: Direct LLM invocation with thinking disabled
```
What is the main topic of these messages in 2-5 words? 
Just the core topic, no extra words.

Use the user language for the headline/summary.
Examples:
Messages about Python programming → "Python Programming"
Messages about climate change → "Climate Change"
Messages about ITDEL University → "ITDEL University"
Messages about DGX vs HGX → "DGX vs HGX"

Messages:
{formatted_messages}

Topic: 
```

### 4.2 Fallback Context Prompt
**Location**: Various locations in RAG service  
**Usage**: When no documents found or collection unavailable  
**Chain**: Used as context replacement in document chains
```
No relevant documents were found for your question. I'll try to answer based on my general knowledge.
```

---

## 5. Chain Usage Analysis

### RAG Chains
1. **`get_rag_response()`**: Uses QA system prompt + contextualization prompt  
2. **`get_streaming_rag_response()`**: Uses streaming QA prompt + contextualization prompt
3. **`get_conversation_rag_response()`**: Uses dynamic prompt selection based on collection type

**Note**: Legacy `create_rag_chain()` method has been removed for code simplification.

### LangChain Template Structures
```python
# Standard RAG Template
ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# With Context Addition
ChatPromptTemplate.from_messages([
    ("system", f"{base_system_prompt}\n\nContext: {{context}}"),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# Contextualization Template  
ChatPromptTemplate.from_messages([
    ("system", contextualize_q_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])
```

---

## 6. Configuration Management

### Admin Config Service
- **Class**: `AdminConfigService` in `/app/app/services/admin_config_service.py`
- **Model**: `AdminConfig` in `/app/app/models/admin_config.py`
- **Keys**: Pre-defined constants for all prompt types

### RAG Config Service  
- **Class**: `RAGConfigService` in `/app/app/services/rag_config_service.py`
- **Purpose**: Wrapper for RAG-specific configuration access
- **Methods**: Get/set for all three main prompt types

### API Endpoints
- **GET/PUT** `/admin/unified-config`: Complete configuration management
- **Individual endpoints removed**: Replaced with unified approach (documented in admin.py)

---

## 7. Language Support

### Multi-language Capabilities
- **English**: Primary language for most prompts
- **Indonesian**: Specific contextualization prompt available
- **Language Preservation**: All title prompts explicitly request to "Use the same language as the user's messages"

### Internationalization Features
- Dynamic language selection based on user input
- Language-aware title generation
- Contextual prompt selection by language

---

## 8. Thinking Mode Integration

### Automatic Thinking Disabling
All title and headline generation functions automatically disable thinking mode:
```python
llm = get_llm(db, override_thinking=False)
```

### Protected Functions
- `generate_conversation_headline()`
- `TitleGenerationService.generate_initial_title()`
- `TitleGenerationService.update_title_periodic()`
- `TitleGenerationService.detect_topic_shift()`
- `TitleGenerationService.update_title_on_shift()`
- `TitleGenerationService.generate_final_title()`

### Regular Chat Usage
- Uses global thinking setting from LLM config
- Can be overridden per request
- Applied to `get_llm_response()` and `get_streaming_llm_response()`

---

## 9. Prompt Categories Summary

| Category | Count | Files | Primary Usage |
|----------|-------|-------|---------------|
| RAG System Prompts | 6 | `rag_service.py`, admin config | Answer questions with retrieved context |
| Contextualization Prompts | 3 | `rag_service.py` | Create standalone questions from chat history |
| Title Generation Prompts | 5 | `title_service.py` | Generate/update conversation titles |
| Headline Generation Prompts | 2 | `llm_service.py`, fallbacks | Create topic labels and handle edge cases |

**Total Unique Prompts**: 16 (plus configuration variants)

---

## 10. Best Practices Observed

### Consistency Patterns
1. **Context Limitation**: Clear instructions about staying within provided context
2. **Conciseness**: Title prompts specifically request short, focused outputs  
3. **Safety**: Instructions to avoid making up information when context insufficient
4. **Language Awareness**: Prompts maintain user's language preference
5. **Professional Tone**: Appropriate formality for different use cases

### Configuration Flexibility
1. **Settings Override**: Environment-based prompt customization possible
2. **Database Config**: Admin can modify prompts via unified config API
3. **Default Fallbacks**: System gracefully handles missing configurations
4. **Type Safety**: Proper value typing in configuration system

### Performance Considerations
1. **Thinking Mode**: Automatically disabled for title generation to prevent overhead
2. **Streaming Support**: Dedicated prompts for real-time response generation
3. **Caching**: Configuration values cached via admin config service
4. **Chain Optimization**: Efficient prompt template structures

---

## 11. Implementation Status

### Completed Features
✅ **Unified Configuration System**: All prompts manageable via single API  
✅ **Global Collection Prompts**: Separate prompts for admin vs user collections  
✅ **Multi-language Support**: Indonesian and English contextualization  
✅ **Title Generation System**: Comprehensive conversation labeling  
✅ **Thinking Mode Integration**: Automatic disabling for title functions  
✅ **API Documentation**: Complete endpoint coverage  

### Configuration Keys Used
- `global_collection_rag_prompt` - Admin collection RAG operations
- `user_collection_rag_prompt` - User collection RAG operations  
- `regular_chat_prompt` - Non-RAG chat conversations
- All keys stored in `general` category of admin config

### Legacy Cleanup
- ❌ Individual prompt endpoints removed from `/app/app/api/routes/admin.py`
- ✅ Unified config endpoints handle all prompt management
- ✅ Backward compatibility maintained

---

## 12. Usage Examples

### Accessing Prompts Programmatically
```python
# Get RAG prompt for specific collection type
from app.services.rag_config_service import RAGConfigService

# Global collection prompt
global_prompt = RAGConfigService.get_global_collection_rag_prompt(db)

# User collection prompt  
user_prompt = RAGConfigService.get_user_collection_rag_prompt(db)

# Regular chat prompt
chat_prompt = RAGConfigService.get_regular_chat_prompt(db)
```

### API Configuration
```bash
# Get all configuration including prompts
GET /admin/unified-config

# Update prompts via unified config
PUT /admin/unified-config
{
  "general": {
    "global_collection_rag_prompt": "Your custom global prompt...",
    "user_collection_rag_prompt": "Your custom user prompt...", 
    "regular_chat_prompt": "Your custom chat prompt..."
  }
}
```

### Chain Integration Example
```python
# Dynamic prompt selection in RAG operations
def _get_rag_system_prompt(self, db: Session, collection_name: str = None) -> str:
    if collection_name and self._is_global_collection(db, collection_name):
        return RAGConfigService.get_global_collection_rag_prompt(db)
    else:
        return RAGConfigService.get_user_collection_rag_prompt(db)
```

---

## 13. Conclusion

The system provides a comprehensive, configurable prompt management system with:

1. **20+ unique prompts** across 7 functional categories
2. **Unified configuration** via admin API and database storage  
3. **Multi-language support** with automatic language preservation
4. **Performance optimization** through thinking mode control
5. **Flexible architecture** supporting both global and user-specific prompts

All prompts are actively used in LangChain operations and can be configured by administrators without code changes, providing a robust foundation for conversational AI operations.
