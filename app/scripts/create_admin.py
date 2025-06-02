import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import get_db, engine
from app.db import models
from app.db.models import UserRole

def create_admin_user(username: str):
    """
    Set a user as admin by username
    """
    # Get a database session
    db = Session(engine)
    
    try:
        # Find user
        user = db.query(models.User).filter(models.User.username == username).first()
        
        if not user:
            print(f"User with username '{username}' not found.")
            return False
        
        # Set role to admin
        user.role = UserRole.ADMIN
        db.commit()
        
        print(f"User '{username}' has been set as an admin.")
        return True
    except Exception as e:
        print(f"Error updating user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_admin.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    success = create_admin_user(username)
    
    if not success:
        sys.exit(1) 