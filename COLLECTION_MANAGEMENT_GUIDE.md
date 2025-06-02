# Collection Management Guide

## Overview

The collection management system has been redesigned to provide clear separation between admin-managed knowledge bases and user-specific document conversations.

## User Roles and Permissions

### **Regular Users**
- ❌ **Cannot create collections**
- ❌ **Cannot modify collections** 
- ❌ **Cannot add files to collections**
- ✅ **Can view non-admin collections** (read-only)
- ✅ **Can upload files to conversations** (auto-creates conversation-specific collections)
- ✅ **Can chat with global default collection**
- ✅ **Can chat with their uploaded files**

### **Admin Users**
- ✅ **Can create collections** (via `/api/collections/` or `/api/admin/collections/`)
- ✅ **Can modify all collections**
- ✅ **Can add/remove files from collections**
- ✅ **Can set global default collections**
- ✅ **Can view all collections**
- ✅ **Can manage system-wide knowledge bases**

## Collection Types

### 1. **Admin Collections** (`is_admin_only=true`)
- Created by admins for organization-wide knowledge
- Visible to all users but only manageable by admins
- Can be set as global default
- Examples: Company policies, product documentation, FAQ

### 2. **Public Collections** (`is_admin_only=false`)
- Created by admins but accessible to all users
- Can be used for shared knowledge that users can reference
- Examples: General knowledge, public documentation

### 3. **Conversation Collections** (Auto-generated)
- Automatically created when users upload files to conversations
- Named using pattern: `conversation_{conversation_id}`
- Only accessible within that specific conversation
- Automatically deleted when conversation is deleted

## User Workflow

### **For Regular Users:**

1. **Start a conversation:**
   ```
   POST /api/chat/initiate-for-files
   ```

2. **Upload files to conversation:**
   ```
   POST /api/chat/upload-file
   ```
   - Files are automatically processed for RAG
   - Creates conversation-specific collection in Milvus
   - Files are only accessible within that conversation

3. **Chat with uploaded files:**
   ```
   POST /api/chat/stream
   ```
   - System automatically uses conversation files for RAG
   - No need to specify collection names

4. **Chat with global knowledge base:**
   ```
   POST /api/chat/initiate-with-global-collection
   ```
   - Uses admin-configured global default collection

### **For Admin Users:**

1. **Create system-wide collection:**
   ```
   POST /api/admin/collections/
   {
     "name": "company_policies",
     "description": "Company policies and procedures",
     "is_admin_only": true
   }
   ```

2. **Add files to collection:**
   ```
   POST /api/admin/collections/{collection_id}/process
   ```

3. **Set as global default:**
   ```
   POST /api/collections/{collection_id}/set-as-global-default
   ```

## API Endpoints

### **Regular User Endpoints (User-Centric):**
```
GET  /api/collections/                    # View user's own conversation collections
GET  /api/collections/{conversation_id}  # View details of user's conversation collection
GET  /api/collections/global-default     # Get current global default collection

# File upload and conversation management
POST /api/chat/upload-file               # Upload files to conversation
POST /api/chat/initiate-for-files        # Start file-based conversation
POST /api/chat/initiate-with-global-collection  # Start with global collection
```

### **Admin-Only Collection Management:**
```
# Basic admin collection management (via /api/collections/)
POST   /api/collections/                 # Create admin collection
PUT    /api/collections/{id}             # Update admin collection  
DELETE /api/collections/{id}             # Delete admin collection
POST   /api/collections/{id}/files/{file_id}  # Add file to admin collection
DELETE /api/collections/{id}/files/{file_id}  # Remove file from admin collection
POST   /api/collections/{id}/set-as-global-default  # Set global default
POST   /api/collections/{id}/text        # Add text to admin collection

# Advanced admin collection management (via /api/admin/collections/)
POST   /api/admin/collections/           # Create admin collection
GET    /api/admin/collections/           # List all collections with files
PUT    /api/admin/collections/{id}       # Update admin collection
DELETE /api/admin/collections/{id}       # Delete admin collection
POST   /api/admin/collections/{id}/process  # Process all files in background
GET    /api/admin/collections/milvus/stats  # Milvus statistics
```

