# FastAPI LLM Chatbot with RAG Capabilities
This repository contains a FastAPI-based chatbot API with streaming and RAG (Retrieval Augmented Generation) capabilities.

## Model Architecture

The system uses two specialized models for different tasks:

1. **Infinity (Stella 1.5B)** for embedding generation
2. **vLLM API** (with models like Qwen 2.5-14B) for text generation

This approach uses each model for what it does best, creating an efficient RAG architecture.

### Embedding Service

The embedding functionality is exposed through a dedicated endpoint:

```
POST /api/chat/embeddings
```

This endpoint accepts text input and returns vector embeddings using the Infinity model. Sample request:

```json
{
  "text": "Your text to embed here",
  "model": "stella-en-1.5B"  // Optional, defaults to INFINITY_EMBEDDINGS_MODEL
}
```

The service also provides a health check endpoint:

```
GET /api/chat/embeddings/health
```

### Configuration

Configure the services using these environment variables:

```
# Infinity Embeddings Settings
INFINITY_EMBEDDINGS_MODEL=stella-en-1.5B
INFINITY_API_URL=http://192.168.1.10:33325
USE_INFINITY_EMBEDDINGS=True

# vLLM API Settings (using OpenAI-compatible API)
OPENAI_API_BASE=http://192.168.1.10:33315/v1
LLM_MODEL=epsindo.ai/qwen2.5-14b-inst-awq

# This points to Infinity for embeddings
REMOTE_EMBEDDER_URL=http://192.168.1.10:33325/embeddings
```

## Unified Configuration System

The application uses a unified configuration system that stores all settings in a single `admin_config` table. This replaces the previous approach of having separate tables for different types of configurations.

### Configuration Categories

Configurations are organized into categories:

- **llm**: LLM-related settings (model, temperature, etc.)
- **rag**: RAG-related settings (retriever settings, collections, etc.)
- **general**: General application settings

### API Endpoints

- `GET /api/config`: Get all configurations
- `PUT /api/config`: Update configurations (admin only)
- `GET /api/config/{category}`: Get configurations for a specific category
- `PUT /api/config/{category}`: Update configurations for a specific category (admin only)

### Migration

When upgrading from a previous version, run the following commands to migrate your data:

```bash
# Apply database migrations
alembic upgrade head

# Migrate data from llm_configs to admin_config
python app/scripts/migrate_to_unified_config.py
```

## Demo UI

A demo UI is available to showcase the unified chat functionality:

1. Login page: `/static/login.html`
2. Chat interface: `/static/unified-chat-demo.html`

The demo allows:
- File upload to MinIO
- Collection selection for RAG
- File-based RAG
- Custom metadata in requests
