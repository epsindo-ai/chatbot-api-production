from sqlalchemy.orm import Session
from app.db import crud, models, schemas
from app.utils.password import verify_password, get_password_hash

def get_user_by_username(username: str, db: Session = None):
    """
    Get a user by username. For compatibility with JWT middleware,
    this function can work without a db session (falling back to fake data).
    """
    if db is not None:
        return crud.get_user_by_username(db, username)
    
    # Fallback for JWT middleware that doesn't have DB access
    # This is just for development; in production, this should be removed
    fake_users_db = {
        "testuser": {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": get_password_hash("password123"),
            "is_active": True,
            "role": models.UserRole.USER
        }
    }
    
    if username not in fake_users_db:
        return None
    
    user_data = fake_users_db[username]
    
    # Create a models.User object instead of a schema
    user = models.User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        full_name=user_data["full_name"],
        hashed_password=user_data["hashed_password"],
        is_active=user_data["is_active"],
        role=user_data["role"]
    )
    
    return user

def create_user(db: Session, user_data: schemas.UserCreate):
    """Create a new user"""
    return crud.create_user(db, user_data)

def authenticate_user(username: str, password: str, db: Session = None):
    """Authenticate a user with username and password."""
    user = get_user_by_username(username, db)
    
    if not user:
        return False
    
    if not verify_password(password, user.hashed_password):
        return False
    
    # Check if user account is active
    if not user.is_active:
        return False
    
    return user

def create_initial_user(db: Session):
    """Create an initial super admin user if no users exist."""
    existing_users = crud.get_users(db, limit=1)
    
    if not existing_users:
        # Check if there's already a super admin user (safety check)
        super_admin_exists = db.query(models.User).filter(
            models.User.role == models.UserRole.SUPER_ADMIN
        ).first()
        
        if not super_admin_exists:
            user_data = schemas.UserCreate(
                username="superadmin",
                email="admin@company.com",
                full_name="Super Administrator",
                password="superadmin123",  # Should be changed immediately after deployment
                role=schemas.UserRole.SUPER_ADMIN
            )
            created_user = crud.create_user(db, user_data)
            print(f"Created initial super admin user: {created_user.username}")
            print("IMPORTANT: Please change the default password immediately!")
            return created_user
    
    return None 