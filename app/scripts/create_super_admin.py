#!/usr/bin/env python3
"""
Script to create the initial super admin user.
This should only be run once during initial deployment.
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

def create_super_admin():
    """
    Create the initial super admin user if none exists.
    """
    # Create database connection
    db = Session(engine)
    
    try:
        # Check if any super admin already exists
        existing_super_admin = db.query(models.User).filter(
            models.User.role == UserRole.SUPER_ADMIN
        ).first()
        
        if existing_super_admin:
            print("❌ A super admin user already exists:")
            print(f"   Username: {existing_super_admin.username}")
            print("   Only one super admin is allowed.")
            return False
        
        print("🚀 Creating initial super admin user...")
        print("=" * 50)
        
        # Get user input
        username = input("Enter super admin username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return False
        
        # Check if username already exists
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
        
        print("✅ Super admin user created successfully!")
        print(f"   Username: {super_admin.username}")
        print(f"   Email: {super_admin.email}")
        print(f"   Role: {super_admin.role.value}")
        print("\n🔐 IMPORTANT SECURITY NOTES:")
        print("1. Keep the super admin credentials secure")
        print("2. Only use this account for critical admin operations")
        print("3. Create regular admin accounts for day-to-day operations")
        print("4. Consider changing the password regularly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def promote_existing_user():
    """
    Promote an existing user to super admin.
    """
    db = Session(engine)
    
    try:
        # Check if any super admin already exists
        existing_super_admin = db.query(models.User).filter(
            models.User.role == UserRole.SUPER_ADMIN
        ).first()
        
        if existing_super_admin:
            print("❌ A super admin user already exists:")
            print(f"   Username: {existing_super_admin.username}")
            print("   Only one super admin is allowed.")
            return False
        
        username = input("Enter username of user to promote to super admin: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return False
        
        user = crud.get_user_by_username(db, username)
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        # Confirm promotion
        print(f"\n⚠️  You are about to promote user '{username}' to SUPER_ADMIN")
        print("   This will give them full system control including:")
        print("   - Ability to delete/deactivate other admins")
        print("   - Ability to change user roles")
        print("   - Access to all administrative functions")
        
        confirm = input("\nType 'CONFIRM' to proceed: ").strip()
        if confirm != 'CONFIRM':
            print("❌ Operation cancelled")
            return False
        
        # Promote user
        user.role = UserRole.SUPER_ADMIN
        db.commit()
        db.refresh(user)
        
        print(f"✅ User '{username}' has been promoted to super admin!")
        return True
        
    except Exception as e:
        print(f"❌ Error promoting user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Super Admin Management Tool")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--promote":
        success = promote_existing_user()
    else:
        success = create_super_admin()
    
    if not success:
        sys.exit(1)
    
    print("\n🎉 Operation completed successfully!")
