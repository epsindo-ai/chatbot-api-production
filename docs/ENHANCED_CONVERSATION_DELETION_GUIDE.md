# Enhanced User Conversation Deletion Endpoint

## Overview
The `DELETE /api/collections/all` endpoint has been enhanced with granular control parameters that allow users to selectively delete different types of conversations.

## Enhanced Endpoint: `DELETE /api/collections/all`

### New Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `delete_collections` | boolean | `true` | Whether to also delete collections and files associated with conversations |
| `include_regular` | boolean | `true` | Whether to delete regular chat conversations (no files or collections) |
| `include_user_files` | boolean | `true` | Whether to delete conversations with user-uploaded files and their collections |
| `include_global_collection` | boolean | `true` | Whether to delete conversations linked to global collections (admin knowledge bases) |

### Conversation Types Explained

#### 1. **REGULAR Conversations**
- Basic chat conversations without any files or collections
- Simple text-based conversations
- No associated MinIO files or Milvus collections
- Safe to delete with no external cleanup needed

#### 2. **USER_FILES Conversations**
- Conversations where users have uploaded files
- Have associated collections in Milvus (named `conversation_{id}`)
- Have files stored in MinIO
- When deleted with `delete_collections=true`, removes:
  - Conversation from database
  - Files from MinIO storage
  - User-created collections from Milvus

#### 3. **GLOBAL_COLLECTION Conversations**
- Conversations linked to admin-managed knowledge bases
- Connected to admin collections (shared across users)
- No user-uploaded files (use admin collections for knowledge)
- When deleted:
  - Removes conversation link to admin collection
  - Does NOT delete the admin collection (shared resource)
  - Safe deletion that preserves admin knowledge bases

### Usage Examples

```bash
# Delete all conversations (original behavior)
DELETE /api/collections/all

# Delete only regular chat conversations
DELETE /api/collections/all?include_user_files=false&include_global_collection=false

# Delete only user file conversations and their collections
DELETE /api/collections/all?include_regular=false&include_global_collection=false

# Delete only global collection conversations (unlink from knowledge bases)
DELETE /api/collections/all?include_regular=false&include_user_files=false

# Delete all conversations but keep files and collections
DELETE /api/collections/all?delete_collections=false

# Complex example: Delete only user files and regular chats, keep global collections
DELETE /api/collections/all?include_global_collection=false&delete_collections=true
```

### Enhanced Response Format

```json
{
  "detail": "Successfully deleted 75 conversations (25 regular chat conversations, 30 user file conversations, 20 global collection conversations)",
  "deleted_stats": {
    "conversations_deleted": 75,
    "files_deleted": 28,
    "collections_deleted": 21,
    "regular_conversations_deleted": 25,
    "user_files_conversations_deleted": 30,
    "global_collection_conversations_deleted": 20,
    "errors": [
      "Warning: Could not delete Milvus collection for conversation abc123"
    ]
  }
}
```

### Key Features

#### 1. **Granular Control**
- Users can choose exactly which types of conversations to delete
- Preserves conversations they want to keep
- Allows selective cleanup based on conversation purpose

#### 2. **Safety Features**
- Admin collections are never deleted (shared resources)
- Users can only delete their own conversations
- Comprehensive error handling with detailed statistics
- Clear feedback on what was actually deleted

#### 3. **Flexible File Management**
- `delete_collections=false` allows keeping files while removing conversations
- Useful for preserving uploaded documents while cleaning up chat history
- Granular control over vector store cleanup

#### 4. **Enhanced Statistics**
- Breakdown by conversation type
- Separate counts for regular, user files, and global collection conversations
- Detailed error reporting for partial failures

### Common Use Cases

#### 1. **Privacy Cleanup**
```bash
# Delete all conversations but keep uploaded files
DELETE /api/collections/all?delete_collections=false
```

#### 2. **File Management**
```bash
# Delete only file-based conversations to free up storage
DELETE /api/collections/all?include_regular=false&include_global_collection=false
```

#### 3. **Knowledge Base Reset**
```bash
# Remove links to old knowledge bases, keep personal files and chats
DELETE /api/collections/all?include_regular=false&include_user_files=false
```

#### 4. **Complete Cleanup**
```bash
# Delete everything (original behavior)
DELETE /api/collections/all
```

### Implementation Details

#### Database Operations
- Filters conversations by type before deletion
- Maintains transaction integrity
- Proper error handling with rollback on failures

#### File Cleanup Logic
- Only deletes files for `USER_FILES` conversations
- Skips file deletion for `GLOBAL_COLLECTION` conversations (no user files)
- Graceful handling of MinIO and Milvus cleanup failures

#### Security Considerations
- User isolation maintained (can only delete own conversations)
- Admin collections protected from deletion
- No privilege escalation or data leakage

### Benefits

1. **User Control**: Fine-grained control over what gets deleted
2. **Safety**: Protects shared resources and prevents accidental deletion
3. **Flexibility**: Supports various cleanup scenarios and use cases
4. **Transparency**: Clear reporting on what was actually deleted
5. **Performance**: Only processes selected conversation types

### Backward Compatibility

The endpoint remains fully backward compatible:
- Default parameters maintain original "delete all" behavior
- Existing API calls continue to work without modification
- No breaking changes to response format (only additions)

This enhancement provides users with powerful, flexible conversation management capabilities while maintaining safety and preserving shared resources.
