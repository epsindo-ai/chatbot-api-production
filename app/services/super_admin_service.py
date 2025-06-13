"""
Super Admin Service - Handles initialization of the single super admin user.
"""
import os
from sqlalchemy.orm import Session
from app.db import crud, models, schemas
from app.db.models import UserRole
from app.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SuperAdminService:
    """Service for managing the single super admin user during deployment."""
    
    @staticmethod
    def initialize_super_admin(db: Session) -> Optional[models.User]:
        """
        Initialize the single super admin user during app deployment.
        
        This function:
        1. Checks if a super admin already exists
        2. If not, creates one using environment variables
        3. Ensures only one super admin can exist
        
        Returns:
            models.User: The super admin user if created/found, None if error
        """
        try:
            # Check if any super admin already exists
            existing_super_admin = db.query(models.User).filter(
                models.User.role == UserRole.SUPER_ADMIN
            ).first()
            
            if existing_super_admin:
                logger.info(f"Super admin already exists: {existing_super_admin.username}")
                return existing_super_admin
            
            # Get super admin credentials from environment variables
            super_admin_username = os.getenv('SUPER_ADMIN_USERNAME', 'superadmin')
            super_admin_password = os.getenv('SUPER_ADMIN_PASSWORD', 'changeme123!')
            super_admin_email = os.getenv('SUPER_ADMIN_EMAIL', 'admin@company.com')
            super_admin_full_name = os.getenv('SUPER_ADMIN_FULL_NAME', 'Super Administrator')
            
            # Warn if using default credentials
            if super_admin_password == 'changeme123!':
                logger.warning(
                    "🚨 SECURITY WARNING: Using default super admin password! "
                    "Set SUPER_ADMIN_PASSWORD environment variable with a secure password."
                )
            
            # Check if username already exists with different role
            existing_user = crud.get_user_by_username(db, super_admin_username)
            if existing_user:
                if existing_user.role != UserRole.SUPER_ADMIN:
                    # Promote existing user to super admin
                    logger.info(f"Promoting existing user '{super_admin_username}' to super admin")
                    existing_user.role = UserRole.SUPER_ADMIN
                    db.commit()
                    db.refresh(existing_user)
                    return existing_user
                else:
                    # This shouldn't happen due to the first check, but just in case
                    return existing_user
            
            # Create new super admin user
            logger.info(f"Creating super admin user: {super_admin_username}")
            
            user_data = schemas.UserCreate(
                username=super_admin_username,
                email=super_admin_email,
                full_name=super_admin_full_name,
                password=super_admin_password,
                is_active=True,
                role=UserRole.SUPER_ADMIN
            )
            
            super_admin = crud.create_user(db, user_data)
            logger.info(f"✅ Super admin created successfully: {super_admin.username}")
            
            # Log security reminders
            logger.info("🔐 IMPORTANT SECURITY REMINDERS:")
            logger.info("1. Change the super admin password immediately if using defaults")
            logger.info("2. Use environment variables to set secure credentials")
            logger.info("3. Restrict access to the super admin account")
            logger.info("4. Create regular admin accounts for day-to-day operations")
            
            return super_admin
            
        except Exception as e:
            logger.error(f"❌ Error initializing super admin: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def get_super_admin(db: Session) -> Optional[models.User]:
        """Get the single super admin user."""
        return db.query(models.User).filter(
            models.User.role == UserRole.SUPER_ADMIN
        ).first()
    
    @staticmethod
    def super_admin_exists(db: Session) -> bool:
        """Check if a super admin user exists."""
        return db.query(models.User).filter(
            models.User.role == UserRole.SUPER_ADMIN
        ).count() > 0
    
    @staticmethod
    def validate_single_super_admin(db: Session) -> bool:
        """
        Validate that exactly one super admin exists.
        
        Returns:
            bool: True if exactly one super admin exists, False otherwise
        """
        super_admin_count = db.query(models.User).filter(
            models.User.role == UserRole.SUPER_ADMIN
        ).count()
        
        if super_admin_count == 0:
            logger.warning("⚠️ No super admin user found in system")
            return False
        elif super_admin_count > 1:
            logger.warning(f"⚠️ Multiple super admin users found: {super_admin_count}")
            return False
        else:
            logger.info("✅ Single super admin validation passed")
            return True