## Collection Endpoints Purpose

### **`/api/collections/` - User-Centric for Regular Users, Admin Management for Admins**

**For Regular Users (User-Centric):**
- `GET /api/collections/` - View their own conversation-based collections
- `GET /api/collections/{conversation_id}` - View detailed info about their conversation collection
- `GET /api/collections/global-default` - View the global default collection
- **Shows only collections created from their file uploads to conversations**
- **Each collection represents a conversation where they uploaded files**

**For Admin Users (Full Management):**
- All user operations above (but shows admin-managed collections)
- Create, update, delete admin-managed collections
- Add/remove files from admin collections
- Set global default collections
- Add text content to admin collections

### **`/api/admin/collections/` - Advanced Admin Management**

**For Admin Users Only:**
- Advanced collection management with enhanced features
- Batch file processing with background tasks
- Milvus statistics and monitoring
- Force admin-only collection creation
- Enhanced file processing workflows

### **`/api/chat/` - User File Management**

**For All Users:**
- Upload files to conversations (auto-creates conversation collections)
- Initiate conversations with different modes
- Chat with uploaded files or global collections

## User Collection Response Format

### **GET /api/collections/ (User's Own Collections)**
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

### **GET /api/collections/{conversation_id} (Detailed View)**
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

## Database Schema

### Collections Table:
```sql
CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description TEXT,
    user_id INTEGER REFERENCES users(id),  -- Always admin user
    is_admin_only BOOLEAN DEFAULT FALSE,   -- Controls visibility
    is_global_default BOOLEAN DEFAULT FALSE,  -- Only one can be true
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

### Key Constraints:
- Only one collection can have `is_global_default=true`
- All collections are created by admin users
- Regular users cannot modify collection records

## Milvus Collection Naming

### Admin Collections:
- Database name: `"company_policies"`
- Milvus name: `"company_policies"` (sanitized)

### Conversation Collections:
- Database: Not stored (auto-generated)
- Milvus name: `"conversation_abc123def"` (sanitized conversation ID)

## Migration Notes

If you have existing user-created collections, you'll need to:

1. **Migrate ownership** to admin users
2. **Set appropriate flags** (`is_admin_only`, `is_global_default`)
3. **Update frontend** to remove collection creation UI for regular users
4. **Test permissions** to ensure regular users can't access admin endpoints

## Security Considerations

- Regular users cannot access admin collection management endpoints
- File uploads are scoped to conversations (no cross-conversation access)
- Conversation collections are automatically isolated
- Admin collections require explicit permission management

## Benefits

1. **Simplified UX**: Users just upload files and chat - no collection management needed
2. **Better Security**: Clear separation between user data and admin knowledge bases  
3. **Easier Administration**: Centralized collection management for admins
4. **Automatic Cleanup**: Conversation collections are tied to conversation lifecycle
5. **Scalable**: No limit on user file uploads, admin controls system collections

## Final Architecture Summary

### **Three-Tier Collection System:**

1. **User Tier**: 
   - No collection management
   - File upload to conversations only
   - Read-only access to public collections

2. **Admin Basic Tier** (`/api/collections/`):
   - Full collection CRUD operations
   - File management within collections
   - Global default configuration
   - Suitable for simple admin tasks

3. **Admin Advanced Tier** (`/api/admin/collections/`):
   - Enhanced collection management
   - Background processing capabilities
   - Milvus monitoring and statistics
   - Batch operations and advanced workflows

This architecture ensures that:
- **Regular users** have a simple, intuitive experience
- **Admins** have powerful tools for knowledge management
- **System security** is maintained through clear permission boundaries
- **Scalability** is achieved through proper separation of concerns 