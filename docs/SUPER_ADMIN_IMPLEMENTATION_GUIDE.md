# Super Admin Implementation Guide

## Overview

This implementation introduces a three-tier user role hierarchy to address security concerns about admin privilege escalation:

- **USER**: Regular users with basic chat and file upload capabilities
- **ADMIN**: Administrative users who can manage collections, files, and system configuration
- **SUPER_ADMIN**: Ultimate system administrators who can manage other admins and users

## Security Model

### Role Hierarchy
```
SUPER_ADMIN (Ultimate authority)
    ├── Can manage other admins and super admins
    ├── Can delete/deactivate/promote any user
    ├── Can change user roles
    └── Has all admin privileges
    
ADMIN (System management)
    ├── Can manage collections and files
    ├── Can view user statistics
    ├── Can manage system configuration
    └── Cannot modify other admin accounts
    
USER (Regular access)
    ├── Can chat and upload files
    ├── Can manage own conversations
    └── Read-only access to shared resources
```

### Key Security Features

1. **Single Super Admin**: Only one super admin can exist at a time
2. **Initial Deployment Only**: Super admin can only be created during initial app deployment
3. **Self-Protection**: Users cannot modify their own roles or delete themselves
4. **Last Admin Protection**: System prevents deletion of the last admin/super admin

## Implementation Details

### Database Changes

1. **New UserRole Enum Value**:
   ```python
   class UserRole(enum.Enum):
       USER = "user"
       ADMIN = "admin"
       SUPER_ADMIN = "super_admin"  # New role
   ```

2. **Migration**: Added Alembic migration to update the database enum

### Authentication Updates

1. **New Dependency**: `get_super_admin_access()` for super admin-only endpoints
2. **Updated Dependencies**: `get_admin_access()` now accepts both ADMIN and SUPER_ADMIN
3. **Token Generation**: Both admin roles get shorter-lived tokens

### API Endpoint Changes

#### Super Admin Only Endpoints
These endpoints now require SUPER_ADMIN role:

- `DELETE /api/admin/users/{user_id}` - Delete users
- `POST /api/admin/users/bulk-delete` - Bulk delete users  
- `PATCH /api/admin/users/{user_id}/deactivate` - Deactivate users
- `PATCH /api/admin/users/{user_id}/reactivate` - Reactivate users
- `POST /api/admin/users/update-role` - Change user roles

#### Admin + Super Admin Endpoints
These endpoints accept both ADMIN and SUPER_ADMIN roles:

- All collection management endpoints
- System configuration endpoints
- User statistics and listing endpoints
- File management endpoints

## Deployment Guide

### Initial Setup

1. **Run Database Migration**:
   ```bash
   cd /app
   alembic upgrade head
   ```

2. **Create Super Admin**:
   ```bash
   python app/scripts/create_super_admin.py
   ```

3. **Follow Security Prompts**: The script will guide you through creating secure credentials

### Alternative: Promote Existing User

If you have an existing admin user to promote:

```bash
python app/scripts/create_super_admin.py --promote
```

## Operational Guidelines

### Super Admin Responsibilities

1. **Minimal Usage**: Only use super admin account for critical operations
2. **Regular Auditing**: Monitor admin user activities
3. **Credential Security**: Use strong passwords and consider rotation
4. **Backup Planning**: Ensure recovery procedures for super admin access

### Creating Additional Admins

Super admins can promote regular users to admin status:

```bash
curl -X POST "http://localhost:8000/api/admin/users/update-role" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user_to_promote",
    "role": "admin"
  }'
```

### Deactivating Problematic Admins

Super admins can deactivate admin accounts without deleting data:

```bash
curl -X PATCH "http://localhost:8000/api/admin/users/123/deactivate" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN"
```

## Security Considerations

### Protections Implemented

1. **Role Change Validation**: Prevents self-role changes and ensures at least one super admin exists
2. **Endpoint Authorization**: Strict role checking on all sensitive operations
3. **Audit Logging**: Critical actions are logged (user promotions, deletions)
4. **Active User Checks**: Inactive users cannot log in or access any endpoints

### Best Practices

1. **Principle of Least Privilege**: Use regular admin accounts for daily operations
2. **Regular Review**: Periodically audit user roles and access patterns
3. **Secure Storage**: Store super admin credentials securely
4. **Change Management**: Document and approve all role changes

## Troubleshooting

### Common Issues

1. **Cannot Create Super Admin**: Check if one already exists
2. **Permission Denied**: Verify token has correct role
3. **Migration Errors**: Ensure database is accessible and up-to-date

### Recovery Procedures

If super admin access is lost:

1. **Database Access Required**: Direct database manipulation needed
2. **Promote Via Script**: Use the promotion script with database access
3. **Reset Approach**: In extreme cases, reset user roles via direct SQL

## Migration Notes

### Existing Systems

For systems upgrading to this implementation:

1. **Existing Admins**: All existing admin users remain as ADMIN role
2. **No Automatic Promotion**: No existing user is automatically promoted to SUPER_ADMIN
3. **Manual Creation**: Super admin must be created manually using the script

### Backward Compatibility

- All existing admin endpoints continue to work for ADMIN role users
- No breaking changes to API contracts
- Enhanced security without functionality loss

## Testing

### Verification Steps

1. **Create Super Admin**: Verify script creates user with correct role
2. **Test Endpoints**: Confirm role-based access control works
3. **Security Checks**: Verify protection mechanisms (self-deletion, last admin, etc.)
4. **Authentication**: Test login and token generation for all roles

### Test Commands

```bash
# Test super admin creation
python app/scripts/create_super_admin.py

# Test endpoint access
curl -X GET "http://localhost:8000/api/admin/users/" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Test role updates (should require super admin)
curl -X POST "http://localhost:8000/api/admin/users/update-role" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "role": "admin"}'
```

## Conclusion

This implementation provides a robust security model that prevents admin privilege abuse while maintaining operational flexibility. The super admin role ensures there's always an ultimate authority for user management while protecting against unauthorized access escalation.
