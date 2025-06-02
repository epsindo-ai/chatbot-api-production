import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from db.database import engine
from db import models
from db.models import UserRole

def set_default_roles():
    """
    Ensure all users have a role assigned.
    Sets role to USER for any user with NULL role.
    """
    # Get a database session
    db = Session(engine)
    
    try:
        # Get all users without a role
        users_without_role = db.query(models.User).filter(
            models.User.role.is_(None)
        ).all()
        
        if not users_without_role:
            print("All users already have roles assigned.")
            return True
        
        # Update users without role
        updated_count = 0
        for user in users_without_role:
            user.role = UserRole.USER
            updated_count += 1
            print(f"Setting role 'USER' for user: {user.username}")
        
        # Commit changes
        if updated_count > 0:
            db.commit()
            print(f"Updated {updated_count} user(s) with default role.")
        
        return True
    except Exception as e:
        print(f"Error updating user roles: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = set_default_roles()
    
    if not success:
        sys.exit(1) 