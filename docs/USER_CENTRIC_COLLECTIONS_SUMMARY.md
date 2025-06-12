# User-Centric Collections API Summary

## Overview
The collections API has been redesigned to be user-centric. Users can only see and manage their own conversation-based collections, which are automatically created when they upload files to conversations.

## Available Endpoints

### 1. Get Global Default Collection
**Endpoint:** `GET /api/collections/global-default`
**Access:** All authenticated users
**Purpose:** Get the current global default collection used for knowledge base conversations

**Response:**
```json
{
  "id": 1,
  "name": "global_knowledge_base",
  "description": "Global knowledge base for all users",
  "is_global_default": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 2. Get User's Collections
**Endpoint:** `GET /api/collections/`
**Access:** All authenticated users (see only their own)
**Purpose:** List all conversation-based collections belonging to the current user

**Response:**
```json
[
  {
    "conversation_id": "conv_123",
    "collection_name": "conversation_conv_123",
    "headline": "My Document Analysis",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:30:00Z",
    "file_count": 3,
    "processed_file_count": 3,
    "is_ready": true,
    "files": [
      {
        "id": 1,
        "filename": "document.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "is_processed": true,
        "created_at": "2024-01-01T10:00:00Z"
      }
    ]
  }
]
```

### 3. Get Collection Details
**Endpoint:** `GET /api/collections/{conversation_id}`
**Access:** Users can only access their own conversation collections
**Purpose:** Get detailed information about a specific conversation collection

**Response:**
```json
{
  "conversation_id": "conv_123",
  "collection_name": "conversation_conv_123",
  "headline": "My Document Analysis",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:30:00Z",
  "conversation_type": "USER_FILES",
  "file_count": 3,
  "processed_file_count": 3,
  "is_ready": true,
  "milvus_collection": {
    "exists": true,
    "name": "conversation_conv_123"
  },
  "files": [
    {
      "id": 1,
      "filename": "document.pdf",
      "file_path": "user_123/conv_123/document.pdf",
      "file_size": 1024000,
      "mime_type": "application/pdf",
      "created_at": "2024-01-01T10:00:00Z",
      "is_processed": true,
      "chunk_count": 25,
      "processed_at": "2024-01-01T10:05:00Z",
      "download_url": "/api/collections/conv_123/files/1/download"
    }
  ]
}
```

### 4. Secure File Download
**Endpoint:** `GET /api/collections/{conversation_id}/files/{file_id}/download`
**Access:** Users can only download files from their own conversation collections
**Purpose:** Securely download a file with authentication and permission validation

**Security Features:**
- Requires authentication for every download
- Validates conversation ownership
- Validates file ownership
- Streams file content directly (no exposed credentials)
- No temporary URLs that can be shared/leaked

**Response:** Binary file stream with appropriate headers

### 5. Remove File from Collection
**Endpoint:** `DELETE /api/collections/{conversation_id}/files/{file_id}`
**Access:** Users can only remove files from their own conversation collections
**Purpose:** Remove a specific file from a conversation collection

**Parameters:**
- `delete_from_minio`: boolean (default: true) - Whether to delete file from MinIO storage
- `delete_from_vectorstore`: boolean (default: true) - Whether to remove vectors from Milvus

**Response:**
```json
{
  "detail": "File removed from conversation successfully",
  "conversation_id": "conv_123",
  "file_id": 1,
  "filename": "document.pdf",
  "deleted_from_minio": true,
  "deleted_from_vectorstore": true
}
```

### 6. Delete Conversation Collection
**Endpoint:** `DELETE /api/collections/{conversation_id}/collection`
**Access:** Users can only delete their own conversation collections
**Purpose:** Delete an entire conversation collection and all its files

**Parameters:**
- `delete_from_milvus`: boolean (default: true) - Whether to delete the collection from Milvus

**Response:**
```json
{
  "detail": "Conversation collection deleted successfully",
  "conversation_id": "conv_123",
  "collection_name": "conversation_conv_123",
  "deleted_files_count": 3,
  "deleted_files": [
    {
      "id": 1,
      "filename": "document.pdf",
      "file_path": "user_123/conv_123/document.pdf"
    }
  ],
  "deleted_from_milvus": true
}
```

### 7. Delete All User Conversations
**Endpoint:** `DELETE /api/collections/all`
**Access:** Users can only delete their own conversations
**Purpose:** Delete user's conversations with granular control over conversation types

**Parameters:**
- `delete_collections`: boolean (default: true) - Whether to also delete collections and files associated with conversations
- `include_regular`: boolean (default: true) - Whether to delete regular chat conversations (no files or collections)
- `include_user_files`: boolean (default: true) - Whether to delete conversations with user-uploaded files and their collections
- `include_global_collection`: boolean (default: true) - Whether to delete conversations linked to global collections (admin knowledge bases)

**Response:**
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

**Usage Examples:**
```bash
# Delete all conversations (default behavior)
DELETE /api/collections/all

