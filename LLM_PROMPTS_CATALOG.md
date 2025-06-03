# LLM Prompts Catalog

This document catalogs all LLM prompts found in the codebase, organized by function and service.

## Overview

The codebase contains multiple types of prompts for different purposes:
1. **RAG System Prompts** - For Retrieval Augmented Generation
2. **Contextualization Prompts** - For creating standalone questions from chat history
3. **Title Generation Prompts** - For creating conversation titles/headlines
4. **QA System Prompts** - For question answering with context

---

## 1. RAG Service Prompts (`/app/app/services/rag_service.py`)

### 1.1 Default RAG System Prompt
**Location**: Lines 39-43
**Purpose**: Default system prompt for RAG operations when not defined in settings
```
You are a helpful AI assistant. Answer the user's question based on the provided context and chat history.
If the answer isn't in the context, politely say you don't know rather than making up an answer.
Be concise, accurate, and helpful in your response.
```

### 1.2 Contextualization System Prompt (Indonesian)
**Location**: Lines 217-223  
**Function**: `create_rag_chain()`
**Purpose**: Contextualizes questions based on chat history (Indonesian language)
```
Berdasarkan riwayat chat dan pertanyaan terakhir pengguna yang mungkin merujuk pada konteks dalam riwayat chat, bentuk pertanyaan yang dapat dipahami. Tanpa riwayat chat jangan menjawab pertanyaan, hanya reformulasi jika diperlukan dan sebaliknya kembalikan seperti semula.
```

### 1.3 RAG Chain System Prompt
**Location**: Lines 231-237
**Function**: `create_rag_chain()`
**Purpose**: Standard RAG response generation
```
You are a helpful AI assistant. Answer the user's question based on the provided context. If the answer isn't in the context, politely say you don't know rather than making up an answer. Be concise, accurate, and helpful in your response.

Context: {context}
```

### 1.4 Contextualization System Prompt (English) 
**Location**: Lines 363-368
**Function**: `get_rag_response()`
**Purpose**: Creates standalone questions from chat history context
```
Given the chat history and the latest user question, create a standalone question that captures all relevant context. If there's no relevant context, return the original question unchanged.
```

### 1.5 QA System Prompt
**Location**: Lines 400-407
**Function**: `get_rag_response()`
**Purpose**: Non-streaming QA with context
```
You are a helpful AI assistant. Answer the user's question based on the provided context. If the answer isn't in the context, politely say you don't know rather than making up an answer. Be concise, accurate, and helpful in your response.

Context: {context}
```

### 1.6 Contextualization System Prompt (Repeated)
**Location**: Lines 481-485
**Function**: `get_rag_response()` (duplicate)
**Purpose**: Same as 1.4 - creates standalone questions
```
Given the chat history and the latest user question, create a standalone question that captures all relevant context. If there's no relevant context, return the original question unchanged.
```

### 1.7 QA System Prompt (Repeated)
**Location**: Lines 516-523
**Function**: `get_rag_response()` (duplicate)
**Purpose**: Same as 1.5 - QA with context
```
You are a helpful AI assistant. Answer the user's question based on the provided context. If the answer isn't in the context, politely say you don't know rather than making up an answer. Be concise, accurate, and helpful in your response.

Context: {context}
```

### 1.8 Streaming Assistant Prompt
**Location**: Lines 818-821
**Function**: `get_streaming_conversation_rag_response()`
**Purpose**: Streaming responses with document context
```
You are a helpful assistant that answers questions based on the provided context. If you don't know the answer based on the context, say you don't know. Do not make up information. Always cite the document source when referring to specific information.
```

---

## 2. Title/Headline Generation Prompts (`/app/app/services/title_service.py`)

### 2.1 Initial Title Generation Prompt
**Location**: Lines 53-59
**Function**: `generate_initial_title()`
**Purpose**: Generate title from first user message
```
Generate a short, descriptive title (2-5 words) for a conversation that starts with this message.
Focus only on the main topic or intent. Be concise and specific.
Use the same language as the user's message.

Message: "{message}"

Title: 
```

### 2.2 Periodic Title Update Prompt
**Location**: Lines 106-112
**Function**: `update_title_periodic()`
**Purpose**: Update title based on recent conversation messages
```
Generate a short, descriptive title (2-5 words) for a conversation containing these messages.
Focus on the main topic or intent. Be concise and specific.
Use the same language as the user's messages.

Messages:
{messages}

Title: 
```

