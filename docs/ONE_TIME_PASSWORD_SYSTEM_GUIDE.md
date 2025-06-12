# One-Time Password System Implementation Guide

## Overview

This document explains the implementation of a one-time password (OTP) system for admin-managed account creation and password resets. This system allows administrators to create user accounts with temporary passwords that must be changed on first login.

## Features

### 1. Admin User Creation with Temporary Passwords
- Admins can create user accounts with temporary passwords
- Temporary passwords have configurable expiration times (default: 24 hours)
- Users must change their password on first login
- System tracks password status and expiration

### 2. Admin Password Reset
- Admins can reset user passwords to temporary ones
- Super admin protection: only super admins can reset super admin passwords
- Configurable expiration times for reset passwords

### 3. Password Change Enforcement
- Users with temporary passwords are required to change them
- Login responses include temporary password status
- Expired temporary passwords prevent login

### 4. Security Features
- Secure password generation utility
- Password expiration tracking
- Role-based access control for password operations

## Database Schema Changes

### User Model Additions
```sql
-- New fields added to users table
is_temporary_password BOOLEAN DEFAULT FALSE NOT NULL;
temp_password_expires_at TIMESTAMP WITH TIME ZONE NULL;
must_reset_password BOOLEAN DEFAULT FALSE NOT NULL;
```

## API Endpoints

### 1. Create User with Temporary Password
**POST** `/api/admin/users/create-with-temp-password`

**Access:** Admin required

**Request Body:**
```json
{
  "username": "newuser",
  "email": "user@company.com",
  "full_name": "New User",
  "role": "USER",
  "temporary_password": "TempPass123!",
  "password_expires_hours": 24
}
```

**Response:**
```json
{
  "user_id": 123,
  "username": "newuser",
  "email": "user@company.com",
  "full_name": "New User",
  "role": "USER",
  "is_active": true,
  "temporary_password": "TempPass123!",
  "password_expires_at": "2025-06-13T07:23:53.412333Z",
  "must_reset_password": true
}
```

### 2. Reset User Password
**POST** `/api/admin/users/reset-password`

**Access:** Admin required

**Request Body:**
```json
{
  "user_id": 123,
  "temporary_password": "NewTempPass456!",
  "password_expires_hours": 48
}
```

**Response:**
```json
{
  "user_id": 123,
  "username": "existinguser",
  "temporary_password": "NewTempPass456!",
  "password_expires_at": "2025-06-14T07:23:53.412333Z",
  "message": "Password has been reset. User must change password on next login."
}
```

### 3. Generate Temporary Password
**POST** `/api/admin/users/generate-temp-password`

**Access:** Admin required

**Response:**
```json
{
  "temporary_password": "X7$mN9pQ2!vR",
  "message": "Use this password when creating a user account or resetting a password. The user will be required to change it on first login."
}
```

### 4. Change Password (User)
**POST** `/api/auth/change-password`

**Access:** Authenticated user

**Request Body:**
```json
{
  "current_password": "TempPass123!",
  "new_password": "MyNewSecurePassword123!",
  "confirm_password": "MyNewSecurePassword123!"
}
```

**Response:**
```json
{
  "message": "Password successfully changed",
  "user_id": 123,
  "username": "newuser",
  "must_reset_password": false,
  "is_temporary_password": false
}
```

## Enhanced Login Response

