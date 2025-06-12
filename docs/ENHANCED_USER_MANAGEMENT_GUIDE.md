# Enhanced User Management Guide

## Overview
The enhanced user management system provides comprehensive tools for administrators to manage users, their data, and system resources effectively. This guide covers all available endpoints and best practices for user management operations.

## User Management Philosophy

### Safety First Approach
1. **Deactivation over Deletion**: Prefer deactivating users over permanent deletion
2. **Data Preservation**: Maintain data integrity and relationships
3. **Dry Run Operations**: Preview impact before making changes
4. **Comprehensive Logging**: Track all administrative actions

### Data Cleanup Levels
1. **Soft Delete**: Deactivate user account (recommended)
2. **Selective Cleanup**: Delete specific data types
3. **Complete Removal**: Full user and data deletion
4. **Bulk Operations**: Manage multiple users efficiently

## Available Endpoints

### 1. User Listing and Statistics

#### **GET /api/admin/users/**
List all users with comprehensive statistics for administrative oversight.

**Parameters:**
- `skip`: Number of users to skip (pagination)
- `limit`: Maximum number of users to return
- `include_stats`: Whether to include detailed statistics
- `active_only`: Filter to show only active users

**Response Example:**
```json
[
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
]
```

**Use Cases:**
- Monitor user activity and resource usage
- Identify users for cleanup or management
- Generate usage reports for system administrators

#### **GET /api/admin/users/{user_id}/stats**
Get detailed statistics for a specific user.

**Response includes:**
- User basic information
- Activity metrics (conversations, files, collections)
- Storage usage statistics
- Last activity timestamp

### 2. User Deactivation (Recommended Approach)

#### **PATCH /api/admin/users/{user_id}/deactivate**
Safely deactivate a user account without data loss.

**Features:**
- Prevents user login while preserving all data
- Maintains data relationships and integrity
- Can be easily reversed with reactivation
- Safer than permanent deletion

**Safety Checks:**
- Prevents self-deactivation
- Prevents deactivating the last active admin

#### **PATCH /api/admin/users/{user_id}/reactivate**
Restore access to a previously deactivated user account.

**Example Usage:**
```bash
# Deactivate a user
curl -X PATCH "http://localhost:8000/api/admin/users/123/deactivate" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Reactivate a user
curl -X PATCH "http://localhost:8000/api/admin/users/123/reactivate" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### 3. Inactive User Management

#### **GET /api/admin/users/inactive**
Identify users who have been inactive for a specified period.

**Parameters:**
- `days_inactive`: Consider users inactive after this many days (default: 30)
- `skip`: Pagination offset
- `limit`: Maximum number of results

**Use Cases:**
- Identify candidates for deactivation
- Clean up unused accounts
- Monitor user engagement patterns

### 4. User Deletion (Use with Caution)

#### **DELETE /api/admin/users/{user_id}**
Permanently delete a user and optionally their associated data.

**Parameters:**
- `delete_files`: Delete user's files from MinIO storage (default: true)
- `delete_conversations`: Delete user's conversations (default: true)
- `delete_collections`: Delete user's collections from Milvus (default: true)
- `force_delete_global_default`: Force delete even if user owns global default collections
- `dry_run`: Preview deletion impact without actually deleting

**Enhanced Features:**
- **Dry Run Mode**: Preview what would be deleted before proceeding
- **Force Delete**: Override protection for global default collections
- **Detailed Statistics**: Comprehensive reporting of deletion impact
- **Enhanced Safety**: Better protection against accidental deletions

**Dry Run Example:**
```bash
curl -X DELETE "http://localhost:8000/api/admin/users/123?dry_run=true" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Response includes impact assessment:**
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
    "storage_to_free_mb": 45.2
  }
}
```

### 5. Bulk Operations

#### **POST /api/admin/users/bulk-delete**
Delete multiple users in a single operation.

**Request Body:**
```json
{
  "user_ids": [123, 456, 789],
  "delete_files": true,
  "delete_conversations": true,
  "delete_collections": true
}
```

**Features:**
- Process up to 50 users per request
- Comprehensive error handling per user
- Detailed statistics for each deletion
- Safety checks for admin users and global collections

**Response includes:**
- Successful deletions with statistics
- Failed deletions with error reasons
- Skipped deletions (safety violations)
- Summary statistics across all operations

### 6. Admin Data Cleanup

#### **DELETE /api/admin/users/admin/all-data**
Nuclear option: Delete all admin files and collections.

**Safety Requirements:**
- Must provide confirmation string: `DELETE_ALL_ADMIN_DATA`
- Extremely destructive operation
- Use only for complete system reset

#### **DELETE /api/admin/users/me/all-conversations**
Allow users (including admins) to delete their own conversations.

**Parameters:**
- `delete_collections`: Whether to also delete associated files and collections

## Best Practices

### 1. User Lifecycle Management

#### New User Onboarding
- Users are created with `USER` role by default
- Admin privileges must be granted separately
- Monitor new user activity patterns

#### Active User Management
- Regular monitoring of user statistics
- Identify heavy users for resource planning
- Track usage patterns for system optimization

#### User Offboarding
```bash
# Recommended approach: Deactivate first
curl -X PATCH "/api/admin/users/123/deactivate"

