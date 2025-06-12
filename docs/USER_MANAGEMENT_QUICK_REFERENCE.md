# Enhanced User Management - Quick Reference

## New Admin Capabilities

Your enhanced user management system now includes comprehensive tools for managing users and their data with multiple safety levels and options.

## 🎯 Key Features Added

### 1. **Enhanced User Listing with Statistics**
```bash
# Get all users with detailed statistics
GET /api/admin/users/?include_stats=true

# Get specific user statistics  
GET /api/admin/users/{user_id}/stats

# Filter active users only
GET /api/admin/users/?active_only=true
```

**Returns comprehensive data:**
- User activity metrics (conversations, files, collections)
- Storage usage (file counts and sizes)
- Last activity timestamps
- Role and status information

### 2. **Safe User Deactivation (Recommended)**
```bash
# Deactivate user (prevents login, preserves data)
PATCH /api/admin/users/{user_id}/deactivate

# Reactivate user (restores access)
PATCH /api/admin/users/{user_id}/reactivate
```

**Benefits:**
- ✅ Reversible operation
- ✅ Preserves all user data and relationships
- ✅ Immediate effect (user cannot login)
- ✅ No data loss risk

### 3. **Enhanced User Deletion with Safety Features**
```bash
# Preview deletion impact (dry run)
DELETE /api/admin/users/{user_id}?dry_run=true

# Delete with granular control
DELETE /api/admin/users/{user_id}?delete_files=true&delete_conversations=true&delete_collections=true

# Force delete users with global collections
DELETE /api/admin/users/{user_id}?force_delete_global_default=true
```

**New safety features:**
- 🔍 **Dry run mode**: Preview what will be deleted
- ⚠️ **Impact assessment**: Shows files, storage, conversations affected
- 🛡️ **Global collection protection**: Warns about system-critical collections
- 📊 **Detailed reporting**: Comprehensive deletion statistics

### 4. **Inactive User Management**
```bash
# Find users inactive for 30+ days
GET /api/admin/users/inactive?days_inactive=30

# Find users inactive for 90+ days (candidates for cleanup)
GET /api/admin/users/inactive?days_inactive=90
```

**Use cases:**
- Identify accounts for deactivation
- Clean up unused accounts
- Monitor user engagement patterns

### 5. **Bulk User Operations**
```bash
# Delete multiple users at once
POST /api/admin/users/bulk-delete
{
  "user_ids": [123, 456, 789],
  "delete_files": true,
  "delete_conversations": true,
  "delete_collections": true
}
```

**Features:**
- Process up to 50 users per request
- Individual error handling per user
- Comprehensive statistics reporting
- Safety checks for admin users

## 🚀 Recommended Workflow

### Step 1: Assessment
```bash
# 1. Get user statistics
curl -X GET "/api/admin/users/123/stats" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 2. Preview deletion impact
curl -X DELETE "/api/admin/users/123?dry_run=true" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Step 2: Decision Making
**For inactive users:**
- **Temporary removal**: Use deactivation (recommended)
- **Data cleanup needed**: Use deletion with dry run first

**For active users:**
- **Policy violation**: Deactivate first, delete later if needed
- **Account migration**: Export data first, then delete

### Step 3: Execution
```bash
# Option A: Safe deactivation (recommended)
curl -X PATCH "/api/admin/users/123/deactivate" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Option B: Permanent deletion (after dry run)
curl -X DELETE "/api/admin/users/123" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## 📊 Response Examples

### User Statistics Response
```json
{
  "user_id": 123,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "conversations_count": 25,
  "files_count": 12,
  "collections_count": 3,
  "total_file_size_mb": 45.2,
  "last_activity": "2024-06-10T14:20:00Z"
}
```

### Dry Run Response
```json
{
  "detail": "DRY RUN: User 'john_doe' deletion preview completed",
  "deleted_stats": {
    "files_deleted": 12,
    "conversations_deleted": 25,
    "collections_deleted": 3,
    "total_file_size_mb": 45.2,
    "warnings": ["User owns 1 global default collection(s)"]
  },
  "impact_summary": {
    "files_to_delete": 12,
    "conversations_to_delete": 25,
    "storage_to_free_mb": 45.2,
    "conversations_to_unlink": 5
  }
}
```

### Bulk Deletion Response
```json
{
  "detail": "Bulk deletion completed: 3 successful, 0 failed, 1 skipped",
  "results": {
    "successful_deletions": [
      {
        "user_id": 123,
        "username": "user1",
        "files_deleted": 5,
        "conversations_deleted": 10
      }
    ],
    "failed_deletions": [],
    "skipped_deletions": [
      {
        "user_id": 456,
        "username": "admin_user",
        "reason": "Cannot delete admin user"
      }
    ],
    "summary_stats": {
      "total_files_deleted": 15,
      "total_conversations_deleted": 30
    }
  }
}
```

## 🛡️ Safety Mechanisms

### Built-in Protections
- ❌ **Cannot delete yourself**
- ❌ **Cannot delete the last admin user**
- ❌ **Cannot deactivate the last active admin**
- ⚠️ **Warns about global default collections**
- 🔄 **Dry run mode for impact preview**

### Best Practices
1. **Always run dry run first** for deletion operations
2. **Use deactivation** instead of deletion when possible
3. **Monitor inactive users** regularly for proactive management
4. **Bulk operations** for efficiency with large user cleanup
5. **Maintain audit trail** of administrative actions

## 🔧 Common Operations

### Monthly Cleanup
```bash
# 1. Find inactive users (60+ days)
GET /api/admin/users/inactive?days_inactive=60

# 2. Deactivate inactive users
PATCH /api/admin/users/{user_id}/deactivate

# 3. Delete very old inactive users (after review)
DELETE /api/admin/users/{user_id}?dry_run=true
DELETE /api/admin/users/{user_id}
```

### User Offboarding
```bash
# 1. Check user's impact
GET /api/admin/users/{user_id}/stats

# 2. Deactivate immediately
PATCH /api/admin/users/{user_id}/deactivate

# 3. Later: Delete if data not needed
DELETE /api/admin/users/{user_id}?dry_run=true
DELETE /api/admin/users/{user_id}
```

### Emergency Cleanup
```bash
# Bulk deactivation (safer than deletion)
POST /api/admin/users/bulk-delete  # Use with deactivation logic
```

Your enhanced user management system now provides comprehensive, safe, and efficient tools for managing users while protecting system integrity and data relationships.
