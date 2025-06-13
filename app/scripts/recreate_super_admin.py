#!/usr/bin/env python3
"""
Script to recreate the super admin user.
This can be used to:
1. Replace an existing super admin 
2. Create a new super admin if none exists
3. Reset super admin credentials

WARNING: This is a powerful script that can replace the system's super admin.
Use with extreme caution.
"""
import sys
import os

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(app_dir)
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from app.db.database import engine
from app.db import crud, schemas, models
from app.db.models import UserRole
from app.utils.password import get_password_hash
import getpass
import argparse

def check_existing_super_admin(db: Session):
    """Check if a super admin already exists and return user info."""
    existing_super_admin = db.query(models.User).filter(
        models.User.role == UserRole.SUPER_ADMIN
    ).first()
    
    if existing_super_admin:
        print("🔍 Existing super admin found:")
        print(f"   Username: {existing_super_admin.username}")
        print(f"   Email: {existing_super_admin.email}")
        print(f"   Active: {existing_super_admin.is_active}")
        print(f"   Created: {existing_super_admin.created_at}")
        return existing_super_admin
    else:
        print("ℹ️  No existing super admin found.")
        return None

def delete_existing_super_admin(db: Session, existing_super_admin):
    """Safely delete the existing super admin."""
    try:
        print(f"🗑️  Deleting existing super admin: {existing_super_admin.username}")
        
        # Delete user (this will cascade delete related records)
        db.delete(existing_super_admin)
        db.commit()
        
        print("✅ Existing super admin deleted successfully")
        return True
    except Exception as e:
        print(f"❌ Error deleting existing super admin: {e}")
        db.rollback()
        return False