When users with temporary passwords log in, the login response includes additional fields:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user_id": 123,
  "username": "newuser",
  "email": "user@company.com",
  "full_name": "New User",
  "role": "USER",
  "expires_in": 3600,
  "is_active": true,
  "must_reset_password": true,
  "is_temporary_password": true,
  "temp_password_expires_at": "2025-06-13T07:23:53.412333Z"
}
```

## Workflow Examples

### 1. Admin Creates New User Account

1. **Admin generates temporary password**
   ```bash
   curl -X POST "http://localhost:8000/api/admin/users/generate-temp-password" \
        -H "Authorization: Bearer <admin_token>"
   ```

2. **Admin creates user with temporary password**
   ```bash
   curl -X POST "http://localhost:8000/api/admin/users/create-with-temp-password" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer <admin_token>" \
        -d '{
          "username": "johndoe",
          "email": "john@company.com",
          "full_name": "John Doe",
          "role": "USER",
          "temporary_password": "X7$mN9pQ2!vR",
          "password_expires_hours": 24
        }'
   ```

3. **Admin provides credentials to user**
   - Username: `johndoe`
   - Temporary Password: `X7$mN9pQ2!vR`
   - Instructions: "You must change your password on first login"

### 2. User First Login and Password Change

1. **User logs in with temporary password**
   ```bash
   curl -X POST "http://localhost:8000/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
          "username": "johndoe",
          "password": "X7$mN9pQ2!vR"
        }'
   ```

2. **System responds with temporary password flags**
   - Response includes `must_reset_password: true`
   - Frontend should redirect to password change form

3. **User changes password**
   ```bash
   curl -X POST "http://localhost:8000/api/auth/change-password" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer <user_token>" \
        -d '{
          "current_password": "X7$mN9pQ2!vR",
          "new_password": "MySecurePassword123!",
          "confirm_password": "MySecurePassword123!"
        }'
   ```

### 3. Admin Resets Existing User Password

1. **Admin resets password**
   ```bash
   curl -X POST "http://localhost:8000/api/admin/users/reset-password" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer <admin_token>" \
        -d '{
          "user_id": 123,
          "temporary_password": "ResetPass789!",
          "password_expires_hours": 48
        }'
   ```

2. **Admin notifies user of password reset**
3. **User follows same login and password change process**

## Security Considerations

### Password Expiry Handling
- Expired temporary passwords prevent login with specific error message
- Users must contact admin for new temporary password if expired
- System tracks expiration timestamps in UTC

### Role-Based Access Control
- Only admins can create accounts and reset passwords
- Only super admins can reset super admin passwords
- Regular users can only change their own passwords

### Password Validation
- Minimum 8 character requirement for new passwords
- Secure temporary password generation with mixed character sets
- Password confirmation required for changes

### Database Security
- Temporary password flags stored securely
- Password expiration tracked with precise timestamps
- All password operations logged through standard audit trail

## Frontend Integration Guidelines

### Login Flow Enhancement
1. Check `must_reset_password` flag in login response
2. If true, redirect to password change form instead of main application
3. Display password expiration time to user
4. Show appropriate error messages for expired passwords

### Admin Interface
1. Add user creation form with temporary password generation
2. Implement password reset functionality for user management
3. Display temporary password status in user lists
4. Provide password generation utility

### User Experience
1. Clear instructions for temporary password usage
2. Password strength indicators for new passwords
3. Confirmation of successful password changes
4. Helpful error messages for various failure scenarios

## Error Handling

### Common Error Scenarios
- **Username already exists**: 409 Conflict
- **Email already exists**: 409 Conflict
- **Temporary password expired**: 401 Unauthorized
- **Incorrect current password**: 401 Unauthorized
- **Password confirmation mismatch**: 400 Bad Request
- **Insufficient permissions**: 403 Forbidden

### Error Response Format
```json
{
  "detail": "Temporary password has expired. Please contact an administrator for a password reset."
}
```

## Monitoring and Maintenance

### Key Metrics to Monitor
- Number of temporary passwords created per day
- Password expiration rates
- Failed login attempts due to expired passwords
- Time between account creation and password change

### Maintenance Tasks
- Regular cleanup of expired temporary password records
- Monitor for accounts with long-standing temporary passwords
- Review password reset frequency patterns
- Audit admin password creation activities

## Migration Notes

### Existing Users
- All existing users have `is_temporary_password = false`
- All existing users have `must_reset_password = false`
- No impact on existing authentication flows

### Database Migration
- Applied migration `4f6b1fa00461_add_temporary_password_fields`
- New columns added with appropriate defaults
- Backward compatible with existing authentication

## Testing

### Manual Testing Checklist
- [ ] Admin can create user with temporary password
- [ ] Admin can reset user password
- [ ] Admin can generate secure passwords
- [ ] User can login with temporary password
- [ ] User must change temporary password
- [ ] Expired passwords prevent login
- [ ] Role restrictions work correctly
- [ ] Password validation works properly

### API Testing Examples
See the workflow examples above for complete curl commands to test each endpoint.

## Conclusion

The one-time password system provides a secure and user-friendly way for administrators to manage user account creation and password resets. The implementation follows security best practices while maintaining a smooth user experience for both administrators and end users.
