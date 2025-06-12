# Enhanced Conversation Deletion API - Request Body Format

## Overview
The `DELETE /api/collections/all` endpoint has been enhanced to use **request body parameters** instead of query parameters for better organization, validation, and clearer naming.

## API Endpoint
```
DELETE /api/chat/conversations/all
```

## Request Format
The endpoint now accepts a JSON request body with the following schema:

### Request Body Schema
```json
{
  "delete_files_and_collections": boolean,
  "delete_regular_chats": boolean,
  "delete_user_file_conversations": boolean,
  "delete_global_collection_conversations": boolean,
  "delete_null_conversations": boolean
}
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `delete_files_and_collections` | boolean | `true` | Whether to also delete files and collections associated with conversations |
| `delete_regular_chats` | boolean | `true` | Whether to delete regular chat conversations (no files or collections) |
| `delete_user_file_conversations` | boolean | `true` | Whether to delete conversations with user-uploaded files and their collections |
| `delete_global_collection_conversations` | boolean | `true` | Whether to delete conversations linked to global collections (admin knowledge bases) |
| `delete_null_conversations` | boolean | `true` | Whether to delete orphaned conversations with null/missing conversation types (cleanup) |

## Key Improvements

### 1. **Better Parameter Names**
- `delete_files_and_collections` (was `delete_collections`) - More descriptive
- `delete_regular_chats` (was `include_regular`) - Clearer intent  
- `delete_user_file_conversations` (was `include_user_files`) - More specific
- `delete_global_collection_conversations` (was `include_global_collection`) - Self-explanatory

### 2. **Request Body Benefits**
- **Better Organization**: Parameters are grouped logically in a JSON structure
- **Validation**: Pydantic models provide automatic type validation
- **Documentation**: Better API schema documentation in OpenAPI/Swagger
- **Extensibility**: Easier to add new parameters in the future
- **Type Safety**: Stronger typing and validation compared to query parameters

### 3. **Consistent Naming Convention**
All parameters now follow the pattern `delete_[type]_[description]` for clarity.

## Usage Examples

### 1. Delete Everything (Default Behavior)
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/all" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delete_files_and_collections": true,
    "delete_regular_chats": true,
    "delete_user_file_conversations": true,
    "delete_global_collection_conversations": true,
    "delete_null_conversations": true
  }'
```

### 2. Delete Only Orphaned/Null Conversations (Cleanup)
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/all" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delete_files_and_collections": false,
    "delete_regular_chats": false,
    "delete_user_file_conversations": false,
    "delete_global_collection_conversations": false,
    "delete_null_conversations": true
  }'
```

### 3. Delete Only Regular Chat Conversations
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/all" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delete_files_and_collections": false,
    "delete_regular_chats": true,
    "delete_user_file_conversations": false,
    "delete_global_collection_conversations": false,
    "delete_null_conversations": false
  }'
```

### 3. Delete User File Conversations But Keep Files
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/all" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delete_files_and_collections": false,
    "delete_regular_chats": false,
    "delete_user_file_conversations": true,
    "delete_global_collection_conversations": false
  }'
```

### 4. Clean Up Everything Except Global Collection Conversations
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/all" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delete_files_and_collections": true,
    "delete_regular_chats": true,
    "delete_user_file_conversations": true,
    "delete_global_collection_conversations": false
  }'
```

### 5. Delete All Conversations But Preserve Files and Collections
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/all" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delete_files_and_collections": false,
    "delete_regular_chats": true,
    "delete_user_file_conversations": true,
    "delete_global_collection_conversations": true
  }'
```

## JavaScript/Frontend Examples

### Using Fetch API
```javascript
// Delete everything
const response = await fetch('/api/chat/conversations/all', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    delete_files_and_collections: true,
    delete_regular_chats: true,
    delete_user_file_conversations: true,
    delete_global_collection_conversations: true
  })
});

// Delete only regular chats
const response = await fetch('/api/chat/conversations/all', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    delete_files_and_collections: false,
    delete_regular_chats: true,
    delete_user_file_conversations: false,
    delete_global_collection_conversations: false
  })
});
```

### Using Axios
```javascript
import axios from 'axios';

// Delete user file conversations only
const response = await axios.delete('/api/chat/conversations/all', {
  headers: {
    'Authorization': `Bearer ${token}`
  },
  data: {
    delete_files_and_collections: true,
    delete_regular_chats: false,
    delete_user_file_conversations: true,
    delete_global_collection_conversations: false
  }
});
```

## Response Format

The response format remains the same, providing detailed statistics:

```json
{
  "detail": "Successfully deleted 15 conversations (5 regular chat conversations, 7 user file conversations, 3 global collection conversations)",
  "deleted_stats": {
    "conversations_deleted": 15,
    "files_deleted": 23,
    "collections_deleted": 7,
    "regular_conversations_deleted": 5,
    "user_files_conversations_deleted": 7,
    "global_collection_conversations_deleted": 3,
    "errors": []
  }
}
```

## Migration Notes

### For API Consumers
- **Breaking Change**: Query parameters are no longer supported
- **Migration Required**: Update client code to use request body instead of query parameters
- **Content-Type**: Must include `Content-Type: application/json` header
- **Validation**: Request body parameters are now validated by Pydantic models

### Old Format (No longer supported)
```bash
# ❌ This will no longer work
DELETE /api/collections/all?delete_collections=true&include_regular=false
```

### New Format (Required)
```bash
# ✅ Use this format instead
DELETE /api/collections/all
Content-Type: application/json

{
  "delete_files_and_collections": true,
  "delete_regular_chats": false,
  "delete_user_file_conversations": true,
  "delete_global_collection_conversations": true
}
```

## Validation Features

### Automatic Type Validation
- All parameters must be boolean values
- Invalid types will return HTTP 422 (Unprocessable Entity)
- Clear error messages for validation failures

### Default Values
All parameters default to `true`, maintaining the original "delete everything" behavior when no request body is provided.

### Schema Documentation
The endpoint is fully documented in the OpenAPI schema, providing:
- Parameter descriptions
- Type information  
- Default values
- Example request bodies
- Response schemas

## Benefits Summary

1. **Clearer Intent**: Parameter names clearly indicate what will be deleted
2. **Better Validation**: Pydantic models provide robust type checking
3. **Future-Proof**: Easy to extend with additional parameters
4. **Self-Documenting**: Request body structure is self-explanatory
5. **API Standards**: Follows REST API best practices for complex parameters
6. **Type Safety**: Stronger typing improves reliability

This enhanced API provides a more robust, clear, and maintainable interface for granular conversation deletion while maintaining all the powerful features introduced in the previous enhancement.
