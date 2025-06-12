# Enhanced Conversation Deletion API - Quick Reference

## Endpoint
```
DELETE /api/chat/conversations/all
```

## Authentication
Requires Bearer token authentication.

## Request Format
**Content-Type**: `application/json`

### Request Body Parameters
```json
{
  "delete_files_and_collections": true,
  "delete_regular_chats": true,
  "delete_user_file_conversations": true,
  "delete_global_collection_conversations": true,
  "delete_null_conversations": true
}
```

#### Parameter Descriptions
- `delete_files_and_collections` (boolean, default: true): Whether to also delete files and collections
- `delete_regular_chats` (boolean, default: true): Include regular chat conversations  
- `delete_user_file_conversations` (boolean, default: true): Include conversations with user files
- `delete_global_collection_conversations` (boolean, default: true): Include global collection conversations
- `delete_null_conversations` (boolean, default: true): Include orphaned/null conversations **[NEW]**

## Response Format
```json
{
  "detail": "Successfully deleted 25 conversations (10 regular chat conversations, 8 user file conversations, 5 global collection conversations, 2 orphaned/null conversations)",
  "deleted_stats": {
    "conversations_deleted": 25,
    "files_deleted": 15,
    "collections_deleted": 8,
    "regular_conversations_deleted": 10,
    "user_files_conversations_deleted": 8,
    "global_collection_conversations_deleted": 5,
    "null_conversations_deleted": 2,
    "errors": []
  }
}
```

## Usage Examples

### 1. Delete Everything (Default)
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/all" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 2. Delete Only Regular Chats
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

### 3. Cleanup Only Orphaned Conversations
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

### 4. Keep Files but Delete Conversations
```bash
curl -X DELETE "http://localhost:8000/api/chat/conversations/all" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delete_files_and_collections": false,
    "delete_regular_chats": true,
    "delete_user_file_conversations": true,
    "delete_global_collection_conversations": true,
    "delete_null_conversations": true
  }'
```

## Error Responses

### No Conversations Found
```json
{
  "detail": "No conversations matching the specified criteria found to delete",
  "deleted_stats": {
    "conversations_deleted": 0,
    "files_deleted": 0,
    "collections_deleted": 0,
    "regular_conversations_deleted": 0,
    "user_files_conversations_deleted": 0,
    "global_collection_conversations_deleted": 0,
    "null_conversations_deleted": 0,
    "errors": []
  }
}
```

### Server Error
```json
{
  "detail": "Failed to delete conversations: <error_message>"
}
```

## Security Notes
- Users can only delete their own conversations
- Admin users have additional privileges
- Operation cannot be undone
- Files and vector collections are permanently deleted when requested

## Features
✅ **Granular Control**: Choose exactly which conversation types to delete  
✅ **Automatic Cleanup**: Handles orphaned/null conversations by default  
✅ **Detailed Statistics**: Know exactly what was deleted  
✅ **Safe Operations**: Cannot delete other users' data  
✅ **Comprehensive Logging**: All errors and warnings reported  

## New in This Version
🆕 **Null Conversation Handling**: Automatic cleanup of orphaned conversations  
🆕 **Enhanced Statistics**: Separate tracking for all conversation types  
🆕 **JSON Request Body**: Better validation and more intuitive API  
🆕 **Improved Location**: Moved to `/api/chat/` for better organization