# If permanent removal needed: Use dry run first
curl -X DELETE "/api/admin/users/123?dry_run=true"

# Then proceed with actual deletion if appropriate
curl -X DELETE "/api/admin/users/123"
```

### 2. Data Management

#### Storage Optimization
- Use inactive user reports to identify cleanup candidates
- Monitor file storage usage per user
- Regular cleanup of deactivated users' data

#### Collection Management
- Be cautious with users who own global default collections
- Use `force_delete_global_default=true` only when necessary
- Ensure replacement global collections before deletion

### 3. Safety Protocols

#### Before User Deletion
1. **Run Statistics Check**: `GET /api/admin/users/{user_id}/stats`
2. **Perform Dry Run**: `DELETE /api/admin/users/{user_id}?dry_run=true`
3. **Review Impact**: Analyze what will be deleted
4. **Consider Deactivation**: Often safer than deletion
5. **Proceed with Caution**: Use actual deletion only when necessary

#### Admin User Management
- Never delete the last admin user
- Prevent self-deletion accidents
- Maintain at least one active admin at all times
- Use role updates carefully

### 4. Monitoring and Reporting

#### Regular Health Checks
```bash
# Get overview of all users
GET /api/admin/users/?include_stats=true

# Identify inactive users
GET /api/admin/users/inactive?days_inactive=60

# Check specific user impact
GET /api/admin/users/123/stats
```

#### Resource Usage Monitoring
- Track total storage usage across users
- Monitor conversation activity patterns
- Identify resource-heavy users
- Plan capacity based on usage trends

## Security Considerations

### Access Control
- All endpoints require admin authentication
- Users cannot delete other users' data
- Self-deletion prevention for admin users
- Global collection protection mechanisms

### Data Privacy
- Complete data removal when requested
- Secure deletion from all storage systems
- Audit trail for administrative actions
- Compliance with data protection regulations

### System Integrity
- Prevention of last admin deletion
- Global collection dependency checks
- Database transaction safety
- Graceful error handling

## Error Handling

### Common Error Scenarios
1. **User Not Found**: 404 error with clear messaging
2. **Permission Denied**: 403 error for non-admin users
3. **Safety Violation**: 400 error for dangerous operations
4. **System Error**: 500 error with detailed logging

### Recovery Procedures
- User reactivation for deactivated accounts
- Data restore from backups if available
- System consistency checks after bulk operations
- Error reporting and logging mechanisms

## Integration Examples

### Frontend Integration
```javascript
// Check user statistics before deletion
const userStats = await api.get(`/admin/users/${userId}/stats`);

// Perform dry run to show impact
const dryRun = await api.delete(`/admin/users/${userId}?dry_run=true`);

// Show confirmation dialog with impact details
if (confirm(`Delete user? This will remove ${dryRun.impact_summary.files_to_delete} files`)) {
  await api.delete(`/admin/users/${userId}`);
}
```

### Automated Cleanup Scripts
```bash
#!/bin/bash
# Weekly inactive user cleanup

# Get inactive users (90+ days)
INACTIVE_USERS=$(curl -s "http://localhost:8000/api/admin/users/inactive?days_inactive=90")

# Process each inactive user
echo "$INACTIVE_USERS" | jq -r '.[].user_id' | while read user_id; do
  # Deactivate instead of delete
  curl -X PATCH "http://localhost:8000/api/admin/users/$user_id/deactivate"
done
```

## Conclusion

The enhanced user management system provides administrators with powerful, safe, and comprehensive tools for managing users and their data. By following the recommended practices and using the safety features (dry runs, deactivation, etc.), administrators can maintain system health while protecting user data and system integrity.

Key recommendations:
1. **Always use dry run before deletion**
2. **Prefer deactivation over deletion**
3. **Monitor user statistics regularly**
4. **Use bulk operations for efficiency**
5. **Maintain at least one active admin**
6. **Document administrative actions**

This system balances administrative power with safety mechanisms to ensure responsible user management.