# Delete only regular chat conversations
DELETE /api/collections/all?include_user_files=false&include_global_collection=false

# Delete only user file conversations and their collections
DELETE /api/collections/all?include_regular=false&include_global_collection=false

# Delete only global collection conversations (unlink from admin knowledge bases)
DELETE /api/collections/all?include_regular=false&include_user_files=false

# Delete all conversations but keep files and collections
DELETE /api/collections/all?delete_collections=false
```

**Note:** This is a destructive operation that cannot be undone. It will delete selected conversation types and optionally their associated files and vector collections.

## Security Features

1. **User Isolation**: Users can only see and manage their own conversation collections
2. **Conversation Ownership**: All operations verify that the conversation belongs to the requesting user
3. **File Access Control**: Users can only remove files from conversations they own
4. **Complete Cleanup**: File deletion removes data from database, MinIO, and Milvus vector store
5. **Secure Downloads**: Authentication-required downloads with no exposed credentials

## Key Benefits

1. **Simplified UX**: Users just upload files to conversations - no collection management complexity
2. **Automatic Organization**: Collections are automatically created and named based on conversations
3. **File Management**: Users can remove unwanted files from their conversations
4. **Complete Cleanup**: File removal includes database, MinIO storage, and vector embeddings
5. **Conversation Reset**: Users can delete entire conversation collections to start fresh
6. **Security**: Clear separation between user data and admin-managed knowledge bases

## Admin vs User Collections

- **User Collections**: Created automatically from file uploads to conversations
  - Managed via `/api/collections/` endpoints
  - Users have full control over their own conversation collections
  - Collection names follow pattern: `conversation_{conversation_id}`

- **Admin Collections**: System-wide knowledge bases managed by admins
  - Managed via `/api/admin/collections/` endpoints
  - Used as global default collections for knowledge base conversations
  - Require admin privileges to create/modify

## Workflow

1. **File Upload**: User uploads files to a conversation via `/api/chat/upload-file`
2. **Auto Collection**: System automatically creates a conversation collection if needed
3. **View Collections**: User can see their collections via `GET /api/collections/`
4. **Manage Files**: User can remove specific files via `DELETE /api/collections/{conversation_id}/files/{file_id}`
5. **Reset Conversation**: User can delete entire collection via `DELETE /api/collections/{conversation_id}/collection`

## Final Endpoint List

The collections endpoint now contains:

### **User-Centric Endpoints:**
- `GET /api/collections/global-default` - Get current global default collection
- `GET /api/collections/` - Get user's own conversation collections  
- `GET /api/collections/{conversation_id}` - Get detailed view of user's conversation collection
- `GET /api/collections/{conversation_id}/files/{file_id}/download` - **NEW**: Secure file download
- `DELETE /api/collections/{conversation_id}/files/{file_id}` - Remove file from conversation
- `DELETE /api/collections/{conversation_id}/collection` - Delete entire conversation collection
- `DELETE /api/collections/all` - **NEW**: Delete all user conversations and associated files/collections

### **Admin-Only Endpoint:**
- `DELETE /api/collections/{collection_id}` - Delete admin collection (admin only, with safety checks)

### **Removed Endpoints:**
- ❌ `POST /api/collections/` - Create Collection
- ❌ `PUT /api/collections/{collection_id}` - Update Collection  
- ❌ `POST /api/collections/{collection_id}/files/{file_id}` - Add File To Collection
- ❌ `DELETE /api/collections/{collection_id}/files/{file_id}` - Remove File From Collection
- ❌ `POST /api/collections/{collection_id}/set-as-global-default` - Set Global Default
- ❌ `POST /api/collections/{collection_id}/text` - Add Text To Collection

**Note:** All admin collection management is now handled via `/api/admin/collections/` endpoints.

## New File Removal Feature

### **DELETE /api/collections/{conversation_id}/files/{file_id}**

Users can now remove unwanted files from their conversation collections. This endpoint:

1. **Removes the file from the database**
2. **Optionally deletes the file from MinIO storage** (`delete_from_minio=true` by default)
3. **Optionally removes the file's vectors from Milvus** (`delete_from_vectorstore=true` by default)

**Query Parameters:**
- `delete_from_minio` (boolean, default: true) - Whether to delete from MinIO storage
- `delete_from_vectorstore` (boolean, default: true) - Whether to remove vectors from Milvus

**Security:**
- Users can only remove files from their own conversations
- File must belong to the specified conversation
- Comprehensive permission checks

**Example Response:**
```json
{
  "detail": "File removed successfully",
  "file_id": 123,
  "conversation_id": "abc123def",
  "deleted_from_minio": true,
  "deleted_from_vectorstore": true
}
```

## Enhanced Delete Collection Safety

The admin collection deletion endpoint now includes safety checks:

- **Prevents deletion** of collections linked to active conversations
- **Shows which conversations** would be affected
- **Suggests alternatives** (unlink first or use `/api/admin/collections/`)
- **Automatically deletes** from both database and Milvus

**Example Error Response:**
```json
{
  "detail": "Cannot delete collection: it is linked to 3 conversation(s): ['conv1', 'conv2', 'conv3']. This would break the RAG functionality for these conversations. Please unlink the collection from conversations first or use /api/admin/collections/ for safer deletion."
}
```

## New User Experience

### For Regular Users:

**`GET /api/collections/`** - Shows user's own conversation collections
- Returns collections created from the user's file uploads to conversations
- Each collection represents a conversation where the user has uploaded files
- Shows processing status and file counts

**`GET /api/collections/{conversation_id}`** - Shows detailed view of user's conversation collection
- Detailed file information with processing status
- Milvus collection status
- Download URLs for files
- Chunk counts and processing timestamps

**`DELETE /api/collections/{conversation_id}/files/{file_id}`** - **NEW**: Remove unwanted files
- Remove files from conversation context
- Clean up MinIO storage
- Remove vectors from Milvus collection
- Helps manage conversation relevance

**`GET /api/collections/global-default`** - Shows global default collection (unchanged)
- Used for knowledge base conversations

### For Admin Users:

- Same user-centric read operations as regular users
- `DELETE /api/collections/{collection_id}` for deleting admin collections (with safety checks)
- **All other admin operations moved to `/api/admin/collections/`**

## API Response Examples

### User's Own Collections (`GET /api/collections/`)
```json
[
  {
    "conversation_id": "abc123def",
    "collection_name": "conversation_abc123def",
    "headline": "My Document Analysis",
    "created_at": "2025-05-27T10:30:00Z",
    "updated_at": "2025-05-27T11:45:00Z",
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
        "created_at": "2025-05-27T10:30:00Z"
      }
    ]
  }
]
```

### Detailed Collection View (`GET /api/collections/{conversation_id}`)
```json
{
  "conversation_id": "abc123def",
  "collection_name": "conversation_abc123def",
  "headline": "My Document Analysis",
  "created_at": "2025-05-27T10:30:00Z",
  "updated_at": "2025-05-27T11:45:00Z",
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
      "created_at": "2025-05-27T10:30:00Z",
      "is_processed": true,
      "chunk_count": 15,
      "processed_at": "2025-05-27T10:32:00Z",
      "download_url": "http://minio.example.com/documents/..."
    }
  ]
}
```

## Key Benefits

1. **Simplified**: Clean, focused endpoint with only user-relevant operations
2. **User-Centric**: Users see only their own conversation collections
3. **Intuitive**: Each collection corresponds to a conversation with uploaded files
4. **File Management**: Users can remove unwanted files from conversations
5. **Complete Cleanup**: File removal includes database, MinIO, and vector store
6. **Security**: Users cannot access other users' conversation collections
7. **Clear Separation**: Admin operations clearly separated to `/api/admin/collections/`
8. **Safety Checks**: Admin collection deletion prevents breaking conversations

## Implementation Details

### Files Modified:
- `app/api/routes/collections.py` - Added file removal and enhanced safety checks
- `COLLECTION_MANAGEMENT_GUIDE.md` - Updated documentation
- Removed test scripts (using Swagger instead)

### Key Functions Added:
- `remove_file_from_conversation()` - User file removal endpoint
- `remove_file_vectors_from_collection()` - Vector cleanup from Milvus
- Enhanced `delete_collection()` with conversation link checks

### Key Functions Used:
- `crud.get_conversation_files()` - Get files for a conversation
- `conversation_collection_name()` - Generate collection name from conversation ID
- `vector_store_manager.collection_exists()` - Check Milvus collection status
- `minio_service.delete_file()` - Remove files from MinIO
- `ingestion_service.delete_collection()` - Remove entire collections from Milvus

### Database Queries:
- Filters conversations by `user_id` and `conversation_type == USER_FILES`
- Only shows conversations that actually have files
- Provides rich file metadata including processing status
- Checks conversation links before collection deletion

## Vector Store Management

### File Vector Removal:
- Uses Milvus `delete()` with expression: `source_file_id == {file_id}`
- Leverages metadata stored during file ingestion
- Automatically flushes changes to ensure persistence
- Graceful error handling if vector removal fails

### Collection Safety:
- Checks for linked conversations before deletion
- Prevents orphaning conversation RAG functionality
- Suggests safer alternatives for admins

## Admin Collection Management

For admin operations, use `/api/admin/collections/` endpoints:
- Create, update, delete admin collections
- Add/remove files from admin collections  
- Set global default collections
- Add text content to admin collections
- Advanced batch processing and monitoring

## Migration Notes

- No database changes required
- Frontend should be updated to expect conversation-based collections
- Users will now see their own file collections instead of admin collections
- Admin users should use `/api/admin/collections/` for management operations
- **New feature**: Users can now remove unwanted files from conversations 

## Secure File Download Implementation

### Previous Approach (Security Issues):
- **Presigned URLs**: Generated temporary URLs with embedded MinIO credentials
- **Example**: `http://192.168.1.10:9000/documents/file.pdf?X-Amz-Credential=minioadmin&X-Amz-Signature=...`
- **Problems**:
  - Credentials visible in URL
  - URLs can be shared/leaked
  - Remain valid until expiration even if user loses access
  - Appear in browser history, server logs, etc.

### New Secure Approach:
- **Authenticated Endpoints**: `/api/collections/{conversation_id}/files/{file_id}/download`
- **Real-time Validation**: Every download requires authentication and permission checks
- **Direct Streaming**: File content streamed directly from MinIO without exposing credentials
- **No Temporary URLs**: No shareable URLs that bypass security

### Security Benefits:
1. **Authentication Required**: Every download validates the user's current session
2. **Permission Validation**: Checks conversation and file ownership on every request
3. **No Credential Exposure**: MinIO credentials never appear in URLs or responses
4. **Audit Trail**: All downloads can be logged and monitored
5. **Immediate Revocation**: Access is revoked instantly when user permissions change
6. **No URL Sharing**: Download URLs are not shareable between users 