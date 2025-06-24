# API Documentation

This document provides comprehensive API documentation for the FastAPI LLM Chatbot with RAG capabilities.

## Table of Contents

1. [Authentication Endpoints](#authentication)
2. [Configuration Endpoints](#configuration)  
3. [LLM Configuration Endpoints](#llm-configuration)

---

## Authentication

Authentication endpoints handle user registration, login, and user information management.

### POST /api/auth/token

**Description**: Login with form data (OAuth2 compatible) to obtain access token.

**Request Body** (Form Data):
- `username` (string, required): User's username
- `password` (string, required): User's password

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
- `access_token` (string): JWT access token for authentication
- `token_type` (string): Always "bearer"
- `user_id` (integer): Unique user identifier
- `username` (string): User's username
- `email` (string, nullable): User's email address
- `full_name` (string, nullable): User's full name
- `role` (string): User role (USER, ADMIN, SUPER_ADMIN)
- `expires_in` (integer): Token expiration time in seconds
- `is_active` (boolean): Whether user account is active
- `must_reset_password` (boolean): Whether user must reset password
- `is_temporary_password` (boolean): Whether current password is temporary
- `temp_password_expires_at` (string, nullable): ISO timestamp when temporary password expires

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

**Request Fields**:
- `username` (string, required): Unique username (3-50 characters)
- `email` (string, optional): Valid email address
- `full_name` (string, optional): User's full name
- `password` (string, required): Password (minimum 8 characters)

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

**Request Fields**:
- `new_password` (string, required): New password (minimum 8 characters)
- `confirm_password` (string, required): Must match new_password

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
- `name` (string): Configuration name identifier
- `model_name` (string): LLM model name (e.g., "gpt-3.5-turbo")
- `temperature` (float): Sampling temperature (0.0-2.0)
- `top_p` (float): Nucleus sampling parameter (0.0-1.0)
- `max_tokens` (integer, nullable): Maximum tokens in response
- `description` (string, nullable): Configuration description
- `extra_params` (object, nullable): Additional model parameters
- `enable_thinking` (boolean): Whether thinking mode is enabled
- `created_at` (string, nullable): ISO timestamp of creation
- `updated_at` (string, nullable): ISO timestamp of last update

**RAG Configuration**:
- `predefined_collection` (string): Default collection name
- `retriever_top_k` (integer): Number of documents to retrieve
- `allow_user_uploads` (boolean): Whether users can upload files
- `max_file_size_mb` (integer): Maximum file size in MB
- `global_collection_behavior` (string): "auto_update" or "readonly_on_change"

**General Configuration**:
- `global_collection_rag_prompt` (string): System prompt for global collection RAG
- `user_collection_rag_prompt` (string): System prompt for user collection RAG  
- `regular_chat_prompt` (string): System prompt for regular (non-RAG) chat

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
- `category` (path): Configuration category ("llm", "rag", "general")

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
- `category` (path): Configuration category ("llm", "rag", "general")

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
- `behavior` (string): "auto_update" or "readonly_on_change"
- `description` (string): Human-readable description of the behavior

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

**Query Parameters** (alternative):
- `behavior` (string): "auto_update" or "readonly_on_change"

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
- `name` (string): Configuration name identifier  
- `model_name` (string): LLM model name (e.g., "gpt-3.5-turbo", "gpt-4")
- `temperature` (float): Sampling temperature, controls randomness (0.0-2.0)
- `top_p` (float): Nucleus sampling parameter (0.0-1.0)
- `max_tokens` (integer, nullable): Maximum tokens in response
- `description` (string, nullable): Human-readable description
- `extra_params` (object, nullable): Additional model-specific parameters
- `enable_thinking` (boolean): Whether thinking mode is enabled
- `created_at` (string): ISO timestamp of creation
- `updated_at` (string, nullable): ISO timestamp of last update

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
- `model_name` (string): LLM model name
- `temperature` (float): Sampling temperature
- `top_p` (float): Nucleus sampling parameter  
- `max_tokens` (integer, nullable): Maximum tokens in response
- `enable_thinking` (boolean): Whether thinking mode is enabled

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

**Request Fields** (all optional):
- `name` (string): Configuration name identifier
- `model_name` (string): LLM model name
- `temperature` (float): Sampling temperature (0.0-2.0)
- `top_p` (float): Nucleus sampling parameter (0.0-1.0)
- `max_tokens` (integer): Maximum tokens in response
- `description` (string): Human-readable description
- `extra_params` (object): Additional model-specific parameters
- `enable_thinking` (boolean): Whether to enable thinking mode

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
