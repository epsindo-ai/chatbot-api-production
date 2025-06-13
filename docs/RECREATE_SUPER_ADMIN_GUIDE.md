# Super Admin Recreate Script

This script provides a comprehensive tool for managing the super admin user in the system.

## Features

The `recreate_super_admin.py` script can:

1. **Recreate Super Admin** - Delete existing super admin and create a new one
2. **Reset Password** - Reset the password of the existing super admin
3. **Promote User** - Promote an existing user to super admin (demoting current one)

## Usage

### 1. Recreate Super Admin (Interactive)
```bash
cd /app
python app/scripts/recreate_super_admin.py
```

This will:
- Check if a super admin exists
- Ask for confirmation before deletion
- Guide you through creating a new super admin
- Provide security warnings and notes

### 2. Recreate Super Admin (Force Mode)
```bash
cd /app
python app/scripts/recreate_super_admin.py --force
```

This will:
- Skip confirmation prompts
- Automatically delete existing super admin
- Create new super admin
- **⚠️ Use with extreme caution!**

### 3. Reset Super Admin Password Only
```bash
cd /app
python app/scripts/recreate_super_admin.py --reset-password
```

This will:
- Keep the existing super admin user
- Only change their password
- Safer option if you just need to reset credentials

### 4. Promote Existing User to Super Admin
```bash
cd /app
python app/scripts/recreate_super_admin.py --promote
```

This will:
- Promote an existing user to super admin
- Demote current super admin to regular admin
- Preserve all user data

## Security Warnings

⚠️ **CRITICAL SECURITY WARNINGS:**

1. **Data Loss**: Recreating super admin will DELETE all data associated with the current super admin
2. **System Access**: This gives complete system control to the new user
3. **Irreversible**: Deletion operations cannot be undone
4. **Single Point of Failure**: Only one super admin can exist at a time

## Examples

### Example 1: Emergency Super Admin Recreation
If you've lost access to the super admin account:

```bash
cd /app
python app/scripts/recreate_super_admin.py
# Follow prompts to create new super admin
```

### Example 2: Quick Password Reset
If you just need to reset the super admin password:

```bash
cd /app
python app/scripts/recreate_super_admin.py --reset-password
# Enter new password when prompted
```

### Example 3: Transfer Super Admin Rights
To transfer super admin rights to an existing user:

```bash
cd /app
python app/scripts/recreate_super_admin.py --promote
# Enter username of user to promote
```

## Output Examples

### Successful Recreation:
```
🔧 Super Admin Recreate Tool
========================================
🔍 Existing super admin found:
   Username: oldadmin
   Email: old@example.com
   Active: True
   Created: 2025-06-13 10:30:00

⚠️  WARNING: This will DELETE the existing super admin and create a new one!
   This action is IRREVERSIBLE and will:
   - Remove the current super admin user from the system
   - Delete all their conversations, files, and collections
   - Create a completely new super admin user

Type 'DELETE_AND_RECREATE' to proceed: DELETE_AND_RECREATE

🗑️  Deleting existing super admin: oldadmin
✅ Existing super admin deleted successfully

🚀 Creating new super admin user...
==================================================
Enter super admin username: newadmin
Enter super admin email (optional): new@example.com
Enter super admin full name (optional): New Admin
Enter super admin password: 
Confirm password: 
✅ New super admin user created successfully!
   Username: newadmin
   Email: new@example.com
   Role: super_admin
   Active: True

🔐 IMPORTANT SECURITY NOTES:
1. Keep the new super admin credentials secure
2. Only use this account for critical admin operations
3. Create regular admin accounts for day-to-day operations
4. Consider changing the password regularly
5. Document this change in your security logs

🎉 Operation completed successfully!
```

### Password Reset Example:
```
🔑 Super Admin Password Reset
========================================
🔍 Existing super admin found:
   Username: admin
   Email: admin@example.com
   Active: True
   Created: 2025-06-13 10:30:00

🔒 Resetting password for: admin
Enter new password: 
Confirm new password: 
✅ Super admin password reset successfully!

🎉 Operation completed successfully!
```

## Best Practices

1. **Backup First**: Always backup your database before running this script
2. **Document Changes**: Keep a record of when and why you recreated the super admin
3. **Use Least Privilege**: Consider using `--reset-password` instead of full recreation when possible
4. **Test Access**: Verify the new super admin can log in before closing your current session
5. **Secure Credentials**: Use strong, unique passwords for the super admin account

## Troubleshooting

### Common Issues:

1. **"No module named 'app'"**: Make sure you're running from the `/app` directory
2. **Database connection errors**: Ensure the database is running and accessible
3. **Permission denied**: Make sure the script is executable (`chmod +x`)

### Emergency Recovery:

If something goes wrong during recreation:

1. Check database directly for user records
2. Use the original `create_super_admin.py` script as fallback
3. Restore from database backup if necessary

## Related Files

- `/app/app/scripts/create_super_admin.py` - Original super admin creation script
- `/app/app/db/crud.py` - User CRUD operations
- `/app/app/utils/auth.py` - Authentication utilities