def create_new_super_admin(db: Session):
    """Create a new super admin user."""
    try:
        print("\n🚀 Creating new super admin user...")
        print("=" * 50)
        
        # Get user input
        username = input("Enter super admin username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return False
        
        # Check if username already exists (for non-super-admin users)
        existing_user = crud.get_user_by_username(db, username)
        if existing_user:
            print(f"❌ Username '{username}' already exists")
            return False
        
        email = input("Enter super admin email (optional): ").strip()
        full_name = input("Enter super admin full name (optional): ").strip()
        
        # Get password securely
        password = getpass.getpass("Enter super admin password: ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long")
            return False
        
        confirm_password = getpass.getpass("Confirm password: ")
        if password != confirm_password:
            print("❌ Passwords do not match")
            return False
        
        # Create user data
        user_data = schemas.UserCreate(
            username=username,
            email=email if email else None,
            full_name=full_name if full_name else None,
            password=password,
            is_active=True,
            role=UserRole.SUPER_ADMIN
        )
        
        # Create the user
        super_admin = crud.create_user(db, user_data)
        
        print("✅ New super admin user created successfully!")
        print(f"   Username: {super_admin.username}")
        print(f"   Email: {super_admin.email}")
        print(f"   Role: {super_admin.role.value}")
        print(f"   Active: {super_admin.is_active}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating new super admin: {e}")
        db.rollback()
        return False

def recreate_super_admin(force=False):
    """
    Main function to recreate super admin.
    
    Args:
        force (bool): If True, will not ask for confirmation before deleting existing super admin
    """
    db = Session(engine)
    
    try:
        print("🔧 Super Admin Recreate Tool")
        print("=" * 40)
        
        # Check for existing super admin
        existing_super_admin = check_existing_super_admin(db)
        
        if existing_super_admin:
            if not force:
                print("\n⚠️  WARNING: This will DELETE the existing super admin and create a new one!")
                print("   This action is IRREVERSIBLE and will:")
                print("   - Remove the current super admin user from the system")
                print("   - Delete all their conversations, files, and collections")
                print("   - Create a completely new super admin user")
                print("\n   Make sure you understand the implications!")
                
                confirm = input("\nType 'DELETE_AND_RECREATE' to proceed: ").strip()
                if confirm != 'DELETE_AND_RECREATE':
                    print("❌ Operation cancelled")
                    return False
            
            # Delete existing super admin
            if not delete_existing_super_admin(db, existing_super_admin):
                return False
        
        # Create new super admin
        if create_new_super_admin(db):
            print("\n🔐 IMPORTANT SECURITY NOTES:")
            print("1. Keep the new super admin credentials secure")
            print("2. Only use this account for critical admin operations")
            print("3. Create regular admin accounts for day-to-day operations")
            print("4. Consider changing the password regularly")
            print("5. Document this change in your security logs")
            return True
        else:
            return False
        
    except Exception as e:
        print(f"❌ Error during super admin recreation: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def reset_super_admin_password():
    """Reset the password of the existing super admin."""
    db = Session(engine)
    
    try:
        print("🔑 Super Admin Password Reset")
        print("=" * 40)
        
        # Check for existing super admin
        existing_super_admin = check_existing_super_admin(db)
        
        if not existing_super_admin:
            print("❌ No super admin found to reset password for")
            return False
        
        print(f"\n🔒 Resetting password for: {existing_super_admin.username}")
        
        # Get new password
        new_password = getpass.getpass("Enter new password: ")
        if len(new_password) < 8:
            print("❌ Password must be at least 8 characters long")
            return False
        
        confirm_password = getpass.getpass("Confirm new password: ")
        if new_password != confirm_password:
            print("❌ Passwords do not match")
            return False
        
        # Update password
        existing_super_admin.hashed_password = get_password_hash(new_password)
        db.commit()
        
        print("✅ Super admin password reset successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def promote_user_to_super_admin():
    """Promote an existing user to super admin (replacing current one if exists)."""
    db = Session(engine)
    
    try:
        print("⬆️  Promote User to Super Admin")
        print("=" * 40)
        
        # Check for existing super admin
        existing_super_admin = check_existing_super_admin(db)
        
        username = input("Enter username of user to promote to super admin: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return False
        
        user = crud.get_user_by_username(db, username)
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        if user.role == UserRole.SUPER_ADMIN:
            print(f"ℹ️  User '{username}' is already a super admin")
            return True
        
        # Show current user info
        print(f"\n👤 User to promote:")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Current Role: {user.role.value}")
        print(f"   Active: {user.is_active}")
        
        if existing_super_admin:
            print(f"\n⚠️  This will demote the current super admin: {existing_super_admin.username}")
            print("   The current super admin will become a regular admin.")
        
        confirm = input(f"\nType 'PROMOTE_{username.upper()}' to proceed: ").strip()
        if confirm != f'PROMOTE_{username.upper()}':
            print("❌ Operation cancelled")
            return False
        
        # Demote existing super admin to regular admin if exists
        if existing_super_admin:
            existing_super_admin.role = UserRole.ADMIN
            print(f"✅ Demoted {existing_super_admin.username} to regular admin")
        
        # Promote user to super admin
        user.role = UserRole.SUPER_ADMIN
        db.commit()
        
        print(f"✅ User '{username}' has been promoted to super admin!")
        return True
        
    except Exception as e:
        print(f"❌ Error promoting user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='Recreate or manage super admin user')
    parser.add_argument('--force', action='store_true', 
                       help='Skip confirmation prompts (use with caution)')
    parser.add_argument('--reset-password', action='store_true',
                       help='Reset existing super admin password only')
    parser.add_argument('--promote', action='store_true',
                       help='Promote an existing user to super admin')
    
    args = parser.parse_args()
    
    if args.reset_password:
        success = reset_super_admin_password()
    elif args.promote:
        success = promote_user_to_super_admin()
    else:
        success = recreate_super_admin(force=args.force)
    
    if not success:
        sys.exit(1)
    
    print("\n🎉 Operation completed successfully!")

if __name__ == "__main__":
    main()
