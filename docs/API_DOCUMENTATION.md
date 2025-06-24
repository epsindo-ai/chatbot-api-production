# API Documentation

This document provides comprehensive API documentation for the FastAPI LLM Chatbot with RAG capabilities.

## Table of Contents

1. [Authentication Endpoints](#authentication)
2. [Configuration Endpoints](#configuration)  
3. [LLM Configuration Endpoints](#llm-configuration)
4. [Collections (User) Endpoints](#collections-user)
5. [Admin Collections Endpoints](#admin-collections)
6. [Admin Users Endpoints](#admin-users)
7. [Chat Endpoints](#chat)
8. [Admin Files Endpoints](#admin-files)

---

## Authentication

Authentication endpoints handle user registration, login, and user information management.

### POST /api/auth/token

**Description**: Login with form data (OAuth2 compatible) to obtain access token.

**Request Body** (Form Data):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | User's username |
| `password` | string | Yes | User's password |

**Response**: `UserLoginResponse`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "role": "USER",
  "expires_in": 1800,
  "is_active": true,
  "must_reset_password": false,
  "is_temporary_password": false,
  "temp_password_expires_at": null
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT access token for authentication |
| `token_type` | string | Always "bearer" |
| `user_id` | integer | Unique user identifier |
| `username` | string | User's username |
| `email` | string, nullable | User's email address |
| `full_name` | string, nullable | User's full name |
| `role` | string | User role (USER, ADMIN, SUPER_ADMIN) |
| `expires_in` | integer | Token expiration time in seconds |
| `is_active` | boolean | Whether user account is active |
| `must_reset_password` | boolean | Whether user must reset password |
| `is_temporary_password` | boolean | Whether current password is temporary |
| `temp_password_expires_at` | string, nullable | ISO timestamp when temporary password expires |

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=securepassword123"
```

**Error Responses**:
```json
// 401 - Invalid credentials
{
  "detail": "Incorrect username or password"
}

// 401 - Account deactivated
{
  "detail": "Account has been deactivated. Please contact an administrator."
}

// 401 - Temporary password expired
{
  "detail": "Temporary password has expired. Please contact an administrator for a password reset."
}
```

---

### POST /api/auth/login

**Description**: Login with JSON body (alternative to /token endpoint).

**Request Body**:
```json
{
  "username": "john_doe",
  "password": "securepassword123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | User's username |
| `password` | string | Yes | User's password |

**Response**: Same as `/token` endpoint (`UserLoginResponse`)

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"john_doe","password":"securepassword123"}'
```

**Error Responses**: Same as `/token` endpoint

---

### POST /api/auth/signup

**Description**: Register a new user account.

**Request Body**:
```json
{
  "username": "new_user",
  "email": "user@example.com",
  "full_name": "New User",
  "password": "securepassword123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Unique username (3-50 characters) |
| `email` | string | No | Valid email address |
| `full_name` | string | No | User's full name |
| `password` | string | Yes | Password (minimum 8 characters) |

**Response**: `UserLoginResponse` (automatically logs in the new user)

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "new_user",
    "email": "user@example.com", 
    "full_name": "New User",
    "password": "securepassword123"
  }'
```

**Error Responses**:
```json
// 409 - Username conflict
{
  "detail": "Username already registered"
}

// 409 - Email conflict  
{
  "detail": "Email already registered"
}
```

---

### GET /api/auth/me

**Description**: Get information about the currently authenticated user.

**Authentication**: Bearer token required

**Response**: `UserInfo`
```json
{
  "user_id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "role": "USER",
  "is_active": true,
  "must_reset_password": false,
  "is_temporary_password": false,
  "temp_password_expires_at": null
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 401 - Invalid/expired token
{
  "detail": "Could not validate credentials"
}
```

---

### POST /api/auth/change-password

**Description**: Change password from temporary to permanent (token-based authentication).

**Authentication**: Bearer token required

**Request Body**:
```json
{
  "new_password": "newsecurepassword123",
  "confirm_password": "newsecurepassword123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `new_password` | string | Yes | New password (minimum 8 characters) |
| `confirm_password` | string | Yes | Must match new_password |

**Response**:
```json
{
  "message": "Password successfully changed",
  "user_id": 1,
  "username": "john_doe", 
  "must_reset_password": false,
  "is_temporary_password": false
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/auth/change-password" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "newsecurepassword123",
    "confirm_password": "newsecurepassword123"
  }'
```

**Error Responses**:
```json
// 400 - Passwords don't match
{
  "detail": "New password and confirmation do not match"
}

// 400 - Password too short
{
  "detail": "New password must be at least 8 characters long"
}

// 401 - Temporary password expired
{
  "detail": "Temporary password has expired. Please contact an administrator for a password reset."
}
```

---

## Configuration

Configuration endpoints manage unified system configuration including LLM, RAG, and general settings.

### GET /api/config/

**Description**: Get unified configuration including LLM, RAG, and general settings.

**Authentication**: Bearer token required (any authenticated user)

**Response**:
```json
{
  "llm": {
    "name": "Default LLM Config",
    "model_name": "gpt-3.5-turbo",
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 2048,
    "description": "Default LLM configuration",
    "extra_params": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-..."
    },
    "enable_thinking": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T14:25:00Z"
  },
  "rag": {
    "predefined_collection": "global_collection",
    "retriever_top_k": 5,
    "allow_user_uploads": true,
    "max_file_size_mb": 10,
    "global_collection_behavior": "auto_update"
  },
  "general": {
    "global_collection_rag_prompt": "You are a helpful AI assistant for the organizational knowledge base...",
    "user_collection_rag_prompt": "You are a helpful AI assistant. Use the documents provided by the user...",
    "regular_chat_prompt": "You are a helpful AI assistant. Provide clear, accurate, and helpful responses..."
  }
}
```

**Response Fields**:

**LLM Configuration**:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Configuration name identifier |
| `model_name` | string | LLM model name (e.g., "gpt-3.5-turbo") |
| `temperature` | float | Sampling temperature (0.0-2.0) |
| `top_p` | float | Nucleus sampling parameter (0.0-1.0) |
| `max_tokens` | integer, nullable | Maximum tokens in response |
| `description` | string, nullable | Configuration description |
| `extra_params` | object, nullable | Additional model parameters |
| `enable_thinking` | boolean | Whether thinking mode is enabled |
| `created_at` | string, nullable | ISO timestamp of creation |
| `updated_at` | string, nullable | ISO timestamp of last update |

**RAG Configuration**:

| Field | Type | Description |
|-------|------|-------------|
| `predefined_collection` | string | Default collection name |
| `retriever_top_k` | integer | Number of documents to retrieve |
| `allow_user_uploads` | boolean | Whether users can upload files |
| `max_file_size_mb` | integer | Maximum file size in MB |
| `global_collection_behavior` | string | "auto_update" or "readonly_on_change" |

**General Configuration**:

| Field | Type | Description |
|-------|------|-------------|
| `global_collection_rag_prompt` | string | System prompt for global collection RAG |
| `user_collection_rag_prompt` | string | System prompt for user collection RAG |
| `regular_chat_prompt` | string | System prompt for regular (non-RAG) chat |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/config/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### PUT /api/config/

**Description**: Update unified configuration. Admin users only.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Request Body**:
```json
{
  "llm": {
    "name": "Updated LLM Config",
    "model_name": "gpt-4",
    "temperature": 0.8,
    "top_p": 0.9,
    "max_tokens": 4096,
    "enable_thinking": true
  },
  "rag": {
    "retriever_top_k": 10,
    "allow_user_uploads": false,
    "max_file_size_mb": 20
  },
  "general": {
    "regular_chat_prompt": "You are an expert AI assistant..."
  }
}
```

**Response**: Updated unified configuration (same format as GET)

**Example Request**:
```bash
curl -X PUT "http://localhost:8000/api/config/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "llm": {
      "temperature": 0.8,
      "enable_thinking": true
    },
    "rag": {
      "retriever_top_k": 10
    }
  }'
```

**Error Responses**:
```json
// 403 - Insufficient permissions
{
  "detail": "Admin access required"
}
```

---

### GET /api/config/{category}

**Description**: Get configuration for a specific category (llm, rag, general).

**Authentication**: Bearer token required (any authenticated user)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `category` | string | path | Configuration category ("llm", "rag", "general") |

**Response** (for category="llm"):
```json
{
  "llm": {
    "name": "Default LLM Config",
    "model_name": "gpt-3.5-turbo",
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 2048,
    "description": "Default LLM configuration",
    "extra_params": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-..."
    },
    "enable_thinking": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T14:25:00Z"
  }
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/config/llm" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### PUT /api/config/{category}

**Description**: Update configuration for a specific category. Admin users only.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `category` | string | path | Configuration category ("llm", "rag", "general") |

**Request Body** (for category="llm"):
```json
{
  "name": "Updated LLM Config",
  "model_name": "gpt-4",
  "temperature": 0.8,
  "enable_thinking": true
}
```

**Response**: Updated category configuration

**Example Request**:
```bash
curl -X PUT "http://localhost:8000/api/config/llm" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 0.8,
    "enable_thinking": true
  }'
```

---

### GET /api/config/global-collection-behavior

**Description**: Get the current global collection behavior setting.

**Authentication**: Bearer token required (any authenticated user)

**Response**:
```json
{
  "behavior": "auto_update",
  "description": "Conversations automatically use the latest global collection"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `behavior` | string | "auto_update" or "readonly_on_change" |
| `description` | string | Human-readable description of the behavior |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/config/global-collection-behavior" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### PUT /api/config/global-collection-behavior

**Description**: Set the global collection behavior. Admin users only.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Request Body**:
```json
{
  "behavior": "readonly_on_change"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `behavior` | string | Yes | "auto_update" or "readonly_on_change" |

**Query Parameters** (alternative):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `behavior` | string | Yes | "auto_update" or "readonly_on_change" |

**Response**:
```json
{
  "behavior": "readonly_on_change",
  "message": "Global collection behavior set to 'readonly_on_change'"
}
```

**Example Request**:
```bash
curl -X PUT "http://localhost:8000/api/config/global-collection-behavior" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"behavior": "readonly_on_change"}'
```

**Error Responses**:
```json
// 400 - Invalid behavior
{
  "detail": "Behavior must be either 'auto_update' or 'readonly_on_change'"
}

// 400 - Missing behavior parameter
{
  "detail": "Behavior must be provided either as query parameter or in request body"
}
```

---

## LLM Configuration

LLM Configuration endpoints manage language model settings and parameters.

### GET /api/llm-config/

**Description**: Get the current LLM configuration. Admin users only.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Response**: `LLMConfig`
```json
{
  "name": "Default LLM Config",
  "model_name": "gpt-3.5-turbo",
  "temperature": 0.7,
  "top_p": 1.0,
  "max_tokens": 2048,
  "description": "Default LLM configuration",
  "extra_params": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-..."
  },
  "enable_thinking": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:25:00Z"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Configuration name identifier |
| `model_name` | string | LLM model name (e.g., "gpt-3.5-turbo", "gpt-4") |
| `temperature` | float | Sampling temperature, controls randomness (0.0-2.0) |
| `top_p` | float | Nucleus sampling parameter (0.0-1.0) |
| `max_tokens` | integer, nullable | Maximum tokens in response |
| `description` | string, nullable | Human-readable description |
| `extra_params` | object, nullable | Additional model-specific parameters |
| `enable_thinking` | boolean | Whether thinking mode is enabled |
| `created_at` | string | ISO timestamp of creation |
| `updated_at` | string, nullable | ISO timestamp of last update |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/llm-config/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 403 - Insufficient permissions
{
  "detail": "Admin access required"
}
```

---

### GET /api/llm-config/public

**Description**: Get a limited view of LLM configuration for regular users.

**Authentication**: Bearer token required (any authenticated user)

**Response**:
```json
{
  "model_name": "gpt-3.5-turbo",
  "temperature": 0.7,
  "top_p": 1.0,
  "max_tokens": 2048,
  "enable_thinking": false
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `model_name` | string | LLM model name |
| `temperature` | float | Sampling temperature |
| `top_p` | float | Nucleus sampling parameter |
| `max_tokens` | integer, nullable | Maximum tokens in response |
| `enable_thinking` | boolean | Whether thinking mode is enabled |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/llm-config/public" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### PUT /api/llm-config/

**Description**: Update the LLM configuration. Admin users only.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Request Body** (all fields optional):
```json
{
  "name": "Updated LLM Config",
  "model_name": "gpt-4",
  "temperature": 0.8,
  "top_p": 0.9,
  "max_tokens": 4096,
  "description": "Updated configuration for GPT-4",
  "extra_params": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-new-key...",
    "timeout": 30
  },
  "enable_thinking": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Configuration name identifier |
| `model_name` | string | No | LLM model name |
| `temperature` | float | No | Sampling temperature (0.0-2.0) |
| `top_p` | float | No | Nucleus sampling parameter (0.0-1.0) |
| `max_tokens` | integer | No | Maximum tokens in response |
| `description` | string | No | Human-readable description |
| `extra_params` | object | No | Additional model-specific parameters |
| `enable_thinking` | boolean | No | Whether to enable thinking mode |

**Response**: Updated `LLMConfig` (same format as GET)

**Example Request**:
```bash
curl -X PUT "http://localhost:8000/api/llm-config/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "gpt-4",
    "temperature": 0.8,
    "enable_thinking": true
  }'
```

**Error Responses**:
```json
// 403 - Insufficient permissions
{
  "detail": "Admin access required"
}

// 404 - Configuration not found
{
  "detail": "Configuration not found"
}
```

---

## Collections (User)

Collections endpoints allow users to manage their conversation-based file collections. These are collections created automatically when users upload files to conversations.

### GET /api/collections/global-default

**Description**: Get the current global default collection used for knowledge base conversations.

**Authentication**: Bearer token required (any authenticated user)

**Response**: `Collection`
```json
{
  "id": 1,
  "name": "global_knowledge_base",
  "description": "Main organizational knowledge base",
  "user_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:25:00Z",
  "is_active": true,
  "is_admin_only": false,
  "is_global_default": true
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique collection identifier |
| `name` | string | Collection name |
| `description` | string, nullable | Collection description |
| `user_id` | integer | ID of the user who created the collection |
| `created_at` | string | ISO timestamp of creation |
| `updated_at` | string, nullable | ISO timestamp of last update |
| `is_active` | boolean | Whether collection is active |
| `is_admin_only` | boolean | Whether collection is admin-only |
| `is_global_default` | boolean | Whether this is the global default collection |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/collections/global-default" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - No global default collection
{
  "detail": "No global default collection has been defined"
}
```

---

### GET /api/collections/

**Description**: Get user's own conversation-based collections. Returns collections created from the user's file uploads to conversations.

**Authentication**: Bearer token required (any authenticated user)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skip` | integer | No | Number of records to skip (default: 0) |
| `limit` | integer | No | Maximum number of records to return (default: 100) |

**Response**: Array of collection objects
```json
[
  {
    "conversation_id": "abc123def",
    "collection_name": "conversation_abc123def",
    "headline": "My Document Analysis",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T14:25:00Z",
    "file_count": 3,
    "processed_file_count": 3,
    "is_ready": true,
    "files": [
      {
        "id": 123,
        "filename": "document1.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "is_processed": true,
        "created_at": "2024-01-15T10:30:00Z"
      }
    ]
  }
]
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | string | Unique conversation identifier |
| `collection_name` | string | Generated collection name for conversation |
| `headline` | string, nullable | Conversation title or "Untitled Conversation" |
| `created_at` | string | ISO timestamp of conversation creation |
| `updated_at` | string, nullable | ISO timestamp of last update |
| `file_count` | integer | Total number of files in conversation |
| `processed_file_count` | integer | Number of files processed for RAG |
| `is_ready` | boolean | Whether all files are processed and ready |
| `files` | array | Array of file objects in the conversation |

**File Object Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique file identifier |
| `filename` | string | Current filename |
| `file_size` | integer | File size in bytes |
| `mime_type` | string | MIME type of the file |
| `is_processed` | boolean | Whether file is processed for RAG |
| `created_at` | string | ISO timestamp of file upload |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/collections/?skip=0&limit=10" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/collections/{conversation_id}

**Description**: Get detailed information about a user's conversation-based collection. Shows all files in the conversation/collection and their processing status.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Response**:
```json
{
  "conversation_id": "abc123def",
  "collection_name": "conversation_abc123def",
  "headline": "My Document Analysis",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:25:00Z",
  "conversation_type": "USER_FILES",
  "file_count": 3,
  "processed_file_count": 3,
  "is_ready": true,
  "milvus_collection": {
    "exists": true,
    "name": "conversation_abc123def"
  },
  "files": [
    {
      "id": 123,
      "filename": "document1.pdf",
      "file_path": "user123/abc123def/document1.pdf",
      "file_size": 1024000,
      "mime_type": "application/pdf",
      "created_at": "2024-01-15T10:30:00Z",
      "is_processed": true,
      "chunk_count": 15,
      "processed_at": "2024-01-15T10:32:00Z",
      "download_url": "/api/collections/abc123def/files/123/download"
    }
  ]
}
```

**Extended Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `conversation_type` | string | Type of conversation ("USER_FILES", "REGULAR", "GLOBAL_COLLECTION") |
| `milvus_collection` | object | Information about Milvus collection status |
| `milvus_collection.exists` | boolean | Whether collection exists in Milvus |
| `milvus_collection.name` | string | Sanitized collection name in Milvus |
| `file_path` | string | Full path to file in storage |
| `chunk_count` | integer | Number of text chunks created from file |
| `processed_at` | string, nullable | ISO timestamp when file was processed |
| `download_url` | string | Secure download URL for the file |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/collections/abc123def" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - Conversation not found
{
  "detail": "Conversation abc123def not found"
}

// 403 - Access denied
{
  "detail": "You don't have access to this conversation"
}

// 404 - No files in conversation
{
  "detail": "No files found in this conversation"
}
```

---

### DELETE /api/collections/{conversation_id}/files/{file_id}

**Description**: Remove a file from user's conversation collection. This will remove the file from the database, optionally delete it from storage, and optionally remove its vectors from the vector store.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |
| `file_id` | integer | path | Unique file identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `delete_from_minio` | boolean | No | Whether to delete file from MinIO storage (default: true) |
| `delete_from_vectorstore` | boolean | No | Whether to remove file vectors from Milvus (default: true) |

**Response**:
```json
{
  "detail": "File removed successfully",
  "file_id": 123,
  "conversation_id": "abc123def",
  "deleted_from_minio": true,
  "deleted_from_vectorstore": true
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `detail` | string | Success message |
| `file_id` | integer | ID of the removed file |
| `conversation_id` | string | ID of the conversation |
| `deleted_from_minio` | boolean | Whether file was deleted from MinIO |
| `deleted_from_vectorstore` | boolean | Whether vectors were removed from Milvus |

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/collections/abc123def/files/123?delete_from_minio=true&delete_from_vectorstore=true" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - Conversation not found
{
  "detail": "Conversation abc123def not found"
}

// 403 - Access denied
{
  "detail": "You don't have access to this conversation"
}

// 404 - File not found
{
  "detail": "File with ID 123 not found"
}

// 400 - File doesn't belong to conversation
{
  "detail": "File does not belong to this conversation"
}
```

---

### DELETE /api/collections/{conversation_id}/collection

**Description**: Delete a user's entire conversation collection. This removes all files from the conversation, deletes them from storage and vector store, and optionally removes the Milvus collection.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `delete_from_milvus` | boolean | No | Whether to delete collection from Milvus (default: true) |

**Response**:
```json
{
  "detail": "Conversation collection deleted successfully",
  "conversation_id": "abc123def",
  "collection_name": "conversation_abc123def",
  "deleted_files_count": 3,
  "deleted_files": [
    {
      "id": 123,
      "filename": "document1.pdf",
      "file_path": "user123/abc123def/document1.pdf"
    }
  ],
  "deleted_from_milvus": true
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `detail` | string | Success message |
| `conversation_id` | string | ID of the conversation |
| `collection_name` | string | Name of the deleted collection |
| `deleted_files_count` | integer | Number of files deleted |
| `deleted_files` | array | Array of deleted file objects |
| `deleted_from_milvus` | boolean | Whether Milvus collection was deleted |

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/collections/abc123def/collection?delete_from_milvus=true" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - Conversation not found
{
  "detail": "Conversation abc123def not found"
}

// 403 - Access denied
{
  "detail": "You don't have access to this conversation"
}

// 404 - No files to delete
{
  "detail": "No files found in this conversation to delete"
}
```

---

### GET /api/collections/{conversation_id}/files/{file_id}/download

**Description**: Securely download a file from user's conversation collection. This endpoint validates permissions and streams the file directly from storage.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |
| `file_id` | integer | path | Unique file identifier |

**Response**: Streaming file download with appropriate headers

**Headers**:
- `Content-Type`: File's MIME type or "application/octet-stream"
- `Content-Disposition`: attachment; filename="original_filename.ext"
- `Content-Length`: File size in bytes (if available)

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/collections/abc123def/files/123/download" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -o "downloaded_file.pdf"
```

**Error Responses**:
```json
// 404 - Conversation not found
{
  "detail": "Conversation abc123def not found"
}

// 403 - Access denied
{
  "detail": "You don't have access to this conversation"
}

// 404 - File not found
{
  "detail": "File with ID 123 not found"
}

// 500 - Download failed
{
  "detail": "Failed to download file from storage"
}
```

---

## Admin Collections

Admin Collections endpoints allow administrators to manage knowledge base collections and upload files for the global collection system. These are admin-only endpoints for managing the organizational knowledge base.

### GET /api/admin/collections/

**Description**: List all collections in the system with their files. Admin users only.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skip` | integer | No | Number of records to skip (default: 0) |
| `limit` | integer | No | Maximum number of records to return (default: 100) |
| `include_files` | boolean | No | Whether to include file details (default: true) |

**Response**: Array of `CollectionWithFiles` objects
```json
[
  {
    "id": 1,
    "name": "global_knowledge_base",
    "description": "Main organizational knowledge base",
    "user_id": 1,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T14:25:00Z",
    "is_active": true,
    "is_admin_only": true,
    "is_global_default": true,
    "files": [
      {
        "id": 123,
        "user_id": 1,
        "filename": "policy_doc_20240115103000.pdf",
        "original_filename": "company_policy.pdf",
        "file_path": "admin/1/policy_doc_20240115103000.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "created_at": "2024-01-15T10:30:00Z",
        "file_metadata": {
          "is_admin_upload": true,
          "is_processed_for_rag": true,
          "chunk_count": 15
        },
        "conversation_id": null
      }
    ]
  }
]
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique collection identifier |
| `name` | string | Collection name |
| `description` | string, nullable | Collection description |
| `user_id` | integer | ID of the admin who created the collection |
| `created_at` | string | ISO timestamp of creation |
| `updated_at` | string, nullable | ISO timestamp of last update |
| `is_active` | boolean | Whether collection is active |
| `is_admin_only` | boolean | Always true for admin collections |
| `is_global_default` | boolean | Whether this is the global default collection |
| `files` | array | Array of file objects in the collection |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/collections/?skip=0&limit=10&include_files=true" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /api/admin/collections/

**Description**: Create a new admin collection (without files). For creating collections with files, use the `/with-files` or `/upload-and-create` endpoints.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Request Body**:
```json
{
  "name": "new_knowledge_base",
  "description": "Additional knowledge base collection",
  "is_active": true,
  "is_global_default": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique collection name |
| `description` | string | No | Collection description |
| `is_active` | boolean | No | Whether collection is active (default: true) |
| `is_global_default` | boolean | No | Whether to set as global default (default: false) |

**Response**: `Collection`
```json
{
  "id": 2,
  "name": "new_knowledge_base",
  "description": "Additional knowledge base collection",
  "user_id": 1,
  "created_at": "2024-01-20T15:30:00Z",
  "updated_at": null,
  "is_active": true,
  "is_admin_only": true,
  "is_global_default": false
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/admin/collections/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new_knowledge_base",
    "description": "Additional knowledge base collection",
    "is_global_default": false
  }'
```

**Error Responses**:
```json
// 400 - Collection name conflict
{
  "detail": "Collection with name 'new_knowledge_base' already exists"
}
```

---

### POST /api/admin/collections/with-files

**Description**: Create a new admin collection and process selected existing files in one operation. This is the recommended way to create collections as it's more efficient.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Request Body** (multipart/form-data):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique collection name |
| `description` | string | No | Collection description |
| `file_ids` | array[integer] | Yes | List of file IDs from storage to include |
| `is_global_default` | boolean | No | Whether to set as global default (default: false) |

**Response**:
```json
{
  "collection": {
    "id": 3,
    "name": "policy_collection",
    "description": "Company policies and procedures",
    "is_global_default": true,
    "created_at": "2024-01-20T16:00:00Z"
  },
  "processing_summary": {
    "total_files": 3,
    "processed_successfully": 3,
    "failed": 0,
    "total_chunks_created": 45
  },
  "processed_files": [
    {
      "file_id": 123,
      "filename": "company_policy.pdf",
      "chunks_processed": 15
    }
  ],
  "failed_files": [],
  "milvus_collection_name": "admin_policy_collection",
  "message": "Collection 'policy_collection' created successfully with 3 files processed"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `collection` | object | Basic collection information |
| `processing_summary` | object | Summary of file processing results |
| `processed_files` | array | Successfully processed files with chunk counts |
| `failed_files` | array | Files that failed processing with error details |
| `milvus_collection_name` | string | Name of the collection in Milvus vector store |
| `message` | string | Success message with summary |

**Processing Summary Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `total_files` | integer | Total number of files provided |
| `processed_successfully` | integer | Number of files processed successfully |
| `failed` | integer | Number of files that failed processing |
| `total_chunks_created` | integer | Total text chunks created across all files |

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/admin/collections/with-files" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "name=policy_collection" \
  -F "description=Company policies and procedures" \
  -F "file_ids=123" \
  -F "file_ids=124" \
  -F "file_ids=125" \
  -F "is_global_default=true"
```

**Error Responses**:
```json
// 400 - Collection name conflict
{
  "detail": "Collection with name 'policy_collection' already exists"
}

// 404 - File not found
{
  "detail": "File with ID 123 not found"
}

// 500 - No files processed
{
  "detail": "Failed to process any files for the collection"
}
```

---

### POST /api/admin/collections/upload-and-create

**Description**: Upload files and create a new admin collection in one operation. Returns immediately and processes everything in the background.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Request Body** (multipart/form-data):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique collection name |
| `description` | string | No | Collection description |
| `files` | array[file] | Yes | Files to upload and process |
| `is_global_default` | boolean | No | Whether to set as global default (default: false) |

**Response** (Immediate):
```json
{
  "status": "processing",
  "message": "Collection 'new_collection' creation started. All 5 files are being processed in the background.",
  "total_files": 5,
  "collection_name": "new_collection",
  "note": "Use GET /api/admin/collections/status/new_collection to check processing status"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always "processing" for this endpoint |
| `message` | string | Description of background processing |
| `total_files` | integer | Number of files being processed |
| `collection_name` | string | Name of the collection being created |
| `note` | string | Instructions for checking status |

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/admin/collections/upload-and-create" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "name=new_collection" \
  -F "description=New knowledge base" \
  -F "files=@/path/to/document1.pdf" \
  -F "files=@/path/to/document2.txt" \
  -F "is_global_default=false"
```

**Error Responses**:
```json
// 400 - Empty collection name
{
  "detail": "Collection name cannot be empty"
}

// 400 - No files provided
{
  "detail": "At least one file must be provided"
}

// 400 - Unsupported file type
{
  "detail": "Unsupported file type: .xyz. Supported types: .pdf, .txt, .doc, .docx, .csv, .md"
}
```

---

### GET /api/admin/collections/{collection_id}

**Description**: Get a specific admin collection with its files.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `collection_id` | integer | path | Unique collection identifier |

**Response**: `CollectionWithFiles`
```json
{
  "id": 1,
  "name": "global_knowledge_base",
  "description": "Main organizational knowledge base",
  "user_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:25:00Z",
  "is_active": true,
  "is_admin_only": true,
  "is_global_default": true,
  "files": [
    {
      "id": 123,
      "filename": "policy_doc_20240115103000.pdf",
      "original_filename": "company_policy.pdf",
      "file_size": 1024000,
      "mime_type": "application/pdf",
      "file_metadata": {
        "is_processed_for_rag": true,
        "chunk_count": 15
      }
    }
  ]
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/collections/1" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - Collection not found
{
  "detail": "Collection with ID 1 not found"
}

// 400 - Not an admin collection
{
  "detail": "This is not an admin collection"
}
```

---

### PUT /api/admin/collections/{collection_id}

**Description**: Update an admin collection metadata. This only updates metadata; to add/remove files, use the unified creation endpoints.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `collection_id` | integer | path | Unique collection identifier |

**Request Body**:
```json
{
  "name": "updated_collection_name",
  "description": "Updated description",
  "is_active": true,
  "is_global_default": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Collection name (must be unique if changed) |
| `description` | string | No | Collection description |
| `is_active` | boolean | No | Whether collection is active |
| `is_global_default` | boolean | No | Whether to set as global default |

**Response**: `Collection` (updated collection)

**Example Request**:
```bash
curl -X PUT "http://localhost:8000/api/admin/collections/1" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated knowledge base description",
    "is_global_default": true
  }'
```

**Error Responses**:
```json
// 404 - Collection not found
{
  "detail": "Collection with ID 1 not found"
}

// 400 - Name conflict
{
  "detail": "Collection with name 'updated_name' already exists"
}
```

---

### DELETE /api/admin/collections/{collection_id}

**Description**: Delete an admin collection. Cannot delete the current global default collection for system safety.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `collection_id` | integer | path | Unique collection identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `force` | boolean | No | Force delete even if conversations are linked (default: false) |

**Response**:
```json
{
  "detail": "Collection deleted successfully",
  "collection_name": "old_collection",
  "milvus_collection_name": "admin_old_collection",
  "unlinked_conversations": 3
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `detail` | string | Success message |
| `collection_name` | string | Name of the deleted collection |
| `milvus_collection_name` | string | Name of the deleted Milvus collection |
| `unlinked_conversations` | integer | Number of conversations unlinked (if force=true) |

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/admin/collections/2?force=true" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 400 - Cannot delete global default
{
  "detail": "Cannot delete the current global default collection. Please set another collection as global default first."
}

// 400 - Conversations linked
{
  "detail": "Cannot delete collection: 5 conversations are linked to this collection. Use force=true to unlink them first."
}
```

---

### GET /api/admin/collections/status/{collection_name}

**Description**: Check the status of a collection creation process (for background operations).

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `collection_name` | string | path | Name of the collection to check |

**Response**:
```json
{
  "status": "completed",
  "message": "Collection 'new_collection' creation completed successfully. All 3 files processed.",
  "collection": {
    "id": 4,
    "name": "new_collection",
    "description": "New knowledge base",
    "is_global_default": false,
    "created_at": "2024-01-20T17:00:00Z"
  },
  "summary": {
    "total_files": 3,
    "processed_files": 3,
    "failed_files": 0,
    "pending_files": 0
  },
  "files": [
    {
      "file_id": 126,
      "filename": "document1.pdf",
      "is_processed": true,
      "chunk_count": 12,
      "processing_error": null,
      "processed_at": "2024-01-20T17:02:00Z"
    }
  ]
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "not_found", "processing", "completed", "completed_with_errors", or "error" |
| `message` | string | Human-readable status description |
| `collection` | object, nullable | Collection details if created |
| `summary` | object | Processing progress summary |
| `files` | array | Detailed status of each file |

**File Status Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `file_id` | integer | Unique file identifier |
| `filename` | string | Original filename |
| `is_processed` | boolean | Whether file processing completed |
| `chunk_count` | integer | Number of text chunks created |
| `processing_error` | string, nullable | Error message if processing failed |
| `processed_at` | string, nullable | ISO timestamp of processing completion |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/collections/status/new_collection" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/admin/collections/{collection_id}/processing-status

**Description**: Check the processing status of files in an existing admin collection.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `collection_id` | integer | path | Unique collection identifier |

**Response**:
```json
{
  "status": "completed",
  "message": "Processing complete: 5/5 files",
  "summary": {
    "total_files": 5,
    "processed_files": 5,
    "pending_files": 0
  },
  "files": [
    {
      "file_id": 123,
      "filename": "company_policy.pdf",
      "is_processed": true,
      "chunk_count": 15,
      "processing_error": null
    }
  ]
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/collections/1/processing-status" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/admin/collections/milvus/collections

**Description**: List all collections directly from Milvus vector store. This shows the actual collections in Milvus, which may differ from database collections if there are sync issues.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Response**: Array of collection names
```json
[
  "admin_global_knowledge_base",
  "admin_policy_collection",
  "conversation_abc123def",
  "conversation_xyz789ghi"
]
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/collections/milvus/collections" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/admin/collections/milvus/stats

**Description**: Get statistics for all Milvus collections including row counts and schema information.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Response**: Array of collection statistics
```json
[
  {
    "name": "admin_global_knowledge_base",
    "stats": {
      "row_count": 245,
      "schema": {
        "fields": [
          {
            "name": "id",
            "dtype": "DataType.INT64",
            "description": "Primary key"
          },
          {
            "name": "embedding",
            "dtype": "DataType.FLOAT_VECTOR",
            "description": "Text embedding vector"
          }
        ],
        "description": "Knowledge base collection"
      },
      "description": "Main organizational knowledge base"
    }
  },
  {
    "name": "conversation_abc123",
    "error": "Collection load failed"
  }
]
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Collection name in Milvus |
| `stats` | object, nullable | Collection statistics (if accessible) |
| `error` | string, nullable | Error message (if inaccessible) |

**Stats Object Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `row_count` | integer | Number of vector entries in the collection |
| `schema` | object | Collection schema information |
| `description` | string | Collection description |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/collections/milvus/stats" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Admin Users

Admin Users endpoints allow administrators to manage user accounts, including creation, role management, deactivation, and comprehensive user statistics. These endpoints provide powerful user management capabilities for system administrators.

### GET /api/admin/users/

**Description**: List all users with comprehensive statistics for admin management. Users are automatically sorted by role priority.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skip` | integer | No | Number of users to skip (default: 0) |
| `limit` | integer | No | Maximum number of users to return (default: 100) |
| `include_stats` | boolean | No | Whether to include user statistics (default: true) |
| `active_only` | boolean | No | Only return active users (default: false) |

**Response**: Array of `UserStatsResponse` objects
```json
[
  {
    "user_id": 1,
    "username": "admin_user",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true,
    "created_at": "2024-01-10T08:00:00Z",
    "conversations_count": 25,
    "files_count": 8,
    "collections_count": 2,
    "total_file_size_mb": 15.6,
    "last_activity": "2024-01-20T14:30:00Z"
  },
  {
    "user_id": 2,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "conversations_count": 12,
    "files_count": 5,
    "collections_count": 0,
    "total_file_size_mb": 8.2,
    "last_activity": "2024-01-19T16:45:00Z"
  }
]
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | integer | Unique user identifier |
| `username` | string | User's username |
| `email` | string, nullable | User's email address |
| `role` | string | User role (user, admin, super_admin) |
| `is_active` | boolean | Whether user account is active |
| `created_at` | string | ISO timestamp of user creation |
| `conversations_count` | integer | Number of conversations created by user |
| `files_count` | integer | Number of files uploaded by user |
| `collections_count` | integer | Number of collections created by user |
| `total_file_size_mb` | float | Total file storage used in MB |
| `last_activity` | string, nullable | ISO timestamp of last activity |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/users/?skip=0&limit=50&include_stats=true&active_only=false" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/admin/users/{user_id}/stats

**Description**: Get detailed statistics for a specific user. Helpful for administrators to understand the impact of user operations.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | path | Unique user identifier |

**Response**: `UserStatsResponse`
```json
{
  "user_id": 2,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "conversations_count": 12,
  "files_count": 5,
  "collections_count": 0,
  "total_file_size_mb": 8.2,
  "last_activity": "2024-01-19T16:45:00Z"
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/users/2/stats" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - User not found
{
  "detail": "User with ID 2 not found"
}
```

---

### GET /api/admin/users/stats

**Description**: Get comprehensive user statistics including detailed breakdowns for system health monitoring.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Response**:
```json
{
  "summary": {
    "total_users": 150,
    "active_users": 142,
    "inactive_users": 8,
    "total_conversations": 1250,
    "total_files": 485,
    "total_collections": 12
  },
  "users_by_role": {
    "regular_users": 145,
    "admin_users": 4,
    "super_admin_users": 1
  },
  "active_users_by_role": {
    "active_regular_users": 138,
    "active_admin_users": 4,
    "active_super_admin_users": 1
  },
  "activity_metrics": {
    "users_with_recent_activity_30d": 98,
    "conversations_last_30d": 325,
    "users_potentially_inactive": 52,
    "activity_rate_percentage": 65.33
  },
  "storage_metrics": {
    "total_files": 485,
    "total_file_size_gb": 2.8,
    "admin_collections": 5,
    "user_collections": 7
  },
  "registration_trends": {
    "new_users_today": 2,
    "new_users_last_7d": 8,
    "growth_rate_7d": 5.33
  },
  "system_health": {
    "admin_coverage": 3.33,
    "active_user_ratio": 94.67,
    "avg_conversations_per_user": 8.33,
    "avg_files_per_user": 3.23
  }
}
```

**Response Fields**:

**Summary Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `total_users` | integer | Total number of users in system |
| `active_users` | integer | Number of active users |
| `inactive_users` | integer | Number of inactive users |
| `total_conversations` | integer | Total conversations across all users |
| `total_files` | integer | Total files across all users |
| `total_collections` | integer | Total collections across all users |

**Activity Metrics Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `users_with_recent_activity_30d` | integer | Users active in last 30 days |
| `conversations_last_30d` | integer | Conversations created in last 30 days |
| `users_potentially_inactive` | integer | Users with no recent activity |
| `activity_rate_percentage` | float | Percentage of users with recent activity |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/users/stats" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /api/admin/users/create-with-temp-password

**Description**: Create a new user account with a temporary password that must be changed on first login.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Request Body**:
```json
{
  "username": "new_user",
  "email": "newuser@example.com",
  "full_name": "New User",
  "role": "user",
  "temporary_password": "TempPass123!",
  "password_expires_hours": 24
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Unique username (3-50 characters) |
| `email` | string | No | Valid email address |
| `full_name` | string | No | User's full name |
| `role` | string | No | User role: "user" or "admin" (default: "user") |
| `temporary_password` | string | Yes | Temporary password (min 8 characters) |
| `password_expires_hours` | integer | No | Hours until password expires (default: 24) |

**Response**: `UserCreateResponse`
```json
{
  "user_id": 151,
  "username": "new_user",
  "email": "newuser@example.com",
  "full_name": "New User",
  "role": "user",
  "is_active": true,
  "temporary_password": "TempPass123!",
  "password_expires_at": "2024-01-21T15:30:00Z",
  "must_reset_password": true
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | integer | Unique identifier for the created user |
| `username` | string | Created username |
| `email` | string, nullable | User's email address |
| `full_name` | string, nullable | User's full name |
| `role` | string | Assigned user role |
| `is_active` | boolean | Whether account is active |
| `temporary_password` | string | The temporary password provided |
| `password_expires_at` | string, nullable | When the temporary password expires |
| `must_reset_password` | boolean | Whether user must reset password on login |

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/admin/users/create-with-temp-password" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "username": "new_user",
    "email": "newuser@example.com",
    "full_name": "New User",
    "role": "user",
    "temporary_password": "TempPass123!",
    "password_expires_hours": 24
  }'
```

**Error Responses**:
```json
// 409 - Username conflict
{
  "detail": "Username already registered"
}

// 403 - Role creation restriction
{
  "detail": "Only super admins can create admin accounts. Regular admins can only create regular user accounts."
}

// 403 - Super admin creation blocked
{
  "detail": "Cannot create super admin users via API. Only one super admin is allowed and is created during deployment."
}
```

---

### POST /api/admin/users/reset-password

**Description**: Reset a user's password to a temporary one that must be changed on first login.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Request Body**:
```json
{
  "user_id": 2,
  "temporary_password": "NewTempPass456!",
  "password_expires_hours": 48
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | integer | Yes | ID of user to reset password for |
| `temporary_password` | string | Yes | New temporary password |
| `password_expires_hours` | integer | No | Hours until password expires (default: 24) |

**Response**: `PasswordResetResponse`
```json
{
  "user_id": 2,
  "username": "john_doe",
  "temporary_password": "NewTempPass456!",
  "password_expires_at": "2024-01-22T15:30:00Z",
  "message": "Password has been reset. User must change password on next login."
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/admin/users/reset-password" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "temporary_password": "NewTempPass456!",
    "password_expires_hours": 48
  }'
```

**Error Responses**:
```json
// 404 - User not found
{
  "detail": "User not found"
}

// 403 - Super admin protection
{
  "detail": "Only super admins can reset super admin passwords"
}
```

---

### POST /api/admin/users/update-role

**Description**: Update a user's role. Super Admin only operation with strict security controls.

**Authentication**: Bearer token required (Super Admin only)

**Request Body**:
```json
{
  "username": "john_doe",
  "role": "admin"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Username of user to update |
| `role` | string | Yes | New role: "user" or "admin" |

**Response**: `UserStatsResponse` (updated user with statistics)

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/admin/users/update-role" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "role": "admin"
  }'
```

**Error Responses**:
```json
// 404 - User not found
{
  "detail": "User 'john_doe' not found"
}

// 403 - Super admin promotion blocked
{
  "detail": "Cannot promote users to super admin via API. Only one super admin is allowed and is created during deployment."
}

// 400 - Self-role change blocked
{
  "detail": "Cannot change your own role"
}

// 403 - Super admin demotion blocked
{
  "detail": "Cannot demote the super admin user. Super admin role is permanent."
}
```

---

### PATCH /api/admin/users/{user_id}/deactivate

**Description**: Deactivate a user account instead of deleting it. This is a safer alternative that preserves all user data.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | path | Unique user identifier |

**Response**:
```json
{
  "detail": "User 'john_doe' deactivated successfully",
  "user_id": 2,
  "username": "john_doe",
  "is_active": false,
  "note": "User data is preserved and can be reactivated if needed"
}
```

**Example Request**:
```bash
curl -X PATCH "http://localhost:8000/api/admin/users/2/deactivate" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 400 - Self-deactivation blocked
{
  "detail": "Cannot deactivate yourself"
}

// 403 - Admin protection
{
  "detail": "Only super admins can deactivate admin users. Regular admins can only deactivate regular users."
}

// 403 - Super admin protection
{
  "detail": "Cannot deactivate the super admin user. Super admin must remain active."
}
```

---

### PATCH /api/admin/users/{user_id}/reactivate

**Description**: Reactivate a previously deactivated user account, restoring full access.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | path | Unique user identifier |

**Response**:
```json
{
  "detail": "User 'john_doe' reactivated successfully",
  "user_id": 2,
  "username": "john_doe",
  "is_active": true,
  "note": "User can now log in and access all their data"
}
```

**Example Request**:
```bash
curl -X PATCH "http://localhost:8000/api/admin/users/2/reactivate" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### DELETE /api/admin/users/{user_id}

**Description**: Delete a user and optionally all their associated data. This is a destructive operation that cannot be undone.

**Authentication**: Bearer token required (Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | path | Unique user identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `delete_files` | boolean | No | Whether to delete user's files from storage (default: true) |
| `delete_conversations` | boolean | No | Whether to delete user's conversations (default: true) |
| `delete_collections` | boolean | No | Whether to delete user's collections from vector store (default: true) |
| `dry_run` | boolean | No | Preview deletion without actually deleting (default: false) |

**Response** (Normal deletion):
```json
{
  "detail": "User deleted successfully",
  "deleted_stats": {
    "user_id": 2,
    "username": "john_doe",
    "files_deleted": 5,
    "conversations_deleted": 12,
    "collections_deleted": 0,
    "milvus_collections_deleted": 1,
    "global_default_collections_found": 0,
    "linked_conversations_unlinked": 0,
    "errors": [],
    "warnings": [],
    "dry_run": false
  }
}
```

**Response** (Dry run):
```json
{
  "detail": "DRY RUN: User 'john_doe' deletion preview completed",
  "deleted_stats": {
    "user_id": 2,
    "username": "john_doe",
    "files_deleted": 5,
    "conversations_deleted": 12,
    "collections_deleted": 0,
    "dry_run": true,
    "total_file_size_mb": 8.2,
    "warnings": ["User owns 0 global collection(s)..."]
  },
  "impact_summary": {
    "files_to_delete": 5,
    "conversations_to_delete": 12,
    "collections_to_delete": 0,
    "global_collections_found": 0,
    "storage_to_free_mb": 8.2,
    "conversations_to_unlink": 0
  }
}
```

**Deletion Stats Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | integer | ID of the deleted user |
| `username` | string | Username of the deleted user |
| `files_deleted` | integer | Number of files deleted from storage |
| `conversations_deleted` | integer | Number of conversations deleted |
| `collections_deleted` | integer | Number of collections deleted |
| `milvus_collections_deleted` | integer | Number of vector store collections deleted |
| `linked_conversations_unlinked` | integer | Conversations unlinked from global collections |
| `errors` | array | Array of error messages if any operations failed |
| `warnings` | array | Array of warning messages |

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/admin/users/2?delete_files=true&delete_conversations=true&delete_collections=true&dry_run=false" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 400 - Self-deletion blocked
{
  "detail": "Cannot delete yourself"
}

// 403 - Super admin protection
{
  "detail": "Cannot delete the super admin user. Super admin is permanent and cannot be deleted."
}
```

---

### POST /api/admin/users/bulk-delete

**Description**: Delete multiple users in a single operation. Useful for cleaning up multiple inactive accounts.

**Authentication**: Bearer token required (Super Admin only)

**Request Body**:
```json
{
  "user_ids": [3, 4, 5],
  "delete_files": true,
  "delete_conversations": true,
  "delete_collections": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_ids` | array[integer] | Yes | List of user IDs to delete (max 50) |
| `delete_files` | boolean | No | Whether to delete users' files (default: true) |
| `delete_conversations` | boolean | No | Whether to delete users' conversations (default: true) |
| `delete_collections` | boolean | No | Whether to delete users' collections (default: true) |

**Response**:
```json
{
  "detail": "Bulk deletion completed: 2 successful, 0 failed, 1 skipped",
  "results": {
    "successful_deletions": [
      {
        "user_id": 3,
        "username": "user3",
        "files_deleted": 2,
        "conversations_deleted": 5,
        "collections_deleted": 0,
        "milvus_collections_deleted": 0,
        "errors": []
      }
    ],
    "failed_deletions": [],
    "skipped_deletions": [
      {
        "user_id": 1,
        "username": "admin_user",
        "reason": "Cannot delete yourself"
      }
    ],
    "total_requested": 3,
    "total_successful": 2,
    "total_failed": 0,
    "total_skipped": 1,
    "summary_stats": {
      "total_files_deleted": 7,
      "total_conversations_deleted": 15,
      "total_collections_deleted": 0,
      "total_milvus_collections_deleted": 1
    }
  }
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/admin/users/bulk-delete" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": [3, 4, 5],
    "delete_files": true,
    "delete_conversations": true,
    "delete_collections": true
  }'
```

**Error Responses**:
```json
// 400 - No user IDs provided
{
  "detail": "No user IDs provided for deletion"
}

// 400 - Too many users
{
  "detail": "Cannot delete more than 50 users at once"
}

// 403 - Super admin in list
{
  "detail": "Cannot delete super admin user. Super admin is permanent and cannot be deleted."
}
```

---

### GET /api/admin/users/inactive

**Description**: List users who have been inactive for a specified number of days. Helps identify candidates for deactivation.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skip` | integer | No | Number of users to skip (default: 0) |
| `limit` | integer | No | Maximum number of users to return (default: 100) |
| `days_inactive` | integer | No | Consider users inactive after this many days (default: 30) |

**Response**: Array of `UserStatsResponse` objects (inactive users only)

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/users/inactive?days_inactive=60&limit=20" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### DELETE /api/admin/users/me/all-conversations

**Description**: Delete all user's own conversations and optionally associated collections and files. Users can only delete their own conversations.

**Authentication**: Bearer token required (any authenticated user)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `delete_collections` | boolean | No | Whether to delete collections and files (default: true) |

**Response**:
```json
{
  "detail": "All conversations deleted successfully",
  "deleted_stats": {
    "conversations_deleted": 8,
    "files_deleted": 12,
    "collections_deleted": 2,
    "errors": []
  }
}
```

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/admin/users/me/all-conversations?delete_collections=true" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /api/admin/users/generate-temp-password

**Description**: Generate a secure temporary password for admin use when creating accounts or resetting passwords.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Response**:
```json
{
  "temporary_password": "TmpPwd789!xY",
  "message": "Use this password when creating a user account or resetting a password. The user will be required to change it on first login."
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/admin/users/generate-temp-password" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Chat

Chat endpoints provide a unified interface for both regular chat and RAG-enabled chat with document collections. The system automatically determines whether to use RAG based on the conversation type and attached files.

### POST /api/chat/

**Description**: Unified chat endpoint that supports both regular chat and RAG-enabled chat. Automatically determines the appropriate mode based on conversation context.

**Authentication**: Bearer token required (any authenticated user)

**Request Body**:
```json
{
  "message": "What are the company's vacation policies?",
  "conversation_id": "abc123def456",
  "meta_data": {
    "user_preference": "detailed"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User's message/question |
| `conversation_id` | string | No | Existing conversation ID (creates new if not provided) |
| `meta_data` | object | No | Optional metadata for the conversation |

**Response**: `UnifiedChatResponse`
```json
{
  "status_code": 200,
  "error": null,
  "response": "According to the company handbook, employees are entitled to 15 vacation days per year for the first two years of employment...",
  "conversation_id": "abc123def456",
  "used_rag": true,
  "meta_data": {
    "sources_used": 3,
    "collection_type": "global"
  }
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `status_code` | integer | HTTP status code |
| `error` | string, nullable | Error message if any |
| `response` | string | AI assistant's response |
| `conversation_id` | string | Conversation identifier |
| `used_rag` | boolean | Whether RAG (retrieval) was used |
| `meta_data` | object, nullable | Additional response metadata |

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the company policies on remote work?",
    "conversation_id": "abc123def456"
  }'
```

**Chat Modes**:
- **Regular Chat**: No files or collections attached - uses base LLM
- **Global Collection RAG**: Conversation linked to admin knowledge base
- **User Files RAG**: Conversation has user-uploaded files
- **Auto-Detection**: System automatically chooses appropriate mode

**Error Responses**:
```json
// 423 - Read-only conversation (outdated global collection)
{
  "status_code": 423,
  "error": "The knowledge base has been updated. This conversation is now read-only. Please start a new conversation or migrate to the current knowledge base.",
  "response": "",
  "conversation_id": "abc123def456",
  "used_rag": false
}

// 400 - Files still processing
{
  "status_code": 400,
  "error": "Files are still being processed for this conversation. Please wait a moment and try again.",
  "response": "",
  "conversation_id": "abc123def456",
  "used_rag": false
}
```

---

### POST /api/chat/stream

**Description**: Streaming version of the unified chat endpoint. Returns real-time response chunks as they are generated.

**Authentication**: Bearer token required (any authenticated user)

**Request Body**: Same as `/api/chat/` endpoint

**Response**: Server-Sent Events (SSE) stream
```json
{"content": "According", "conversation_id": "abc123def456", "error": null, "finished": false}
{"content": " to the", "conversation_id": "abc123def456", "error": null, "finished": false}
{"content": " company handbook", "conversation_id": "abc123def456", "error": null, "finished": false}
{"content": "", "conversation_id": "abc123def456", "error": null, "finished": true}
```

**Response Stream Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `content` | string | Partial response content chunk |
| `conversation_id` | string | Conversation identifier |
| `error` | string, nullable | Error message if any |
| `finished` | boolean | Whether the response is complete |

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/chat/stream" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain the employee benefits package",
    "conversation_id": "abc123def456"
  }'
```

**JavaScript Example**:
```javascript
const response = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'What are the security policies?',
    conversation_id: 'abc123def456'
  })
});

const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = new TextDecoder().decode(value);
  const data = JSON.parse(chunk);
  
  if (data.finished) {
    console.log('Response complete');
    break;
  }
  
  console.log('Chunk:', data.content);
}
```

---

### POST /api/chat/initiate

**Description**: Create a new empty conversation that expires if not used. Ideal for starting fresh conversations.

**Authentication**: Bearer token required (any authenticated user)

**Request Body**: None

**Response**: `ConversationInitiateResponse`
```json
{
  "conversation_id": "new789ghi012",
  "expires_at": "2024-01-21T15:30:00Z"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | string | New conversation identifier |
| `expires_at` | string, nullable | ISO timestamp when conversation expires if unused |

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/chat/initiate" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /api/chat/initiate-with-global-collection

**Description**: Create a new conversation linked to the current global default collection for knowledge base chat.

**Authentication**: Bearer token required (any authenticated user)

**Request Body**: None

**Response**: `ConversationInitiateResponse`
```json
{
  "conversation_id": "global456xyz789",
  "expires_at": "2024-01-21T15:30:00Z"
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/chat/initiate-with-global-collection" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - No global collection configured
{
  "detail": "No predefined collection has been defined in the RAG configuration. Please contact an administrator."
}

// 404 - Global collection not found
{
  "detail": "Collection 'global_knowledge_base' defined in the RAG configuration was not found in the database. Please contact an administrator."
}
```

---

### GET /api/chat/conversations

**Description**: Get all conversations for the current user with optional filtering.

**Authentication**: Bearer token required (any authenticated user)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skip` | integer | No | Number of conversations to skip (default: 0) |
| `limit` | integer | No | Maximum conversations to return (default: 100) |
| `include_empty` | boolean | No | Include conversations without messages (default: true) |

**Response**: Array of `Conversation` objects
```json
[
  {
    "id": "abc123def456",
    "user_id": 1,
    "headline": "Employee Benefits Discussion",
    "conversation_type": "global_collection",
    "created_at": "2024-01-20T10:30:00Z",
    "updated_at": "2024-01-20T14:25:00Z",
    "expires_at": null,
    "linked_global_collection_id": 1,
    "original_global_collection_name": "hr_policies"
  },
  {
    "id": "def456ghi789",
    "user_id": 1,
    "headline": "Product Documentation Chat",
    "conversation_type": "user_files",
    "created_at": "2024-01-19T16:45:00Z",
    "updated_at": "2024-01-19T17:20:00Z",
    "expires_at": null,
    "linked_global_collection_id": null,
    "original_global_collection_name": null
  }
]
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique conversation identifier |
| `user_id` | integer | ID of the user who owns the conversation |
| `headline` | string, nullable | Auto-generated conversation title |
| `conversation_type` | string | Type: "regular", "user_files", "global_collection" |
| `created_at` | string | ISO timestamp of creation |
| `updated_at` | string | ISO timestamp of last update |
| `expires_at` | string, nullable | When conversation expires (if unused) |
| `linked_global_collection_id` | integer, nullable | ID of linked global collection |
| `original_global_collection_name` | string, nullable | Original global collection name |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/chat/conversations?skip=0&limit=20&include_empty=false" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/chat/conversations/{conversation_id}

**Description**: Get a specific conversation with all its messages.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Response**: `ConversationWithMessages`
```json
{
  "id": "abc123def456",
  "user_id": 1,
  "headline": "Employee Benefits Discussion",
  "conversation_type": "global_collection",
  "created_at": "2024-01-20T10:30:00Z",
  "updated_at": "2024-01-20T14:25:00Z",
  "expires_at": null,
  "linked_global_collection_id": 1,
  "original_global_collection_name": "hr_policies",
  "messages": [
    {
      "id": 1,
      "conversation_id": "abc123def456",
      "role": "user",
      "content": "What are our vacation policies?",
      "timestamp": "2024-01-20T10:30:00Z"
    },
    {
      "id": 2,
      "conversation_id": "abc123def456",
      "role": "assistant",
      "content": "According to the company handbook, employees are entitled to 15 vacation days...",
      "timestamp": "2024-01-20T10:30:15Z"
    }
  ]
}
```

**Message Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique message identifier |
| `conversation_id` | string | Conversation this message belongs to |
| `role` | string | "user" or "assistant" |
| `content` | string | Message content |
| `timestamp` | string | ISO timestamp of message creation |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/chat/conversations/abc123def456" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - Conversation not found or access denied
{
  "detail": "Conversation not found"
}
```

---

### GET /api/chat/conversations/{conversation_id}/files

**Description**: Get a conversation with its associated files and file processing status.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Response**: `ConversationWithFiles`
```json
{
  "id": "def456ghi789",
  "user_id": 1,
  "headline": "Product Documentation Chat",
  "conversation_type": "user_files",
  "created_at": "2024-01-19T16:45:00Z",
  "updated_at": "2024-01-19T17:20:00Z",
  "files": [
    {
      "id": 123,
      "user_id": 1,
      "filename": "product_guide_20240119164500.pdf",
      "original_filename": "product_guide.pdf",
      "file_path": "1/def456ghi789/product_guide_20240119164500.pdf",
      "file_size": 2048000,
      "mime_type": "application/pdf",
      "created_at": "2024-01-19T16:45:00Z",
      "conversation_id": "def456ghi789",
      "file_metadata": {
        "is_processed_for_rag": true,
        "chunk_count": 25,
        "processed_at": "2024-01-19T16:47:00Z"
      }
    }
  ]
}
```

**File Metadata Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `is_processed_for_rag` | boolean | Whether file is processed for RAG |
| `chunk_count` | integer | Number of text chunks created |
| `processed_at` | string | ISO timestamp of processing completion |
| `processing_error` | string, nullable | Error message if processing failed |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/chat/conversations/def456ghi789/files" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /api/chat/upload-file

**Description**: Upload files to a conversation for RAG-enabled chat. Supports both synchronous and asynchronous processing.

**Authentication**: Bearer token required (any authenticated user)

**Request Body** (multipart/form-data):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | array[file] | Yes | Files to upload (max 3 files) |
| `conversation_id` | string | Yes | Conversation ID to attach files to |
| `sync_processing` | boolean | No | Wait for processing completion (default: true) |

**Response**: Array of file upload results
```json
[
  {
    "id": 124,
    "user_id": 1,
    "filename": "manual_20240120150000.pdf",
    "original_filename": "user_manual.pdf",
    "file_path": "1/def456ghi789/manual_20240120150000.pdf",
    "file_size": 1536000,
    "mime_type": "application/pdf",
    "created_at": "2024-01-20T15:00:00Z",
    "conversation_id": "def456ghi789",
    "file_metadata": {
      "is_processed_for_rag": true,
      "chunk_count": 18
    },
    "download_url": "/api/collections/def456ghi789/files/124/download",
    "processing_status": "completed"
  }
]
```

**Processing Status Values**:
- `completed`: File processed successfully (sync mode)
- `pending`: File queued for background processing (async mode)
- `failed`: Processing failed with error

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/chat/upload-file" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "files=@/path/to/document1.pdf" \
  -F "files=@/path/to/document2.txt" \
  -F "conversation_id=def456ghi789" \
  -F "sync_processing=true"
```

**Error Responses**:
```json
// 400 - Too many files
{
  "detail": "Too many files. Maximum allowed: 3, received: 5"
}

// 404 - Conversation not found
{
  "detail": "Conversation def456ghi789 not found"
}

// 400 - Unsupported file type
{
  "detail": "Unsupported file type: .xyz. Supported types: .pdf, .txt, .doc, .docx, .csv, .md"
}
```

---

### GET /api/chat/file-status/{conversation_id}

**Description**: Check the processing status of files in a conversation to determine if they're ready for RAG.

**Authentication**: Bearer token required (any authenticated user)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Response**:
```json
{
  "status": "ready",
  "message": "All files processed and ready",
  "files": [
    {
      "file_id": 123,
      "filename": "product_guide.pdf",
      "is_processed": true
    },
    {
      "file_id": 124,
      "filename": "user_manual.pdf",
      "is_processed": true
    }
  ]
}
```

**Status Values**:
- `ready`: All files processed and ready for RAG
- `processing`: Some files still being processed
- `no_files`: No files found for conversation
- `error`: Error checking file status

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/chat/file-status/def456ghi789" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### DELETE /api/chat/conversations/{conversation_id}

**Description**: Delete a specific conversation and all its associated data.

**Authentication**: Bearer token required (any authenticated user - can only delete own conversations, admins can delete any)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Response**:
```json
{
  "detail": "Conversation deleted successfully",
  "conversation_id": "def456ghi789",
  "conversation_type": "user_files",
  "deleted_files_count": 2,
  "user_id": 1
}
```

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/def456ghi789" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - Conversation not found
{
  "detail": "Conversation def456ghi789 not found"
}

// 403 - Access denied
{
  "detail": "You don't have permission to delete this conversation"
}
```

---

### DELETE /api/chat/conversations/all

**Description**: Delete multiple conversations with granular control over conversation types and cleanup options.

**Authentication**: Bearer token required (any authenticated user - can only delete own conversations)

**Request Body**:
```json
{
  "delete_files_and_collections": true,
  "delete_regular_chats": true,
  "delete_user_file_conversations": true,
  "delete_global_collection_conversations": false,
  "delete_null_conversations": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `delete_files_and_collections` | boolean | No | Delete files and vector collections (default: true) |
| `delete_regular_chats` | boolean | No | Delete regular chat conversations (default: true) |
| `delete_user_file_conversations` | boolean | No | Delete conversations with user files (default: true) |
| `delete_global_collection_conversations` | boolean | No | Delete global collection conversations (default: true) |
| `delete_null_conversations` | boolean | No | Delete orphaned conversations (default: true) |

**Response**:
```json
{
  "detail": "Successfully deleted 8 conversations (3 regular chat conversations, 2 user file conversations, 3 orphaned/null conversations)",
  "deleted_stats": {
    "conversations_deleted": 8,
    "files_deleted": 12,
    "collections_deleted": 2,
    "regular_conversations_deleted": 3,
    "user_files_conversations_deleted": 2,
    "global_collection_conversations_deleted": 0,
    "null_conversations_deleted": 3,
    "errors": []
  }
}
```

**Deletion Stats Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `conversations_deleted` | integer | Total conversations deleted |
| `files_deleted` | integer | Files removed from storage |
| `collections_deleted` | integer | Vector collections deleted |
| `regular_conversations_deleted` | integer | Regular chat conversations deleted |
| `user_files_conversations_deleted` | integer | User file conversations deleted |
| `global_collection_conversations_deleted` | integer | Global collection conversations deleted |
| `null_conversations_deleted` | integer | Orphaned conversations deleted |
| `errors` | array | Array of error messages if any operations failed |

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/all" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "delete_files_and_collections": true,
    "delete_regular_chats": true,
    "delete_user_file_conversations": true,
    "delete_global_collection_conversations": false,
    "delete_null_conversations": true
  }'
```

---

### POST /api/chat/conversations/{conversation_id}/generate-headline

**Description**: Manually generate or regenerate a headline for a conversation using AI.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Response**: `Conversation` (updated with new headline)

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/chat/conversations/abc123def456/generate-headline" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /api/chat/conversations/{conversation_id}/generate-final-headline

**Description**: Generate a comprehensive final headline considering the entire conversation context.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Response**: `Conversation` (updated with final headline)

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/chat/conversations/abc123def456/generate-final-headline" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /api/chat/conversations/{conversation_id}/migrate-to-current-global

**Description**: Update a conversation to use the current global default collection when it has changed.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Response**: `Conversation` (updated conversation)

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/chat/conversations/abc123def456/migrate-to-current-global" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 400 - Not a global collection conversation
{
  "detail": "This conversation is not linked to a global collection"
}

// 400 - Already up to date
{
  "detail": "This conversation is already using the current global collection"
}
```

---

### GET /api/chat/conversations/{conversation_id}/global-collection-status

**Description**: Get the global collection status for a conversation and available actions.

**Authentication**: Bearer token required (any authenticated user - can only access own conversations)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | path | Unique conversation identifier |

**Response**:
```json
{
  "conversation_type": "global_collection",
  "is_global_collection": true,
  "behavior": "readonly_on_change",
  "is_outdated": true,
  "original_collection_name": "old_knowledge_base",
  "current_global_collection_name": "new_knowledge_base",
  "linked_collection_id": 1,
  "can_migrate": true,
  "is_readonly": true,
  "auto_updates": false,
  "message": "This conversation is read-only because the global collection has changed. You can migrate to the current collection or start a new conversation."
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `conversation_type` | string | Type of conversation |
| `is_global_collection` | boolean | Whether linked to global collection |
| `behavior` | string | Global collection behavior setting |
| `is_outdated` | boolean | Whether conversation uses outdated collection |
| `original_collection_name` | string, nullable | Original collection name |
| `current_global_collection_name` | string, nullable | Current global collection name |
| `can_migrate` | boolean | Whether migration is available |
| `is_readonly` | boolean | Whether conversation is read-only |
| `auto_updates` | boolean | Whether conversation auto-updates |
| `message` | string | Human-readable status description |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/chat/conversations/abc123def456/global-collection-status" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/chat/system/health

**Description**: Check the health of all system components used by the chat system.

**Authentication**: None required

**Response**:
```json
{
  "status": "healthy",
  "timestamp": 1705834800.123,
  "components": {
    "database": {
      "status": "healthy"
    },
    "minio": {
      "status": "healthy",
      "buckets": 3
    },
    "milvus": {
      "status": "healthy",
      "collections": ["admin_global_kb", "conversation_abc123"]
    },
    "vllm": {
      "status": "healthy"
    },
    "infinity_embeddings": {
      "status": "healthy",
      "model": "BAAI/bge-small-en-v1.5"
    }
  }
}
```

**Status Values**:
- `healthy`: All components operational
- `degraded`: Some components have issues
- `unhealthy`: Critical components failing

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/chat/system/health"
```

---

## Admin Files

Admin Files endpoints allow administrators to manage all files in the system, including file uploads, downloads, and storage management.

### GET /api/admin/files/

**Description**: List all files in the system with optional search functionality. Admin users only.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skip` | integer | No | Number of records to skip (default: 0) |
| `limit` | integer | No | Maximum number of records to return (default: 100) |
| `search` | string | No | Filter by filename (partial match) |

**Response**: Array of `FileStorageResponse` objects
```json
[
  {
    "id": 123,
    "user_id": 1,
    "filename": "document1.pdf",
    "original_filename": "document1.pdf",
    "file_path": "admin/document1_20240115103000.pdf",
    "file_size": 1024000,
    "mime_type": "application/pdf",
    "created_at": "2024-01-15T10:30:00Z",
    "file_metadata": {
      "is_admin_upload": true,
      "is_processed_for_rag": true,
      "chunk_count": 15
    },
    "conversation_id": null,
    "download_url": "/api/admin/files/123/download"
  }
]
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique file identifier |
| `user_id` | integer | ID of user who uploaded the file |
| `filename` | string | Current filename in storage |
| `original_filename` | string | Original filename when uploaded |
| `file_path` | string | Full path to file in MinIO storage |
| `file_size` | integer | File size in bytes |
| `mime_type` | string | MIME type of the file |
| `created_at` | string | ISO timestamp of file upload |
| `file_metadata` | object, nullable | Additional metadata about the file |
| `conversation_id` | string, nullable | Associated conversation ID (if any) |
| `download_url` | string | Secure download URL for the file |

**File Metadata Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `is_admin_upload` | boolean | Whether file was uploaded by admin |
| `is_processed_for_rag` | boolean | Whether file is processed for RAG |
| `chunk_count` | integer | Number of text chunks created |
| `processing_error` | string | Error message if processing failed |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/files/?skip=0&limit=10&search=document" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/admin/files/minio

**Description**: List all files in MinIO storage with rich database information. Shows both database-tracked files and orphaned files that exist only in storage.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prefix` | string | No | Filter by file path prefix |

**Response**: Array of file objects with MinIO and database information
```json
[
  {
    "id": 123,
    "filename": "document1.pdf",
    "original_filename": "document1.pdf",
    "file_path": "admin/document1_20240115103000.pdf",
    "file_size": 1024000,
    "mime_type": "application/pdf",
    "created_at": "2024-01-15T10:30:00Z",
    "file_metadata": {
      "is_admin_upload": true
    },
    "conversation_id": null,
    "user_id": 1,
    "download_url": "/api/admin/files/123/download",
    "minio_metadata": {
      "etag": "9bb58f26192e4ba00f01e2e7b136bbd8",
      "last_modified_minio": "2024-01-15T10:30:00Z",
      "size_minio": 1024000
    },
    "collections": [
      {
        "collection_id": 1,
        "collection_name": "global_knowledge_base",
        "collection_description": "Main knowledge base",
        "is_processed": true,
        "added_at": "2024-01-15T10:30:00Z",
        "is_global_default": true,
        "is_admin_only": false
      }
    ]
  },
  {
    "name": "orphaned_file.pdf",
    "size": 512000,
    "last_modified": "2024-01-10T09:15:00Z",
    "etag": "abc123def456789",
    "download_url": "/api/admin/files/minio/orphaned_file.pdf",
    "is_orphaned": true,
    "filename": null,
    "original_filename": null,
    "file_path": "orphaned_file.pdf",
    "file_size": 512000,
    "mime_type": null,
    "file_metadata": null,
    "conversation_id": null,
    "id": null,
    "user_id": null,
    "created_at": null,
    "collections": []
  }
]
```

**Extended Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `minio_metadata` | object | MinIO-specific metadata |
| `minio_metadata.etag` | string | MinIO ETag for the file |
| `minio_metadata.last_modified_minio` | string | Last modified timestamp in MinIO |
| `minio_metadata.size_minio` | integer | File size reported by MinIO |
| `collections` | array | Collections this file belongs to |
| `is_orphaned` | boolean | Whether file exists only in MinIO (not in database) |

**Collection Association Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `collection_id` | integer | Unique collection identifier |
| `collection_name` | string | Collection name |
| `collection_description` | string, nullable | Collection description |
| `is_processed` | boolean | Whether file is processed in this collection |
| `added_at` | string | ISO timestamp when file was added to collection |
| `is_global_default` | boolean | Whether collection is global default |
| `is_admin_only` | boolean | Whether collection is admin-only |

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/files/minio?prefix=admin/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /api/admin/files/upload

**Description**: Upload a file as an admin to MinIO storage. This endpoint handles file upload and storage but does not process the file for RAG.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Request Body** (multipart/form-data):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | File to upload |

**Response**: `FileStorageResponse`
```json
{
  "id": 123,
  "user_id": 1,
  "filename": "document1_20240115103000.pdf",
  "original_filename": "document1.pdf",
  "file_path": "admin/document1_20240115103000.pdf",
  "file_size": 1024000,
  "mime_type": "application/pdf",
  "created_at": "2024-01-15T10:30:00Z",
  "file_metadata": {
    "is_admin_upload": true
  },
  "conversation_id": null,
  "download_url": "/api/admin/files/123/download"
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/admin/files/upload" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "file=@/path/to/document1.pdf"
```

**Error Responses**:
```json
// 500 - Upload failed
{
  "detail": "Failed to upload file to storage"
}
```

---

### DELETE /api/admin/files/{file_id}

**Description**: Delete a file from the system. Optionally also delete it from MinIO storage.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `file_id` | integer | path | Unique file identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `delete_from_minio` | boolean | No | Whether to delete file from MinIO storage (default: true) |

**Response**:
```json
{
  "detail": "File deleted successfully"
}
```

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/admin/files/123?delete_from_minio=true" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Error Responses**:
```json
// 404 - File not found
{
  "detail": "File with ID 123 not found"
}

// 500 - Delete failed
{
  "detail": "Failed to delete file from database"
}
```

---

### GET /api/admin/files/{file_id}/download

**Description**: Securely download a file by ID. Streams the file content directly from MinIO with proper authentication.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `file_id` | integer | path | Unique file identifier |

**Response**: Streaming file download with appropriate headers

**Headers**:
- `Content-Type`: File's MIME type or "application/octet-stream"
- `Content-Disposition`: attachment; filename="original_filename.ext"
- `Content-Length`: File size in bytes (if available)

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/files/123/download" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -o "downloaded_file.pdf"
```

**Error Responses**:
```json
// 404 - File not found
{
  "detail": "File with ID 123 not found"
}

// 500 - Download failed
{
  "detail": "Failed to download file from storage"
}
```

---

### GET /api/admin/files/minio/{file_path}

**Description**: Download an orphaned file directly from MinIO by its path. This is for files that exist in MinIO but not in the database.

**Authentication**: Bearer token required (Admin/Super Admin only)

**Parameters**:

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `file_path` | string | path | Full path to file in MinIO (can include slashes) |

**Response**: Streaming file download with appropriate headers

**Headers**:
- `Content-Type`: "application/octet-stream"
- `Content-Disposition`: attachment; filename="extracted_filename"

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/admin/files/minio/admin/orphaned_file.pdf" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -o "orphaned_file.pdf"
```

**Error Responses**:
```json
// 404 - File not found in storage
{
  "detail": "File not found in storage"
}
```

---

## Common Error Responses

### Authentication Errors

```json
// 401 - Missing or invalid token
{
  "detail": "Not authenticated"
}

// 401 - Invalid credentials
{
  "detail": "Could not validate credentials"
}

// 401 - Inactive user
{
  "detail": "Inactive user"
}
```

### Authorization Errors

```json
// 403 - Insufficient permissions
{
  "detail": "Admin access required"
}

// 403 - Super admin required
{
  "detail": "Super admin access required"
}
```

### Validation Errors

```json
// 422 - Request validation error
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Server Errors

```json
// 500 - Internal server error
{
  "detail": "Internal server error"
}
```

---

## Authentication

All protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### User Roles

- **USER**: Regular user with basic access
- **ADMIN**: Administrator with configuration access
- **SUPER_ADMIN**: Super administrator with full system access

### Token Expiration

- Regular users: 30 minutes (1800 seconds)
- Admin users: Configurable (typically longer)
- Tokens include expiration time in the login response (`expires_in`)

---

## Rate Limiting

The API may implement rate limiting on certain endpoints. Check response headers for rate limit information:

- `X-RateLimit-Limit`: Request limit per time window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

---

## SDKs and Integration

### JavaScript/TypeScript Example

```javascript
class APIClient {
  constructor(baseURL, token) {
    this.baseURL = baseURL;
    this.token = token;
  }

  async login(username, password) {
    const response = await fetch(`${this.baseURL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      this.token = data.access_token;
      return data;
    }
    throw new Error('Login failed');
  }

  async getConfig() {
    const response = await fetch(`${this.baseURL}/api/config/`, {
      headers: { 
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      return await response.json();
    }
    throw new Error('Failed to get config');
  }

  async updateLLMConfig(config) {
    const response = await fetch(`${this.baseURL}/api/llm-config/`, {
      method: 'PUT',
      headers: { 
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(config)
    });
    
    if (response.ok) {
      return await response.json();
    }
    throw new Error('Failed to update LLM config');
  }
}

// Usage
const client = new APIClient('http://localhost:8000');
await client.login('username', 'password');
const config = await client.getConfig();
```

### Python Example

```python
import requests
import json

class APIClient:
    def __init__(self, base_url, token=None):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()
    
    def login(self, username, password):
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })
        return data
    
    def get_config(self):
        response = self.session.get(f"{self.base_url}/api/config/")
        response.raise_for_status()
        return response.json()
    
    def update_llm_config(self, config):
        response = self.session.put(
            f"{self.base_url}/api/llm-config/",
            json=config
        )
        response.raise_for_status()
        return response.json()

# Usage
client = APIClient("http://localhost:8000")
client.login("username", "password")
config = client.get_config()
```

---

This documentation covers the core authentication, configuration, and LLM configuration endpoints. Each endpoint includes detailed request/response examples, field descriptions, and error handling information to help developers integrate with the API effectively.