### 2.3 Topic Shift Detection Prompt
**Location**: Lines 147-152
**Function**: `detect_topic_shift()`
**Purpose**: Detect if conversation topic has shifted significantly
```
Determine if there's a significant topic shift between the current conversation title and the new message.
Current title: "{title}"
New message: "{message}"

Is there a significant shift in topic? Answer YES or NO only.
```

### 2.4 Topic Shift Title Update Prompt
**Location**: Lines 188-198
**Function**: `update_title_on_shift()`
**Purpose**: Generate new title when topic shift is detected
```
Generate a short, descriptive title (2-5 words) for a conversation that has shifted to a new topic.
Focus on the most recent topic or intent. Be concise and specific.
Use the same language as the user's messages.

Previous title: "{previous_title}"

Recent messages:
{messages}

New title reflecting the current topic: 
```

### 2.5 Final Title Generation Prompt
**Location**: Lines 253-262
**Function**: `generate_final_title()`
**Purpose**: Generate comprehensive title when conversation ends
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

## 3. Headline Generation Prompts (`/app/app/services/llm_service.py`)

### 3.1 Conversation Headline Prompt
**Location**: Lines 384-400
**Function**: `generate_conversation_headline()`
**Purpose**: Generate simple topic labels for conversations
```
What is the main topic of these messages in 2-5 words? 
Just the core topic, no extra words.
Examples:
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

---

## 4. Configuration Integration

### 4.1 Settings-Based Prompt Override
**Location**: `/app/app/services/rag_service.py` Line 608
**Function**: `get_conversation_rag_response()`
**Purpose**: Allows system prompt customization via settings
```python
system_prompt = getattr(settings, 'RAG_SYSTEM_PROMPT', DEFAULT_RAG_SYSTEM_PROMPT)
```

---

## 5. Prompt Template Structures

### 5.1 Standard RAG Template Structure
```python
ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("human", "Context: {context}")
])
```

### 5.2 Contextualization Template Structure
```python
ChatPromptTemplate.from_messages([
    ("system", contextualize_q_system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])
```

### 5.3 Streaming Template Structure
```python
ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant..."),
    ("system", "Context information is below.\n{context}"),
    ("system", "Previous conversation history:\n{chat_history}"),
    ("human", "{input}")
])
```

---

## 6. Language Support

The codebase contains prompts in multiple languages:
- **English**: Primary language for most prompts
- **Indonesian**: Specific contextualization prompt in `create_rag_chain()`

### 6.1 Multi-language Considerations
- Title generation prompts explicitly instruct to "Use the same language as the user's messages"
- Contextualization includes both English and Indonesian versions
- System respects user's language preference for responses

---

## 7. Thinking Mode Integration

All headline/title generation functions automatically disable thinking mode:
```python
llm = get_llm(db, override_thinking=False)
```

This prevents thinking output from interfering with title generation endpoints.

---

## 8. Prompt Categories Summary

| Category | Count | Purpose |
|----------|-------|---------|
| RAG System Prompts | 6 | Answer questions using retrieved context |
| Contextualization Prompts | 3 | Create standalone questions from chat history |
| Title Generation Prompts | 5 | Generate conversation titles/headlines |
| QA System Prompts | 2 | Direct question answering with context |
| Streaming Prompts | 1 | Real-time response generation |

**Total Unique Prompts**: 17

---

## 9. Best Practices Observed

1. **Consistency**: Similar prompts share common instruction patterns
2. **Language Awareness**: Prompts instruct to maintain user's language
3. **Context Limitation**: Clear instructions about staying within provided context
4. **Conciseness**: Title prompts specifically request short, focused outputs
5. **Safety**: Instructions to avoid making up information when context is insufficient
6. **Flexibility**: Settings-based prompt override capability for customization

---

## 10. Configuration Hooks

The system provides configuration hooks for prompt customization:

1. **Settings Override**: `RAG_SYSTEM_PROMPT` in settings can override default
2. **Database Config**: Admin can potentially configure prompts via admin settings
3. **Environment Variables**: Could be extended to support env-based prompt configuration
